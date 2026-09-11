"""
SlashingGuard Autonomous Dual-Chain Settlement Relay (Python Engine)
====================================================================
Monitors GenLayer SlashingGuardCourt Intelligent Contract for CLAIM_APPROVED
events, authorizes parametric payout on EVM SlashingGuardVault, and reports
cryptographic settlement receipts back to GenLayer.
"""

import os
import sys
import time
import json
import logging
import subprocess
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SlashingGuardRelay] %(message)s",
    handlers=[
        logging.FileHandler("slashingguard_relay.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configuration
GENLAYER_RPC = os.getenv("GENLAYER_RPC", "https://studio.genlayer.com/api")
GENLAYER_COURT_ADDRESS = os.getenv("GENLAYER_COURT_ADDRESS", "0x1aa80e21FDEc3B9Ff1440B49edD046Ffc12Ecb50")
EVM_RPC_URL = os.getenv("EVM_RPC_URL", "https://sepolia.base.org")
EVM_VAULT_ADDRESS = os.getenv("EVM_VAULT_ADDRESS", "0x3Fa9b23f81902c34918239482910394817e12a89")
RELAY_PRIVATE_KEY = os.getenv("RELAY_PRIVATE_KEY", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))

class SlashingGuardDualChainRelay:
    def __init__(self):
        self.w3_evm = Web3(Web3.HTTPProvider(EVM_RPC_URL))
        logging.info(f"Connected to Base Sepolia: {self.w3_evm.is_connected()}")
        
        # Load Vault ABI
        build_dir = os.path.join(os.path.dirname(__file__), "..", "build")
        vault_json_path = os.path.join(build_dir, "SlashingGuardVault.json")
        self.vault_abi = []
        if os.path.exists(vault_json_path):
            with open(vault_json_path, "r", encoding="utf-8") as f:
                artifact = json.load(f)
                self.vault_abi = artifact.get("abi", [])

        clean_pk = RELAY_PRIVATE_KEY if RELAY_PRIVATE_KEY.startswith("0x") else f"0x{RELAY_PRIVATE_KEY}"
        self.relay_account = Account.from_key(clean_pk)
        logging.info(f"Relay Account: {self.relay_account.address}")

    def query_genlayer_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        # Invoke genlayer-js query bridge via node
        script = f'''
        import('../frontend/node_modules/genlayer-js/dist/index.js').then(async m => {{
            const c = m.createClient({{ endpoint: '{GENLAYER_RPC}' }});
            const p = await c.readContract({{
                address: '{GENLAYER_COURT_ADDRESS}',
                functionName: 'get_policy',
                args: ['{policy_id}']
            }});
            console.log(p);
        }}).catch(e => console.error(e));
        '''
        try:
            res = subprocess.run(
                ["node", "--input-type=module", "-e", script],
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), ".."),
                timeout=20
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout.strip())
        except Exception as e:
            logging.error(f"Error querying policy {policy_id}: {e}")
        return None

    def execute_evm_disbursement(self, policy_id: str, staker: str, amount_usdc: int) -> Dict[str, Any]:
        logging.info(f"Authorizing EVM payout on Base Sepolia: {amount_usdc} USDC -> {staker}")
        balance = self.w3_evm.eth.get_balance(self.relay_account.address)
        logging.info(f"Relay balance: {self.w3_evm.from_wei(balance, 'ether')} ETH")
        
        if balance > 0:
            contract = self.w3_evm.eth.contract(address=Web3.to_checksum_address(EVM_VAULT_ADDRESS), abi=self.vault_abi)
            nonce = self.w3_evm.eth.get_transaction_count(self.relay_account.address)
            policy_bytes32 = Web3.keccak(text=policy_id)
            tx = contract.functions.executeSlashingPayout(
                policy_bytes32,
                Web3.to_checksum_address(staker),
                amount_usdc
            ).build_transaction({
                "from": self.relay_account.address,
                "nonce": nonce,
                "gas": 150000,
                "gasPrice": self.w3_evm.eth.gas_price,
                "chainId": 84532
            })
            signed = self.w3_evm.eth.account.sign_transaction(tx, private_key=RELAY_PRIVATE_KEY)
            tx_hash = self.w3_evm.eth.send_raw_transaction(signed.rawTransaction)
            logging.info(f"EVM Tx sent: {tx_hash.hex()}")
            receipt = self.w3_evm.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            if receipt.status != 1:
                raise RuntimeError(f"EVM payout reverted on Base Sepolia: {tx_hash.hex()}")
            return {"status": receipt.status, "transactionHash": tx_hash.hex(), "blockNumber": receipt.blockNumber}
        else:
            raise RuntimeError(f"Relay account {self.relay_account.address} has 0 ETH on Base Sepolia. Payout aborted (Zero Fabrication Policy).")

    def process_approved_policies(self):
        logging.info(f"Scanning GenLayer Court: {GENLAYER_COURT_ADDRESS}...")
        for i in range(1, 10):
            p_id = f"POLICY_{i:03d}"
            policy = self.query_genlayer_policy(p_id)
            if not policy:
                break
            if policy.get("status") == "CLAIM_APPROVED" and not policy.get("claim_payout_tx_hash"):
                logging.info(f"Approved claim found for {p_id}! Executing dual-chain settlement...")
                receipt = self.execute_evm_disbursement(
                    policy_id=p_id,
                    staker=policy["staker_address"],
                    amount_usdc=policy["coverage_amount_usdc"]
                )
                logging.info(f"EVM Settlement Receipt: {receipt['transactionHash']} (Block #{receipt['blockNumber']})")

    def run(self):
        logging.info("SlashingGuard Settlement Relay Daemon started.")
        self.process_approved_policies()

if __name__ == "__main__":
    relay = SlashingGuardDualChainRelay()
    relay.run()
