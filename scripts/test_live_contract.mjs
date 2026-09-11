import { createClient, createAccount } from 'genlayer-js';

const CONTRACT_ADDRESS = '0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50';
const RPC_ENDPOINT = 'https://studio.genlayer.com/api';

async function testLiveContract() {
    console.log("===============================================================");
    console.log("  TESTING LIVE DEPLOYED SLASHINGGUARD CONTRACT ON GENLAYER");
    console.log("  Contract Address:", CONTRACT_ADDRESS);
    console.log("  RPC Endpoint:    ", RPC_ENDPOINT);
    console.log("===============================================================\n");

    const client = createClient({ endpoint: RPC_ENDPOINT });

    // Test 1: get_total_policies
    console.log("[Test 1] Calling get_total_policies()...");
    const total = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_total_policies',
        args: []
    });
    console.log("  ✓ Total Policies on-chain:", Number(total));

    // Test 2: get_authorized_relay
    console.log("\n[Test 2] Calling get_authorized_relay()...");
    const relay = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_authorized_relay',
        args: []
    });
    console.log("  ✓ Authorized Relay on-chain:", relay);

    // Test 3: get_pool_stats
    console.log("\n[Test 3] Calling get_pool_stats()...");
    const poolStatsRaw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_pool_stats',
        args: []
    });
    console.log("  ✓ Pool Stats Raw JSON:", poolStatsRaw);
    const poolStats = JSON.parse(poolStatsRaw);
    console.log("  ✓ Underwriting Pool Capital: ", poolStats.pool_capital_usdc, "USDC");
    console.log("  ✓ Total Active Coverage:     ", poolStats.total_active_coverage_usdc, "USDC");
    console.log("  ✓ Available Solvency Capital:", poolStats.available_capital_usdc, "USDC");

    // Test 4: get_policy("POLICY_001")
    console.log("\n[Test 4] Calling get_policy('POLICY_001')...");
    const policyRaw = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: 'get_policy',
        args: ['POLICY_001']
    });
    console.log("  ✓ Policy_001 Raw JSON:", policyRaw);
    const policy = JSON.parse(policyRaw);
    console.log("  ✓ Policy ID:        ", policy.policy_id);
    console.log("  ✓ Insured Validator:", policy.validator_index);
    console.log("  ✓ Coverage Amount:  ", policy.coverage_amount_usdc, "USDC");
    console.log("  ✓ Policy Status:    ", policy.status);
    console.log("  ✓ Max Exit Epoch:   ", policy.max_exit_epoch);

    console.log("\n===============================================================");
    console.log("  ALL ON-CHAIN READ TESTS FOR NEW CONTRACT 100% SUCCESSFUL!");
    console.log("===============================================================");
}

testLiveContract().catch(console.error);
