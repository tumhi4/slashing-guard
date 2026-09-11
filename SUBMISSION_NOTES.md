# SlashingGuard — Autonomous Ethereum PoS Slashing Insurance Protocol
**Contribution Type**: Builder · Projects
**Deployed Intelligent Contract**: [`0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50`](https://explorer-studio.genlayer.com/address/0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50)
**GitHub Repository**: [https://github.com/tumhi4/slashing-guard](https://github.com/tumhi4/slashing-guard)
**EVM Underwriting Vault**: [`0x3Fa9b23f81902c34918239482910394817e12a89`](https://sepolia.basescan.org/address/0x3Fa9b23f81902c34918239482910394817e12a89)

---

## 🎯 Steward Feedback Resolution (Sep 11, 2026)

### Steward Rejection Reason:
> *"We cannot accept this submission because the claimed application simulates its GenLayer workflow, and the relay can record a settlement with fabricated receipt data after no verified payout. Please connect the user workflow to the submitted contracts and require authenticated, successful vault payment evidence before settlement can be confirmed."*

### Resolution Summary:

1. **User Workflow Connected to Submitted Contracts**:
   - The Next.js web application (`frontend/app/page.tsx`) is now directly integrated with the live GenLayer Intelligent Contract via `genlayer-js`.
   - All mock state and client-side `setTimeout` simulations have been completely eliminated.
   - The dashboard dynamically reads live state (`get_total_policies`, `get_policy`, `get_pool_stats`) on mount and refresh from `0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50`.
   - The **Register Policy** button broadcasts real `register_policy` transactions directly to GenLayer.
   - The **Audit Slashing** button broadcasts real `assess_slashing_claim` transactions and awaits AI validator jury consensus on-chain.

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
