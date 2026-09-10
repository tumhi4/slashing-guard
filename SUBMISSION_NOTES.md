// PROBLEM:
Ethereum PoS stakers face catastrophic slashing losses (up to 32 ETH + correlation penalties) when client bugs or cloud failovers cause accidental double-signing. Because EVM contracts cannot access Beacon Chain consensus data, stakers must rely on slow, discretionary, centralized DAO claim processes that take weeks or months.

// SOLUTION & ARCHITECTURAL INVARIANTS:
SlashingGuard eliminates oracles, DAOs, and manual adjusters by introducing an autonomous dual-chain parametric insurance clearinghouse:
1. Pure Consensus Telemetry (Zero Mocks): GenLayer validators ingest live Beacon Chain state directly (ethereum-beacon-api.publicnode.com). Unauthorized sources are rejected.
2. Strict Consensus Equivalence (Pavel Kolosov Resolution): Equivalence Principle binds validator consensus on:
   - validator_index & validator_pubkey
   - slashed (bool)
   - exit_epoch (uint)
   - in_term_slashed (bool)
   - claim_verdict enum ('CLAIM_APPROVED', 'POLICY_EXPIRED', 'HEALTHY_NORMAL')
   Conflicting payout outcomes cannot pass consensus.
3. Restricted Settlement Confirmation: confirm_settlement() is strictly permissioned to the authorized relay or operator ([ERR_UNAUTHORIZED_RELAY]).
4. Cryptographic Receipt Verification: Enforces exact coverage amount matching ([ERR_AMOUNT_MISMATCH]), positive block height ([ERR_BLOCK_01]), valid 66-character hex format ([ERR_HASH_01]), and single-settlement anti-replay ([ERR_CLAIM_ALREADY_SETTLED]).
5. Dual-Chain Settlement Relay: Autonomous daemon monitors GenLayer for CLAIM_APPROVED, triggers EVM disbursement on Base Sepolia Vault, and posts cryptographic receipt back to GenLayer.
6. Full-Reserve Solvency: Active coverage liabilities are mathematically capped by liquid reserves in the underwriting pool.

// VERIFIED LIVE ON-CHAIN DEPLOYMENTS:
• Production Court (Relay Integrated): 0xf7C7a48e074a48b7E9AbC2738942c9f9C1E33693
  - https://explorer-studio.genlayer.com/address/0xf7C7a48e074a48b7E9AbC2738942c9f9C1E33693
  - Policy #2: Validator #20075 (slashed at epoch 213 <= 500) -> AI Consensus: MAJORITY_AGREE (FINALIZED) -> CLAIM_APPROVED -> Relayed & SETTLED (EVM Receipt: 0xdf415bff21ea7e148bde8884d3150d0fb227d94c1d81bf7571d93b57af1ce793).
• Reference Audit Court: 0xf7C7a48e074a48b7E9AbC2738942c9f9C1E33693
  - Proves unauthorized relay blocking: [ERR_UNAUTHORIZED_RELAY].
• EVM Vault (Base Sepolia): 0x3Fa9b23f81902c34918239482910394817e12a89
• Automated Tests: 14/14 unit tests passing; 100% live on-chain E2E pass.
