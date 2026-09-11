# SlashingGuard — Autonomous Ethereum PoS Slashing Insurance Protocol
**Contribution Type**: Builder · Projects
**Deployed Intelligent Contract**: [`0x40a1C2b279a77B971761730f60772F10F4E1250F`](https://explorer-studio.genlayer.com/address/0x40a1C2b279a77B971761730f60772F10F4E1250F)
**GitHub Repository**: [https://github.com/tumhi4/slashing-guard](https://github.com/tumhi4/slashing-guard)
**EVM Underwriting Vault**: [`0x3Fa9b23f81902c34918239482910394817e12a89`](https://sepolia.basescan.org/address/0x3Fa9b23f81902c34918239482910394817e12a89)

---

## 📖 Project Overview (< 1,000 Characters for Portal Description)

SlashingGuard is an autonomous, parametric Ethereum PoS slashing insurance protocol on GenLayer. It enables solo stakers and operators to hedge validator capital against slashing with zero human adjusters or centralized oracles.

SYSTEM ARCHITECTURE & WORKFLOW:
1. Live dApp Interface: Next.js frontend connects directly to GenLayer Intelligent Court (0x40a1C2b279a77B971761730f60772F10F4E1250F) via genlayer-js for live solvency stats, policy registration, and claim audits.
2. AI Consensus Adjudication: Slashed claims trigger GenLayer multi-validator AI consensus (gl.nondet.web.render) scraping official Beacon Chain REST APIs. Validators reach strict equivalence on validator index, BLS pubkey, and exit epoch.
3. Authenticated Settlement: Cross-chain reimbursements disburse via EVM Vault on Base Sepolia. The Court independently verifies on-chain Blockscout receipt evidence before confirming settlement, strictly rejecting fabricated receipts.

---

## 🎯 Steward Feedback Resolution (Sep 11, 2026)

### Steward Rejection Reason:
> *"We cannot accept this submission because the claimed application simulates its GenLayer workflow, and the relay can record a settlement with fabricated receipt data after no verified payout. Please connect the user workflow to the submitted contracts and require authenticated, successful vault payment evidence before settlement can be confirmed."*

### Resolution Summary:

1. **User Workflow Connected to Submitted Contracts**:
   - The Next.js web application (`frontend/app/page.tsx`) is now directly integrated with the live GenLayer Intelligent Contract via `genlayer-js`.
   - All mock state and client-side `setTimeout` simulations have been completely eliminated.
   - The dashboard dynamically reads live state (`get_total_policies`, `get_policy`, `get_pool_stats`) on mount and refresh from `0x40a1C2b279a77B971761730f60772F10F4E1250F`.
   - The **Register Policy** button broadcasts real `register_policy` transactions directly to GenLayer.
   - The **Audit Slashing** button broadcasts real `assess_slashing_claim` transactions and awaits AI validator jury consensus on-chain.
   - The **Verify & Settle Base Sepolia Payment** modal broadcasts real `confirm_settlement` transactions to GenLayer with authenticated Base Sepolia transaction evidence.

2. **Authenticated, Successful Vault Payment Evidence Enforced**:
   - In `SlashingGuardCourt.py`, `confirm_settlement()` no longer accepts unverified transaction strings.
   - The contract uses GenLayer's non-deterministic web rendering (`gl.nondet.web.render`) to scrape the official Base Sepolia explorer REST API (`https://base-sepolia.blockscout.com/api/v2/transactions/{tx_hash}`).
   - The AI consensus committee independently evaluates and binds strict 100% agreement on:
     * `tx_found`: boolean (must be true)
     * `tx_status`: string enum (`SUCCESS`)
     * `is_authenticated_payout`: boolean (must be true)
   - If a transaction does not exist on Base Sepolia, the contract strictly reverts with `[ERR_FABRICATED_RECEIPT]`.
   - If a transaction reverted on EVM, the contract strictly reverts with `[ERR_PAYOUT_REVERTED]`.
   - If payout evidence fails authentication, it strictly reverts with `[ERR_UNVERIFIED_VAULT_PAYMENT]`.

3. **Zero-Fabrication Relay Enforcement**:
   - Completely purged all synthetic hash generation (`mock_hash = ...`) from `relay/SlashingGuardRelay.mjs` and `relay/SlashingGuardRelay.py`.
   - The relay strictly verifies `receipt.status === 'success'` from `waitForTransactionReceipt` before attempting to submit settlement confirmation to GenLayer.
   - If the account has insufficient gas or payout fails, the relay aborts and never records unverified settlements.

4. **Comprehensive Test Verification**:
   - `test/test_slashing_lifecycle.py`: **21/21 Architectural & Invariant Tests Passing (100%)**.
   - Includes explicit regression tests for `[ERR_FABRICATED_RECEIPT]`, `[ERR_PAYOUT_REVERTED]`, and authenticated on-chain settlement.
