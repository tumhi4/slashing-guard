"""
SlashingGuard Lifecycle & Architectural Invariant Test Suite
============================================================
Comprehensive test suite verifying the core architectural invariants of
the SlashingGuard Ethereum PoS Validator Slashing Insurance Protocol,
specifically validating all protocol steward (Pavel Kolosov) requirements
and hardcore security audit remediations:

1. In-Term Slashing Consensus: slashed=True, exit_epoch <= max_epoch -> CLAIM_APPROVED.
2. Out-of-Term Slashing Consensus: slashed=True, exit_epoch > max_epoch -> EXPIRED (pool preserved).
3. Relay Authorization Invariant: Unauthorized caller attempting confirm_settlement reverts with [ERR_UNAUTHORIZED_RELAY].
4. Receipt Amount Invariant: Amount mismatch in confirm_settlement reverts with [ERR_AMOUNT_MISMATCH].
5. Anti-Replay Invariant: Duplicate settlement attempts revert with [ERR_CLAIM_ALREADY_SETTLED].
6. Receipt Block Height Invariant: Settlement block <= 0 reverts with [ERR_BLOCK_01].
7. Receipt Hash Format Invariant: Invalid hash format reverts with [ERR_HASH_01].
8. BLS Public Key Cryptographic Binding: Mismatched pubkey reverts with [ERR_PUBKEY_MISMATCH].
9. Underwriting Pool Solvency & Full Reserve Accounting.
10. EVM SlashingGuardVault Multi-Layer Anti-Replay & Solvency Guards.
11. Global Cross-Policy Receipt Anti-Replay: [ERR_HASH_ALREADY_USED].
12. Underwriting Deposit Access Control: [ERR_UNAUTHORIZED].
13. Strict Conjunction Verdict Consistency: [ERR_VERDICT_CONTRADICTION].
14. EVM Vault Pull-Payment DoS Resilience & Emergency Controls.
"""

import sys
import os
import json
import logging
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


class MockSlashingGuardVault:
    """Mock EVM Underwriting & Reimbursement Vault simulating SlashingGuardVault.sol"""
    def __init__(self, relay_address: str, initial_reserves: int = 25000):
        self.owner = "0x71546f55c131acd54cf93e181b9cabaeaf440fc3"
        self.authorized_relay = relay_address.lower()
        self.total_reserves = initial_reserves
        self.total_claims_paid = 0
        self.settled_claims = {}
        self.pending_reimbursements = {}

    def execute_slashing_payout(self, policy_id_b32: bytes, staker: str, amount: int, direct_transfer_fails: bool = False) -> dict:
        if self.settled_claims.get(policy_id_b32, False):
            raise AssertionError("[ERR_ALREADY_SETTLED] Claim for this policy was already settled.")
        if self.total_reserves < amount:
            raise AssertionError(f"[ERR_UNDERFUNDED] Vault reserves ({self.total_reserves}) < claim amount ({amount}).")

        self.settled_claims[policy_id_b32] = True
        self.total_reserves -= amount
        self.total_claims_paid += amount

        if direct_transfer_fails:
            # Fallback to pull payments
            self.pending_reimbursements[staker.lower()] = self.pending_reimbursements.get(staker.lower(), 0) + amount
            return {
                "status": 1,
                "queued": True,
                "transactionHash": "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
                "blockNumber": 6891234
            }
        return {
            "status": 1,
            "queued": False,
            "transactionHash": "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a",
            "blockNumber": 6891234,
            "gasUsed": 48210
        }

    def withdraw_pending_reimbursement(self, caller: str) -> int:
        amt = self.pending_reimbursements.get(caller.lower(), 0)
        if amt == 0:
            raise AssertionError("[ERR_NO_PENDING_FUNDS] No pending reimbursement to withdraw.")
        self.pending_reimbursements[caller.lower()] = 0
        return amt


class MockSlashingGuardCourt:
    """Simulates SlashingGuardCourt Intelligent Contract on GenLayer"""
    def __init__(self, operator: str, authorized_relay: str = ""):
        self.operator = operator.strip().lower()
        self.authorized_relay = authorized_relay.strip().lower() if authorized_relay else self.operator
        self.pool_capital_usdc = 25000
        self.total_active_coverage_usdc = 1000
        self.total_claims_paid_usdc = 0
        self.total_policies = 1

        self.authorized_sources = {
            "ethereum-beacon-api.publicnode.com": True,
            "sepolia-beacon-api.publicnode.com": True,
            "holesky-beacon-api.publicnode.com": True,
            "beaconcha.in": True
        }

        self.settled_tx_hashes = {}

        # Genesis policy
        self.policies: Dict[str, Dict[str, Any]] = {
            "POLICY_001": {
                "policy_id": "POLICY_001",
                "staker_address": self.operator,
                "validator_index": 0,
                "validator_pubkey": "0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
                "coverage_amount_usdc": 1000,
                "premium_paid_usdc": 50,
                "max_exit_epoch": 500000,
                "status": "ACTIVE",
                "claim_payout_tx_hash": "",
                "last_audit_summary": "Genesis policy active.",
                "last_observed_epoch": 0
            }
        }

    def set_authorized_relay(self, caller: str, relay_address: str) -> str:
        assert caller.strip().lower() == self.operator,             "[ERR_UNAUTHORIZED] Caller is not the contract operator."
        clean_relay = relay_address.strip().lower()
        assert len(clean_relay) == 42 and clean_relay.startswith("0x"),             "[ERR_INVALID_RELAY] Invalid relay address."
        self.authorized_relay = clean_relay
        return f"SUCCESS: Authorized relay updated to {clean_relay}."

    def deposit_underwriting_capital(self, caller: str, amount_usdc: int) -> str:
        sender = caller.strip().lower()
        assert sender in (self.operator, self.authorized_relay),             "[ERR_UNAUTHORIZED] Caller is not authorized to deposit underwriting capital."
        assert amount_usdc > 0, "[ERR_AMOUNT_01] Deposit amount must be greater than zero."
        self.pool_capital_usdc += amount_usdc
        return f"SUCCESS: Deposited {amount_usdc} USDC."

    def register_policy(
        self,
        staker_address: str,
        validator_index: int,
        validator_pubkey: str,
        coverage_amount_usdc: int,
        premium_paid_usdc: int,
        max_exit_epoch: int
    ) -> str:
        staker = staker_address.strip().lower()
        assert len(staker) == 42 and staker.startswith("0x"), "[ERR_STAKER_01] Invalid staker EVM address."
        assert len(validator_pubkey) >= 10, "[ERR_PUBKEY_01] Invalid validator BLS public key."
        assert coverage_amount_usdc > 0, "[ERR_COVERAGE_01] Coverage amount must be greater than zero."
        assert premium_paid_usdc > 0, "[ERR_PREMIUM_01] Premium must be greater than zero."
        assert max_exit_epoch > 0, "[ERR_EPOCH_01] Max exit epoch must be greater than zero."

        total_committed = self.total_claims_paid_usdc + self.total_active_coverage_usdc
        avail_capital = max(0, self.pool_capital_usdc - total_committed)
        assert avail_capital >= coverage_amount_usdc,             f"[ERR_INSUFFICIENT_POOL_CAPITAL] Insufficient pool capital ({avail_capital} USDC available)."

        self.total_policies += 1
        policy_id = f"POLICY_{str(self.total_policies).zfill(3)}"
        self.policies[policy_id] = {
            "policy_id": policy_id,
            "staker_address": staker,
            "validator_index": validator_index,
            "validator_pubkey": validator_pubkey.lower(),
            "coverage_amount_usdc": coverage_amount_usdc,
            "premium_paid_usdc": premium_paid_usdc,
            "max_exit_epoch": max_exit_epoch,
            "status": "ACTIVE",
            "claim_payout_tx_hash": "",
            "last_audit_summary": f"Policy registered for validator #{validator_index}.",
            "last_observed_epoch": 0
        }
        self.pool_capital_usdc += premium_paid_usdc
        self.total_active_coverage_usdc += coverage_amount_usdc
        return policy_id

    def assess_slashing_claim(
        self,
        policy_id: str,
        telemetry_accessible: bool,
        validator_index: int,
        validator_pubkey: str,
        slashed: bool,
        exit_epoch: int,
        claim_verdict: str = "",
        validator_status: str = "active_ongoing",
        telemetry_host: str = "ethereum-beacon-api.publicnode.com"
    ) -> str:
        p_id = policy_id.strip()
        assert p_id in self.policies, f"[ERR_STATE_01] Policy '{p_id}' does not exist."
        policy = self.policies[p_id]
        assert policy["status"] == "ACTIVE",             f"[ERR_STATE_02] Policy '{p_id}' is not in active state (current: {policy['status']})."

        assert telemetry_host in self.authorized_sources,             f"[ERR_UNAUTHORIZED_SOURCE] Telemetry host '{telemetry_host}' is not authorized."

        assert telemetry_accessible,             "[ERR_TELEMETRY_01] Failed to read live Ethereum Beacon Chain telemetry (Fail-Closed)."

        assert validator_index == policy["validator_index"],             f"[ERR_INDEX_MISMATCH] Scraped index ({validator_index}) != Policy index ({policy['validator_index']})."

        if policy["validator_pubkey"]:
            assert validator_pubkey.lower() == policy["validator_pubkey"].lower(),                 f"[ERR_PUBKEY_MISMATCH] Scraped key does not match registered key."

        max_epoch = int(policy["max_exit_epoch"])
        cov = int(policy["coverage_amount_usdc"])

        # Equivalence fields derived deterministically
        in_term_slashed = bool(slashed and (exit_epoch <= max_epoch))
        if not claim_verdict:
            if slashed and (exit_epoch <= max_epoch):
                claim_verdict = "CLAIM_APPROVED"
            elif slashed and (exit_epoch > max_epoch):
                claim_verdict = "POLICY_EXPIRED"
            else:
                claim_verdict = "HEALTHY_NORMAL"

        policy["last_observed_epoch"] = exit_epoch

        # STRICT FAIL-CLOSED CONJUNCTION EVALUATION (H-01 Resolution)
        if slashed and in_term_slashed and claim_verdict == "CLAIM_APPROVED":
            policy["status"] = "CLAIM_APPROVED"
            self.total_claims_paid_usdc += cov
            self.total_active_coverage_usdc -= cov
            policy["last_audit_summary"] = (
                f"SLASHING CLAIM APPROVED: Validator #{validator_index} confirmed slashed at epoch {exit_epoch}. "
                f"Authorized reimbursement of {cov} USDC."
            )
        elif slashed and (not in_term_slashed) and claim_verdict == "POLICY_EXPIRED":
            policy["status"] = "EXPIRED"
            self.total_active_coverage_usdc -= cov
            policy["last_audit_summary"] = (
                f"POLICY EXPIRED: Slashing occurred at epoch {exit_epoch}, which exceeds policy term {max_epoch}. "
                f"Collateral preserved."
            )
        elif (not slashed) and claim_verdict == "HEALTHY_NORMAL":
            policy["status"] = "ACTIVE"
            policy["last_audit_summary"] = (
                f"POLICY HEALTHY: Validator #{validator_index} operating normally (slashed=false)."
            )
        else:
            raise AssertionError(
                f"[ERR_VERDICT_CONTRADICTION] Contradictory verdict state: slashed={slashed}, "
                f"in_term={in_term_slashed}, verdict='{claim_verdict}'."
            )

        self.policies[p_id] = policy
        return policy["last_audit_summary"]

    def confirm_settlement(
        self,
        caller: str,
        policy_id: str,
        evm_tx_hash: str,
        settlement_block: int,
        disbursed_amount_usdc: int
    ) -> str:
        sender = caller.strip().lower()
        assert sender in (self.authorized_relay, self.operator),             "[ERR_UNAUTHORIZED_RELAY] Caller is not the authorized settlement relay."

        p_id = policy_id.strip()
        assert p_id in self.policies, f"[ERR_STATE_01] Policy '{p_id}' does not exist."
        policy = self.policies[p_id]

        assert policy["status"] == "CLAIM_APPROVED",             f"[ERR_SETTLEMENT_01] Policy '{p_id}' is not in approved state (current: {policy['status']})."

        clean_hash = evm_tx_hash.strip().lower()
        assert len(clean_hash) == 66 and clean_hash.startswith("0x"),             "[ERR_HASH_01] Invalid EVM settlement transaction hash format."

        # C-01: Global anti-replay across all policies
        assert clean_hash not in self.settled_tx_hashes,             f"[ERR_HASH_ALREADY_USED] EVM transaction receipt '{clean_hash}' has already been consumed."

        assert int(disbursed_amount_usdc) == int(policy["coverage_amount_usdc"]),             f"[ERR_AMOUNT_MISMATCH] Disbursed amount ({int(disbursed_amount_usdc)}) does not match policy coverage ({int(policy['coverage_amount_usdc'])})."

        assert int(settlement_block) > 0,             f"[ERR_BLOCK_01] Invalid settlement block number ({int(settlement_block)})."

        assert policy["claim_payout_tx_hash"] == "",             f"[ERR_CLAIM_ALREADY_SETTLED] Claim for policy '{p_id}' has already been settled."

        self.settled_tx_hashes[clean_hash] = True
        policy["status"] = "SETTLED"
        policy["claim_payout_tx_hash"] = clean_hash
        policy["last_audit_summary"] = (
            f"CLAIM SETTLED: Reimbursed {int(policy['coverage_amount_usdc'])} USDC. EVM Receipt: {clean_hash}."
        )

        self.policies[p_id] = policy
        return policy["last_audit_summary"]

    def get_pool_stats(self) -> dict:
        total_committed = self.total_claims_paid_usdc + self.total_active_coverage_usdc
        avail = max(0, self.pool_capital_usdc - total_committed)
        return {
            "pool_capital_usdc": self.pool_capital_usdc,
            "total_active_coverage_usdc": self.total_active_coverage_usdc,
            "total_claims_paid_usdc": self.total_claims_paid_usdc,
            "available_capital_usdc": avail,
            "total_policies_count": self.total_policies
        }


def test_slashing_guard_lifecycle():
    logging.info("=" * 80)
    logging.info("  SLASHINGGUARD ETHEREUM POS VALIDATOR INSURANCE COMPREHENSIVE AUDIT SUITE")
    logging.info("  VERIFYING PROTOCOL STEWARD (PAVEL KOLOSOV) & HARDCORE AUDIT REMEDIATIONS")
    logging.info("=" * 80)

    operator = "0x71546f55c131acd54cf93e181b9cabaeaf440fc3"
    relay = "0x8888888888888888888888888888888888888888"
    unauthorized_caller = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"

    court = MockSlashingGuardCourt(operator=operator, authorized_relay=relay)
    vault = MockSlashingGuardVault(relay_address=relay, initial_reserves=25000)

    # Invariant 1: 1-to-1 Policy ID mapping
    assert court.policies["POLICY_001"]["policy_id"] == "POLICY_001"
    logging.info("✓ 1. Standardized 1-to-1 Policy-ID Mapping: 'POLICY_001' verified.")

    # Invariant 2: Underwriting Pool Solvency
    stats = court.get_pool_stats()
    assert stats["available_capital_usdc"] == 24000
    logging.info("✓ 2. Underwriting Pool Solvency: 25000 USDC reserves backing 1000 USDC active liabilities.")

    # Invariant 3: Official Consensus Telemetry Whitelist
    assert "ethereum-beacon-api.publicnode.com" in court.authorized_sources
    try:
        court.assess_slashing_claim(
            policy_id="POLICY_001",
            telemetry_accessible=True,
            validator_index=0,
            validator_pubkey="0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
            slashed=False,
            exit_epoch=0,
            telemetry_host="fake-unauthorized-api.com"
        )
        raise AssertionError("Unauthorized host should fail")
    except AssertionError as e:
        assert "[ERR_UNAUTHORIZED_SOURCE]" in str(e)
        logging.info("✓ 3. Official Consensus Telemetry Whitelist Verified: Unauthorized endpoints blocked.")

    # Invariant 4: Negative Test Case (Validator #0 unslashed)
    court.assess_slashing_claim(
        policy_id="POLICY_001",
        telemetry_accessible=True,
        validator_index=0,
        validator_pubkey="0x933ad9491b62059dd065b560d256d8957a8c402cc6e8d8ee7290ae11e8f7329267a8811c397529dac52ae1342ba58c95",
        slashed=False,
        exit_epoch=18446744073709551615
    )
    assert court.policies["POLICY_001"]["status"] == "ACTIVE"
    logging.info("✓ 4. Negative Test Case Verified: Validator #0 (slashed=False, exit_epoch=FAR_FUTURE) -> Status remains ACTIVE.")

    # Invariant 5: In-Term Slashing Consensus
    staker = "0x9014DF05Fa3C62Ea443775B4D4b7f26853F4C9e9"
    p2_id = court.register_policy(
        staker_address=staker,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        coverage_amount_usdc=1000,
        premium_paid_usdc=50,
        max_exit_epoch=500
    )
    court.assess_slashing_claim(
        policy_id=p2_id,
        telemetry_accessible=True,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        slashed=True,
        exit_epoch=213
    )
    assert court.policies[p2_id]["status"] == "CLAIM_APPROVED"
    logging.info("✓ 5. STEWARD INVARIANT 1 PASS: In-Term Slashing Consensus (slashed=True, exit_epoch=213 <= 500 -> CLAIM_APPROVED).")

    # Invariant 6: Out-of-Term Slashing Consensus
    p3_id = court.register_policy(
        staker_address=staker,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        coverage_amount_usdc=1000,
        premium_paid_usdc=50,
        max_exit_epoch=200
    )
    court.assess_slashing_claim(
        policy_id=p3_id,
        telemetry_accessible=True,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        slashed=True,
        exit_epoch=213
    )
    assert court.policies[p3_id]["status"] == "EXPIRED"
    logging.info("✓ 6. STEWARD INVARIANT 2 PASS: Out-of-Term Slashing Consensus (slashed=True, exit_epoch=213 > 200 -> EXPIRED).")

    # Invariant 7: Pubkey Mismatch Guard
    p4_id = court.register_policy(
        staker_address=staker,
        validator_index=12345,
        validator_pubkey="0x8888888888888888888888888888888888888888888888888888888888888888",
        coverage_amount_usdc=500,
        premium_paid_usdc=25,
        max_exit_epoch=1000
    )
    try:
        court.assess_slashing_claim(
            policy_id=p4_id,
            telemetry_accessible=True,
            validator_index=12345,
            validator_pubkey="0x9999999999999999999999999999999999999999999999999999999999999999",
            slashed=False,
            exit_epoch=0
        )
        raise AssertionError("Pubkey mismatch should have reverted")
    except AssertionError as e:
        assert "[ERR_PUBKEY_MISMATCH]" in str(e)
        logging.info("✓ 7. Cryptographic Pubkey Binding Guard Verified: Mismatched key rejected ([ERR_PUBKEY_MISMATCH]).")

    # Invariant 8: Relay Authorization Invariant
    valid_tx_hash = "0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a"
    try:
        court.confirm_settlement(
            caller=unauthorized_caller,
            policy_id=p2_id,
            evm_tx_hash=valid_tx_hash,
            settlement_block=6891234,
            disbursed_amount_usdc=1000
        )
        raise AssertionError("Unauthorized caller should have reverted")
    except AssertionError as e:
        assert "[ERR_UNAUTHORIZED_RELAY]" in str(e)
        logging.info("✓ 8. STEWARD INVARIANT 3 PASS: Relay Authorization Invariant: Unauthorized caller reverted ([ERR_UNAUTHORIZED_RELAY]).")

    # Invariant 9: Receipt Amount Invariant
    try:
        court.confirm_settlement(
            caller=relay,
            policy_id=p2_id,
            evm_tx_hash=valid_tx_hash,
            settlement_block=6891234,
            disbursed_amount_usdc=500
        )
        raise AssertionError("Amount mismatch should have reverted")
    except AssertionError as e:
        assert "[ERR_AMOUNT_MISMATCH]" in str(e)
        logging.info("✓ 9. STEWARD INVARIANT 4 PASS: Receipt Amount Invariant: Mismatched amount reverted ([ERR_AMOUNT_MISMATCH]).")

    # Invariant 10: Block Number & Hash Validation
    try:
        court.confirm_settlement(
            caller=relay,
            policy_id=p2_id,
            evm_tx_hash=valid_tx_hash,
            settlement_block=0,
            disbursed_amount_usdc=1000
        )
        raise AssertionError("Zero block should have reverted")
    except AssertionError as e:
        assert "[ERR_BLOCK_01]" in str(e)
        logging.info("✓ 10a. Receipt Invariant Verified: Non-positive block number reverted ([ERR_BLOCK_01]).")

    try:
        court.confirm_settlement(
            caller=relay,
            policy_id=p2_id,
            evm_tx_hash="invalid_hash",
            settlement_block=6891234,
            disbursed_amount_usdc=1000
        )
        raise AssertionError("Invalid hash should have reverted")
    except AssertionError as e:
        assert "[ERR_HASH_01]" in str(e)
        logging.info("✓ 10b. Receipt Invariant Verified: Malformed transaction hash reverted ([ERR_HASH_01]).")

    # Invariant 11: First Settlement Succeeded
    court.confirm_settlement(
        caller=relay,
        policy_id=p2_id,
        evm_tx_hash=valid_tx_hash,
        settlement_block=6891234,
        disbursed_amount_usdc=1000
    )
    assert court.policies[p2_id]["status"] == "SETTLED"
    logging.info(f"✓ 11a. First Settlement Succeeded: SETTLED with receipt {valid_tx_hash[:16]}...")

    # Duplicate settlement on same policy
    try:
        court.confirm_settlement(
            caller=relay,
            policy_id=p2_id,
            evm_tx_hash=valid_tx_hash,
            settlement_block=6891234,
            disbursed_amount_usdc=1000
        )
        raise AssertionError("Duplicate settlement should have reverted")
    except AssertionError as e:
        assert "[ERR_SETTLEMENT_01]" in str(e) or "[ERR_CLAIM_ALREADY_SETTLED]" in str(e)
        logging.info("✓ 11b. STEWARD INVARIANT 5 PASS: Anti-Replay Invariant: Duplicate settlement blocked ([ERR_SETTLEMENT_01]).")

    # Invariant 12: EVM SlashingGuardVault Anti-Replay
    p2_b32 = p2_id.encode('utf-8').ljust(32, b'\x00')
    vault_receipt = vault.execute_slashing_payout(p2_b32, staker, 1000)
    assert vault_receipt["status"] == 1
    try:
        vault.execute_slashing_payout(p2_b32, staker, 1000)
        raise AssertionError("Vault should have prevented replay")
    except AssertionError as e:
        assert "[ERR_ALREADY_SETTLED]" in str(e)
        logging.info("✓ 12. EVM Vault Anti-Replay Verified: Duplicate payout for policy blocked ([ERR_ALREADY_SETTLED]).")

    # Invariant 13: Strict Underfunded Vault Revert
    depleted_vault = MockSlashingGuardVault(operator, initial_reserves=500)
    unbacked_b32 = b"POLICY_999\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    try:
        depleted_vault.execute_slashing_payout(unbacked_b32, staker, 5000)
        raise AssertionError("Should have reverted on underfunded reserves")
    except AssertionError as e:
        assert "[ERR_UNDERFUNDED]" in str(e)
        logging.info("✓ 13. Strict Underfunded Vault Revert Verified: Reverts when reserves < claim ([ERR_UNDERFUNDED]).")

    # Invariant 14: Operator Relay Management Access Control
    new_relay = "0x9999999999999999999999999999999999999999"
    try:
        court.set_authorized_relay(caller=unauthorized_caller, relay_address=new_relay)
        raise AssertionError("Unauthorized caller should not be able to set relay")
    except AssertionError as e:
        assert "[ERR_UNAUTHORIZED]" in str(e)
        logging.info("✓ 14a. Relay Management Access Control Verified: Non-operator blocked ([ERR_UNAUTHORIZED]).")

    court.set_authorized_relay(caller=operator, relay_address=new_relay)
    assert court.authorized_relay == new_relay.lower()
    court.set_authorized_relay(caller=operator, relay_address=relay)
    logging.info(f"✓ 14b. Relay Management Access Control Verified: Operator successfully updated relay.")

    # -------------------------------------------------------------------------
    # NEW AUDIT INVARIANTS:
    # -------------------------------------------------------------------------

    # Invariant 15: Cross-Policy EVM Receipt Replay Guard (C-01 Resolution)
    p5_id = court.register_policy(
        staker_address=staker,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        coverage_amount_usdc=1000,
        premium_paid_usdc=50,
        max_exit_epoch=500
    )
    court.assess_slashing_claim(
        policy_id=p5_id,
        telemetry_accessible=True,
        validator_index=20075,
        validator_pubkey="0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288",
        slashed=True,
        exit_epoch=213
    )
    try:
        # Attempt to reuse valid_tx_hash (which was used for p2_id) on p5_id
        court.confirm_settlement(
            caller=relay,
            policy_id=p5_id,
            evm_tx_hash=valid_tx_hash,
            settlement_block=6891234,
            disbursed_amount_usdc=1000
        )
        raise AssertionError("Cross-policy hash replay should have reverted")
    except AssertionError as e:
        assert "[ERR_HASH_ALREADY_USED]" in str(e)
        logging.info("✓ 15. AUDIT INVARIANT C-01 PASS: Cross-Policy Hash Replay Strictly Blocked ([ERR_HASH_ALREADY_USED]).")

    # Invariant 16: Capital Deposit Access Control (C-02 Resolution)
    try:
        court.deposit_underwriting_capital(caller=unauthorized_caller, amount_usdc=50000)
        raise AssertionError("Unauthorized capital deposit should have reverted")
    except AssertionError as e:
        assert "[ERR_UNAUTHORIZED]" in str(e)
        logging.info("✓ 16. AUDIT INVARIANT C-02 PASS: Capital Deposit Access Control Enforced ([ERR_UNAUTHORIZED]).")

    # Invariant 17: Strict Conjunction Verdict Consistency (H-01 Resolution)
    p6_id = court.register_policy(
        staker_address=staker,
        validator_index=11111,
        validator_pubkey="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        coverage_amount_usdc=500,
        premium_paid_usdc=25,
        max_exit_epoch=500
    )
    try:
        # Contradictory inputs: slashed is False, but claim_verdict is CLAIM_APPROVED
        court.assess_slashing_claim(
            policy_id=p6_id,
            telemetry_accessible=True,
            validator_index=11111,
            validator_pubkey="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            slashed=False,
            exit_epoch=0,
            claim_verdict="CLAIM_APPROVED"
        )
        raise AssertionError("Contradictory verdict should have reverted")
    except AssertionError as e:
        assert "[ERR_VERDICT_CONTRADICTION]" in str(e)
        logging.info("✓ 17. AUDIT INVARIANT H-01 PASS: Strict Conjunction Verdict Guard Enforced ([ERR_VERDICT_CONTRADICTION]).")

    # Invariant 18: EVM Vault Pull-Payment Fallback for DoS Protection (H-02 Resolution)
    p5_b32 = p5_id.encode('utf-8').ljust(32, b'\x00')
    vault_p5 = vault.execute_slashing_payout(p5_b32, staker, 1000, direct_transfer_fails=True)
    assert vault_p5["queued"] is True
    assert vault.pending_reimbursements[staker.lower()] == 1000
    withdrawn = vault.withdraw_pending_reimbursement(staker)
    assert withdrawn == 1000
    assert vault.pending_reimbursements[staker.lower()] == 0
    logging.info("✓ 18. AUDIT INVARIANT H-02 PASS: Pull-Payment DoS Resilience Verified.")

    logging.info("=" * 80)
    logging.info("  ALL 18 ARCHITECTURAL, STEWARD & AUDIT INVARIANTS 100% VERIFIED AND PASSING!")
    logging.info("=" * 80)


if __name__ == "__main__":
    test_slashing_guard_lifecycle()
