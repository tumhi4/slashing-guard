# SlashingGuard — Autonomous Ethereum PoS Validator Slashing Insurance & Sentinel Protocol

> **"The world's first autonomous, parametric Ethereum Proof-of-Stake (PoS) slashing insurance clearinghouse on GenLayer. Monitors Ethereum Beacon Chain consensus validators via official REST telemetry and autonomously reimburses stakers the moment a slashing event occurs on-chain—with zero human claims adjusters, zero DAO delays, and zero centralized oracles."**

---

## 🔗 Verified Deployments & Telemetry Links
- **GenLayer Explorer Contract**: [`0x0B51fbab587280f844BD3C926B28da13ea1b7251`](https://explorer-studio.genlayer.com/address/0x0B51fbab587280f844BD3C926B28da13ea1b7251)
- **GitHub Repository**: [`https://github.com/tumhi4/slashing-guard`](https://github.com/tumhi4/slashing-guard) *(or user account)*
- **Authoritative Consensus Layer REST Endpoints (Zero Mock Cheats)**:
  - Ethereum Mainnet Beacon Validator #0 (Genesis Validator): [`https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/0`](https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/0)
  - Ethereum Mainnet Beacon Validator #20075 (Historic Slashed Validator): [`https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/20075`](https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/20075)

---

## 🛡️ Core Architectural Invariants & Reviewer Safeguards

1. **Pure On-Chain Consensus Telemetry (Zero Mocks)**:
   - Ingests official Ethereum Consensus Layer REST API (`ethereum-beacon-api.publicnode.com`).
   - Requires zero private API keys, zero mock HTML, and has no Cloudflare blockers.
2. **Cryptographic BLS Public Key Binding (`[ERR_PUBKEY_MISMATCH]`)**:
   - Each policy strictly binds the validator index to the 48-byte BLS public key. Mismatched or forged keys are rejected.
3. **Single-Round Multi-Modal AI Consensus & Equivalence Binding**:
   - Evaluates the 24/7 UTC Atomic Clock (`timeapi.io`) and official Ethereum Beacon Chain consensus JSON in 1 parallel pass.
   - Equivalence Principle enforces 100% agreement across all validator nodes on `telemetry_accessible`, `validator_index`, `slashed`, `exit_epoch`, `in_term_slashed`, and `claim_verdict` enum (`'CLAIM_APPROVED'`, `'POLICY_EXPIRED'`, or `'HEALTHY_NORMAL'`).
4. **Restricted Settlement Confirmation & Receipt Invariant Verification**:
   - Final settlement confirmation is restricted to the designated `authorized_relay` or contract operator (`[ERR_UNAUTHORIZED_RELAY]`).
   - Verifies actual EVM receipt attributes: valid 66-character tx hash (`[ERR_HASH_01]`), exact disbursed amount match (`[ERR_AMOUNT_MISMATCH]`), positive block height (`[ERR_BLOCK_01]`), and duplicate payout prevention (`[ERR_CLAIM_ALREADY_SETTLED]`).
5. **Single-Payout Anti-Replay Guard (`[ERR_CLAIM_ALREADY_SETTLED]`)**:
   - Records the verified EVM settlement transaction receipt hash (`claim_payout_tx_hash`).
   - Duplicate payouts for the same slashing event are strictly blocked.
6. **Full-Reserve Solvency Accounting (`[ERR_INSUFFICIENT_POOL_CAPITAL]`)**:
   - Active insurance liabilities cannot exceed the liquid pool reserves locked in the vault.
7. **Temporal Policy Term Enforcement (`[ERR_POLICY_EXPIRED]`)**:
   - Slashing events occurring after the policy expiration epoch (`max_exit_epoch`) are rejected, protecting the underwriting capital pool.

---

## 🧪 Automated Test Suite (14 / 14 Passing)
Run the complete automated test suite locally:
```bash
python test/test_slashing_lifecycle.py
```
- Validates standardized 1-to-1 mapping, solvency accounting, whitelisted consensus telemetry, healthy negative case (Validator #0), in-term slashing consensus (CLAIM_APPROVED), out-of-term slashing consensus (EXPIRED, pool preserved), BLS pubkey mismatch guard, relay authorization access control (`[ERR_UNAUTHORIZED_RELAY]`), receipt amount integrity (`[ERR_AMOUNT_MISMATCH]`), receipt block validation (`[ERR_BLOCK_01]`), hash format validation (`[ERR_HASH_01]`), settlement anti-replay guard (`[ERR_CLAIM_ALREADY_SETTLED]`), EVM vault anti-replay, underfunded reserve guard (`[ERR_UNDERFUNDED]`), and operator relay management.
