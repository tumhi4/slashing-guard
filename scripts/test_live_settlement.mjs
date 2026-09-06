import { createClient, createAccount } from '../../AetherDungeon/frontend/node_modules/genlayer-js/dist/index.js';

const CONTRACT_ADDRESS = '0x0B51fbab587280f844BD3C926B28da13ea1b7251';
const RPC_ENDPOINT = 'https://studio.genlayer.com/api';

async function testSettlementGuard() {
    console.log("Testing Restricted Settlement Confirmation Invariants on-chain...");
    const unauthorizedCaller = createAccount();
    console.log("Unauthorized Caller:", unauthorizedCaller.address);

    const client = createClient({ endpoint: RPC_ENDPOINT, account: unauthorizedCaller });

    console.log("Attempting unauthorized confirm_settlement call...");
    try {
        const txHash = await client.writeContract({
            address: CONTRACT_ADDRESS,
            functionName: 'confirm_settlement',
            args: [
                'POLICY_002',
                '0x7f8a9b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a',
                6891234,
                1000
            ]
        });
        console.log("Tx Hash:", txHash);
        const receipt = await client.waitForTransactionReceipt({
            hash: txHash,
            status: 'FINALIZED',
            interval: 3000,
            retries: 30
        });
        console.log("Receipt result:", receipt.result_name, receipt.status_name);
        console.log("Receipt execution result:", receipt.execution_result);
    } catch (err) {
        console.log("✓ Expected revert captured:", err.message || err);
    }
}

testSettlementGuard().catch(console.error);
