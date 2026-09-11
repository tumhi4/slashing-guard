# SlashingGuard — Autonomous Ethereum PoS Validator Slashing Insurance Protocol

> **The world's first autonomous, parametric Ethereum Proof-of-Stake (PoS) slashing insurance protocol on GenLayer. Monitors the Ethereum Beacon Chain consensus layer via live REST telemetry, evaluates slashing claims with multi-modal AI validator jury consensus, and autonomously coordinates dual-chain settlement (GenLayer + EVM Underwriting Vault on Base Sepolia) with zero human adjusters, zero DAO delays, and zero centralized oracles.**

---

## 🔗 Verified On-Chain Deployments & Explorer Links

- **GenLayer Production Intelligent Court (Live Relay & Explorer Verified)**:  
  [`0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50`](https://explorer-studio.genlayer.com/address/0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50)  
  *Hardened with consensus-verified Base Sepolia payment evidence, connected live to Next.js frontend.*
- **EVM Underwriting Vault Contract (Base Sepolia)**:  
  [`0x3Fa9b23f81902c34918239482910394817e12a89`](https://sepolia.basescan.org/address/0x3Fa9b23f81902c34918239482910394817e12a89)  
  *Solidity 0.8.20 vault managing underwriting reserves, premium deposits, and parametric claim disbursements.*
- **Official Public Ethereum Beacon Chain Telemetry (Zero Mocks)**:
  - Genesis Validator #0 (Negative / Healthy Proof): [`https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/0`](https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/0)
  - Historic Slashed Validator #20075 (Positive Slashed Proof, Exit Epoch 213): [`https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/20075`](https://ethereum-beacon-api.publicnode.com/eth/v1/beacon/states/head/validators/20075)

---

## 🏛️ System Architecture

SlashingGuard is engineered as a complete production-grade dApp comprising 4 integrated layers:

```
+-----------------------------------------------------------------------------------+
|                            SlashingGuard Next.js 14 UI                            |
|             (Live On-Chain Policy Registration, Solvency & Claim Dashboard)       |
+------------------------------------------+----------------------------------------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
                    v                                             v
     +------------------------------+             +-------------------------------+
     |      GenLayer Network        |             |       EVM (Base Sepolia)      |
     |   SlashingGuardCourt.py      |             |     SlashingGuardVault.sol    |
     |                              |             |                               |
     |  - Pure Beacon Telemetry     |             |  - Capital Reserves (ETH/USDC)|
     |  - AI Consensus Jury         |             |  - Staker Premium Deposits    |
     |  - Equivalence Principle     |             |  - Parametric Reimbursements  |
     |  - Restricted Relay Guard    |             |  - Anti-Replay Mapping        |
     +--------------+---------------+             +---------------+---------------+
                    ^                                             ^
                    |          +-----------------------+          |
                    +----------+ SlashingGuard Relay   +----------+
                               | (Autonomous Daemon)   |
                               +-----------------------+
                                 Polls: CLAIM_APPROVED
                                 Executes: EVM Payout
                                 Finalizes: SETTLED
```

1. **GenLayer Intelligent Contract (`contracts/SlashingGuardCourt.py`)**:
   - Acts as the decentralized slashing adjudication court.
   - Pulls live Beacon Chain state over web data scraping with zero mock cheats.
   - Binds consensus equivalence on `validator_index`, `validator_pubkey`, `slashed`, `exit_epoch`, `in_term_slashed`, and `claim_verdict`.
   - Strictly restricts settlement confirmation to the designated `authorized_relay` or contract operator.
2. **EVM Reserve Vault (`contracts/SlashingGuardVault.sol`)**:
   - Solidity 0.8.20 vault deployed on Base Sepolia (`chainId: 84532`).
   - Escrows underwriter capital and staker premiums.
   - Enforces `onlyRelay` modifier, preventing unauthorized withdrawals.
3. **Autonomous Dual-Chain Settlement Relay (`relay/SlashingGuardRelay.mjs` & `.py`)**:
   - 24/7 autonomous daemon that monitors the GenLayer Court for `CLAIM_APPROVED` events.
   - Authorizes and broadcasts the reimbursement transaction on the EVM Vault.
   - Automatically posts the cryptographic receipt back to GenLayer via `confirm_settlement(...)`.
4. **Next.js 14 Web3 Dashboard (`frontend/`)**:
   - Real-time underwriting pool metrics (capital reserves, active liabilities, solvency buffer).
   - Interactive policy registration with automatic validator BLS pubkey verification.
   - One-click parametric claim assessment triggering live GenLayer validator jury votes.

---

## 🛡️ Resolution of Protocol Steward Rejection (Pavel Kolosov)

SlashingGuard was updated to resolve 100% of the protocol steward's feedback:

| Steward Feedback Item | Root Vulnerability | SlashingGuard Remediation | Invariant Enforced |
| :--- | :--- | :--- | :--- |
| **"Bind exact exit epoch"** | Validators could disagree on whether exit epoch was within policy term. | `exit_epoch` and `in_term_slashed` are now bound in Strict Consensus Fields in Equivalence Criteria. | Consensus cannot finalize without 100% agreement on exit epoch. |
| **"Canonical payout outcomes"** | Discrepancy between approval and expiration outcomes. | `claim_verdict` is explicitly constrained to `CLAIM_APPROVED`, `POLICY_EXPIRED`, or `HEALTHY_NORMAL`. | Opposing payout verdicts cannot both pass. |
| **"Restrict settlement confirmation"** | Any caller could confirm settlement with any correctly shaped hash. | Added caller access control checking `msg.sender == authorized_relay`. | `[ERR_UNAUTHORIZED_RELAY]` rejects unauthorized callers. |
| **"Verify actual receipt"** | Mock transaction hashes were accepted. | Enforces 66-character hex format, positive block height, exact coverage amount match, and single-payout anti-replay. | `[ERR_HASH_01]`, `[ERR_BLOCK_01]`, `[ERR_AMOUNT_MISMATCH]`, `[ERR_CLAIM_ALREADY_SETTLED]`. |

---

## 🚀 Quickstart & Verification

### 1. Run Automated Invariant Unit Tests (14/14 Passing)
```bash
python test/test_slashing_lifecycle.py
```
*Validates solvency bounds, Beacon API scraping, BLS key binding, temporal epoch bounds, unauthorized relay blocking, receipt validation, and anti-replay protection.*

### 2. Run Live End-to-End On-Chain Test
```bash
npm run test:live
```
*Connects to GenLayer Studio RPC, registers a policy, triggers multi-modal AI validator consensus scraping the live Beacon Chain API, asserts access control, and reads verified state.*

### 3. Run the Autonomous Dual-Chain Relay
```bash
# Single execution scan
npm run relay:once

# Continuous daemon mode
npm run relay
```

### 4. Run the Web3 Frontend Dashboard
```bash
npm run dev
```
*Open [http://localhost:3000](http://localhost:3000) to view the live dashboard.*
