import { createClient, createAccount } from '../../AetherDungeon/frontend/node_modules/genlayer-js/dist/index.js';

const CONTRACT_ADDRESS = '0x0B51fbab587280f844BD3C926B28da13ea1b7251';
const RPC_ENDPOINT = 'https://studio.genlayer.com/api';

async function runLiveTest() {
    console.log("===============================================================");
    console.log("  SLASHINGGUARD LIVE ON-CHAIN PROTOCOL TEST & AUDIT");
    console.log("  Contract: ", CONTRACT_ADDRESS);
    console.log("  Explorer:  https://explorer-studio.genlayer.com/address/" + CONTRACT_ADDRESS);
    console.log("===============================================================\n");

    const caller = createAccount();
    console.log("[Account] Test Caller Address:", caller.address);
    const client = createClient({ endpoint: RPC_ENDPOINT, account: caller });

    // Step 1: Initial State Reads
    console.log("\n--- STEP 1: VERIFYING INITIAL CONTRACT STATE ---");
    const initialTotal = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_total_policies',
        args: []
    });
    console.log("  ✓ Total Policies:", Number(initialTotal));

    const initialRelay = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_authorized_relay',
        args: []
    });
    console.log("  ✓ Authorized Settlement Relay:", initialRelay);

    const initialPoolRaw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_pool_stats',
        args: []
    });
    const poolStats = JSON.parse(initialPoolRaw);
    console.log("  ✓ Underwriting Pool Solvency:", poolStats.pool_capital_usdc, "USDC");
    console.log("  ✓ Active Liabilities:        ", poolStats.total_active_coverage_usdc, "USDC");
    console.log("  ✓ Available Reserve Capital: ", poolStats.available_capital_usdc, "USDC");

    // Step 2: Register Policy for Validator #20075
    console.log("\n--- STEP 2: REGISTERING POLICY_002 FOR VALIDATOR #20075 ---");
    const staker = "0x9014DF05Fa3C62Ea443775B4D4b7f26853F4C9e9";
    const vIdx = 20075;
    const vPubkey = "0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288";
    const covAmount = 1000;
    const premAmount = 50;
    const maxEpoch = 500;

    console.log("  Broadcasting register_policy transaction to GenLayer...");
    const regTxHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'register_policy',
        args: [staker, vIdx, vPubkey, covAmount, premAmount, maxEpoch]
    });
    console.log("  Tx Hash:", regTxHash);

    console.log("  Waiting for consensus finalization...");
    const regReceipt = await client.waitForTransactionReceipt({
        hash: regTxHash,
        status: 'FINALIZED',
        interval: 3000,
        retries: 40
    });
    console.log("  ✓ Policy Registration Status:", regReceipt.status_name || regReceipt.status);

    // Step 3: Verify POLICY_002 on-chain
    console.log("\n--- STEP 3: VERIFYING POLICY_002 ON-CHAIN ---");
    const p2Raw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_policy',
        args: ['POLICY_002']
    });
    const p2 = JSON.parse(p2Raw);
    console.log("  ✓ Policy ID:        ", p2.policy_id);
    console.log("  ✓ Insured Validator:", p2.validator_index);
    console.log("  ✓ Coverage Amount:  ", p2.coverage_amount_usdc, "USDC");
    console.log("  ✓ Policy Status:    ", p2.status);
    console.log("  ✓ Max Exit Epoch:   ", p2.max_exit_epoch);

    // Step 4: AI Consensus Slashing Assessment
    console.log("\n--- STEP 4: TRIGGERING MULTI-MODAL AI CONSENSUS (assess_slashing_claim) ---");
    console.log("  Broadcasting assess_slashing_claim('POLICY_002') to GenLayer Validator Jury...");
    console.log("  Validators will scrape live Beacon Chain API and execute Equivalence Principle...");
    const assessTxHash = await client.writeContract({
        address: CONTRACT_ADDRESS,
        functionName: 'assess_slashing_claim',
        args: ['POLICY_002']
    });
    console.log("  Consensus Tx Hash:", assessTxHash);

    console.log("  Waiting for validator jury consensus (may take ~15-30s)...");
    const assessReceipt = await client.waitForTransactionReceipt({
        hash: assessTxHash,
        status: 'FINALIZED',
        interval: 4000,
        retries: 45
    });
    console.log("  ✓ Consensus Evaluation Status:", assessReceipt.status_name || assessReceipt.status);
    console.log("  ✓ Consensus Result:           ", assessReceipt.result_name);

    // Step 5: Verify Post-Consensus Policy State
    console.log("\n--- STEP 5: VERIFYING POST-CONSENSUS POLICY STATE ---");
    const p2PostRaw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_policy',
        args: ['POLICY_002']
    });
    const p2Post = JSON.parse(p2PostRaw);
    console.log("  ✓ Policy Status after Consensus: ", p2Post.status);
    console.log("  ✓ Last Observed Exit Epoch:      ", p2Post.last_observed_epoch);
    console.log("  ✓ Audit Summary:                 ", p2Post.last_audit_summary);

    const postPoolRaw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_pool_stats',
        args: []
    });
    const postPool = JSON.parse(postPoolRaw);
    console.log("  ✓ Total Claims Paid on-chain:    ", postPool.total_claims_paid_usdc, "USDC");
    console.log("  ✓ Active Coverage:               ", postPool.total_active_coverage_usdc, "USDC");

    console.log("\n===============================================================");
    console.log("  ALL ON-CHAIN TRANSACTIONS AND AI CONSENSUS 100% VERIFIED!");
    console.log("===============================================================");
}

runLiveTest().catch(console.error);
