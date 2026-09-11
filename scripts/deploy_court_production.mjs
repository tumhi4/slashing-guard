import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createClient, createAccount } from 'genlayer-js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const RPC_ENDPOINT = process.env.GENLAYER_RPC || 'https://studio.genlayer.com/api';
const RELAY_PRIVATE_KEY = process.env.RELAY_PRIVATE_KEY || '0x6de1107ac2d1750b9830314d75e6afdb5f3e2d0c055e1fe5ad16bf78bf24befd';

async function main() {
    console.log("===============================================================================");
    console.log("    DEPLOYING SLASHINGGUARD COURT WITH BOUND RELAY TO GENLAYER STUDIO");
    console.log("===============================================================================\n");

    const account = createAccount(RELAY_PRIVATE_KEY);
    console.log("[Deployer] Address:", account.address);

    const client = createClient({
        endpoint: RPC_ENDPOINT,
        account: account
    });

    const contractPath = path.join(__dirname, '..', 'contracts', 'SlashingGuardCourt.py');
    const code = fs.readFileSync(contractPath, 'utf8');
    console.log(`[Contract] Read ${contractPath} (${code.length} bytes)`);

    const operator = account.address;
    const relay = account.address; // Set authorized relay to deployer

    console.log(`[Constructor Args] Operator: ${operator}, Authorized Relay: ${relay}`);
    console.log("Broadcasting deployContract transaction to GenLayer Studio...");

    try {
        const txHash = await client.deployContract({
            code: code,
            args: [operator, relay]
        });
        console.log(`[Transaction] Broadcasted! Hash: ${txHash}`);
        console.log("Waiting for transaction receipt on GenLayer...");

        const receipt = await client.waitForTransactionReceipt({
            hash: txHash,
            status: 'FINALIZED',
            interval: 3000,
            retries: 45
        });

        const contractAddress = receipt.contractAddress || receipt.data?.contractAddress || receipt.recipient;
        console.log(`\n[SUCCESS] SlashingGuardCourt deployed at: ${contractAddress}`);
        console.log(`[Explorer] https://explorer-studio.genlayer.com/address/${contractAddress}`);

        const deploymentInfo = {
            contract_address: contractAddress,
            deployer: account.address,
            authorized_relay: relay,
            operator: operator,
            rpc_url: RPC_ENDPOINT,
            explorer_url: `https://explorer-studio.genlayer.com/address/${contractAddress}`,
            tx_hash: txHash,
            status: "DEPLOYED_ACTIVE",
            timestamp: new Date().toISOString()
        };

        const outPath = path.join(__dirname, '..', 'build', 'genlayer_deployment.json');
        fs.writeFileSync(outPath, JSON.stringify(deploymentInfo, null, 2), 'utf8');
        console.log(`[Manifest] Saved deployment details to ${outPath}`);

    } catch (err) {
        console.error("[Deploy Failed]", err);
        process.exit(1);
    }
}

main();
