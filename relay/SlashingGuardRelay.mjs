import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createClient, createAccount } from 'genlayer-js';
import { createPublicClient, createWalletClient, http, parseEther, formatEther, keccak256, toHex } from 'viem';
import { baseSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const GENLAYER_RPC = process.env.GENLAYER_RPC || 'https://studio.genlayer.com/api';
const GENLAYER_COURT = process.env.GENLAYER_COURT_ADDRESS || '0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50';
const EVM_RPC_URL = process.env.EVM_RPC_URL || 'https://sepolia.base.org';
const EVM_VAULT_ADDRESS = process.env.EVM_VAULT_ADDRESS || '0x3Fa9b23f81902c34918239482910394817e12a89';
const RELAY_PRIVATE_KEY = process.env.RELAY_PRIVATE_KEY || '';
const POLL_INTERVAL_MS = parseInt(process.env.POLL_INTERVAL_MS || '15000', 10);

// Load EVM Vault ABI
const vaultArtifactPath = path.join(__dirname, '..', 'build', 'SlashingGuardVault.json');
let vaultAbi = [];
if (fs.existsSync(vaultArtifactPath)) {
    const raw = JSON.parse(fs.readFileSync(vaultArtifactPath, 'utf8'));
    vaultAbi = raw.abi || [];
}

console.log("===============================================================================");
console.log("      SLASHINGGUARD AUTONOMOUS DUAL-CHAIN SETTLEMENT RELAY DAEMON");
console.log("  GenLayer Court   :", GENLAYER_COURT);
console.log("  GenLayer RPC     :", GENLAYER_RPC);
console.log("  EVM Vault Address:", EVM_VAULT_ADDRESS);
console.log("  EVM Network      : Base Sepolia (84532)");
console.log("===============================================================================\n");

// Initialize GenLayer Client
const formattedKey = RELAY_PRIVATE_KEY ? (RELAY_PRIVATE_KEY.startsWith('0x') ? RELAY_PRIVATE_KEY : `0x${RELAY_PRIVATE_KEY}`) : null;
const relayAccount = formattedKey ? createAccount(formattedKey) : createAccount();
const genlayerClient = createClient({ endpoint: GENLAYER_RPC, account: relayAccount });

// Initialize Viem Clients
const viemAccount = formattedKey ? privateKeyToAccount(formattedKey) : privateKeyToAccount('0x0000000000000000000000000000000000000000000000000000000000000001');
const evmPublicClient = createPublicClient({
    chain: baseSepolia,
    transport: http(EVM_RPC_URL)
});
const evmWalletClient = createWalletClient({
    account: viemAccount,
    chain: baseSepolia,
    transport: http(EVM_RPC_URL)
});

console.log(`[Relay Engine] Initialized relay account: ${relayAccount.address}`);

async function processApprovedClaims() {
    try {
        const totalRaw = await genlayerClient.readContract({
            address: GENLAYER_COURT,
            functionName: 'get_total_policies',
            args: []
        });
        const totalPolicies = Number(totalRaw);
        console.log(`[Relay Scan] Active policies count: ${totalPolicies}. Scanning for approved claims...`);

        for (let i = 1; i <= totalPolicies; i++) {
            const policyId = `POLICY_${String(i).padStart(3, '0')}`;
            let policyRaw;
            try {
                policyRaw = await genlayerClient.readContract({
                    address: GENLAYER_COURT,
                    functionName: 'get_policy',
                    args: [policyId]
                });
            } catch (err) {
                continue;
            }

            const policy = JSON.parse(policyRaw);
            if (policy.status === 'CLAIM_APPROVED' && !policy.claim_payout_tx_hash) {
                console.log(`\n[CLAIM DETECTED] Policy ${policyId} is CLAIM_APPROVED!`);
                console.log(`  Insured Staker : ${policy.staker_address}`);
                console.log(`  Validator Index: ${policy.validator_index}`);
                console.log(`  Coverage Amount: ${policy.coverage_amount_usdc} USDC`);
                console.log(`  Reason         : ${policy.last_audit_summary}`);

                // Execute EVM Slashing Reimbursement
                let evmTxHash = '';
                let blockNumber = 0;

                try {
                    const balance = await evmPublicClient.getBalance({ address: viemAccount.address });
                    console.log(`  Relay Base Sepolia Balance: ${formatEther(balance)} ETH`);

                    if (balance > parseEther('0.0005')) {
                        console.log(`  Broadcasting executeSlashingPayout to EVM Vault on Base Sepolia...`);
                        const policyIdBytes32 = keccak256(toHex(policyId));
                        const hash = await evmWalletClient.writeContract({
                            address: EVM_VAULT_ADDRESS,
                            abi: vaultAbi,
                            functionName: 'executeSlashingPayout',
                            args: [policyIdBytes32, policy.staker_address, BigInt(policy.coverage_amount_usdc)]
                        });
                        console.log(`  Broadcasted EVM Tx Hash: ${hash}`);
                        const receipt = await evmPublicClient.waitForTransactionReceipt({ hash });
                        if (receipt.status !== 'success') {
                            throw new Error(`EVM payout transaction reverted on-chain (status: ${receipt.status})`);
                        }
                        evmTxHash = receipt.transactionHash;
                        blockNumber = Number(receipt.blockNumber);
                        console.log(`  ✓ Authenticated EVM Payout Confirmed in Block #${blockNumber}! Tx: ${evmTxHash}`);
                    } else {
                        console.error(`  [ABORT] Relay account has insufficient gas for live Base Sepolia broadcast.`);
                        console.error(`  No settlement will be submitted until valid on-chain payment occurs (Zero Fabrication Policy).`);
                        continue;
                    }
                } catch (evmErr) {
                    console.error(`  [ERROR] EVM Vault payout failed: ${evmErr.message || evmErr}`);
                    console.error(`  Settlement aborted to prevent unauthenticated settlement submission.`);
                    continue;
                }

                if (!evmTxHash || !blockNumber) {
                    console.warn(`  Skipping settlement for ${policyId}: No verified EVM transaction receipt.`);
                    continue;
                }

                // Finalize on GenLayer Court
                console.log(`  Submitting confirm_settlement to GenLayer Court Intelligent Contract...`);
                try {
                    const confirmHash = await genlayerClient.writeContract({
                        address: GENLAYER_COURT,
                        functionName: 'confirm_settlement',
                        args: [policyId, evmTxHash, blockNumber, policy.coverage_amount_usdc]
                    });
                    console.log(`  GenLayer Confirmation Tx: ${confirmHash}`);
                    const confirmReceipt = await genlayerClient.waitForTransactionReceipt({
                        hash: confirmHash,
                        status: 'FINALIZED',
                        interval: 3000,
                        retries: 30
                    });
                    console.log(`  ✓ Settlement Finalized on GenLayer! Status: ${confirmReceipt.status_name || confirmReceipt.status}`);
                } catch (courtErr) {
                    console.warn(`  Settlement confirmation invariant note: ${courtErr.message || courtErr}`);
                }
            }
        }
    } catch (err) {
        console.error(`[Relay Loop Error] ${err.message || err}`);
    }
}

async function runDaemon() {
    console.log(`\n[Relay Daemon] Started. Polling every ${POLL_INTERVAL_MS / 1000} seconds...`);
    await processApprovedClaims();
    setInterval(processApprovedClaims, POLL_INTERVAL_MS);
}

// Single-run mode if --once flag passed
if (process.argv.includes('--once')) {
    processApprovedClaims().then(() => {
        console.log("[Relay Engine] Single execution cycle completed.");
        process.exit(0);
    });
} else {
    runDaemon();
}
