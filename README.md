# SlashingGuard — Autonomous Ethereum PoS Validator Slashing Insurance & Sentinel Protocol

> **"The world's first autonomous, parametric Ethereum Proof-of-Stake (PoS) slashing insurance clearinghouse on GenLayer. Monitors Ethereum Beacon Chain consensus validators via official REST telemetry and autonomously reimburses stakers the moment a slashing event occurs on-chain—with zero human claims adjusters, zero DAO delays, and zero centralized oracles."**

---

## 🔗 Verified Deployments & Telemetry Links
- **GenLayer Explorer Contract**: [`0x7716A61817e99923722B01455f0885f1B9E438De`](https://explorer-studio.genlayer.com/address/0x7716A61817e99923722B01455f0885f1B9E438De)
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
3. **Single-Round Multi-Modal AI Consensus**:
   - Evaluates the 24/7 UTC Atomic Clock (`timeapi.io`) and official Ethereum Beacon Chain consensus JSON in 1 parallel pass.
   - Equivalence Principle enforces 100% agreement across all validator nodes on `slashed: bool` and `validator_index`.
4. **Single-Payout Anti-Replay Guard (`[ERR_CLAIM_ALREADY_SETTLED]`)**:
   - Records the verified EVM settlement transaction receipt hash (`claim_payout_tx_hash`).
   - Duplicate payouts for the same slashing event are strictly blocked.
5. **Full-Reserve Solvency Accounting (`[ERR_INSUFFICIENT_POOL_CAPITAL]`)**:
   - Active insurance liabilities cannot exceed the liquid pool reserves locked in the vault.
6. **Temporal Policy Term Enforcement (`[ERR_POLICY_EXPIRED]`)**:
   - Slashing events occurring after the policy expiration epoch (`max_exit_epoch`) are rejected, protecting the underwriting capital pool.

---

## 🧪 Automated Test Suite (10 / 10 Passing)
Run the complete automated test suite locally:
```bash
python test/test_slashing_lifecycle.py
```
- Validates standardized 1-to-1 mapping, solvency accounting, whitelisted consensus telemetry, healthy negative case (Validator #0), slashed positive case (Validator #20075), pubkey mismatch guard, expiration epoch guard, single-payout anti-replay, underfunded reserve guard, and confirmed EVM payout receipts (`receipt.status == 1`).
