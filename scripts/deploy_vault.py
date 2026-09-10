#!/usr/bin/env python3
"""
SlashingGuard EVM Vault Deployment Script
=========================================
Deploys SlashingGuardVault.sol to an EVM testnet (Base Sepolia / Sepolia)
and writes the deployment manifest to build/vault_deployment.json.
"""

import os
import sys
import json
import logging
from web3 import Web3
from eth_account import Account

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [DeployVault] %(message)s"
)

EVM_RPC_URL = os.getenv("EVM_RPC_URL", "https://sepolia.base.org")
PRIVATE_KEY = os.getenv("EVM_PRIVATE_KEY") or os.getenv("RELAY_PRIVATE_KEY", "")
AUTHORIZED_RELAY = os.getenv("AUTHORIZED_RELAY", "")

def main():
    logging.info(f"Connecting to EVM RPC: {EVM_RPC_URL}")
    w3 = Web3(Web3.HTTPProvider(EVM_RPC_URL))
    
    if not w3.is_connected():
        logging.error(f"Failed to connect to RPC endpoint: {EVM_RPC_URL}")
        sys.exit(1)
        
    chain_id = w3.eth.chain_id
    logging.info(f"Connected to Chain ID: {chain_id}")

    # Load compiled artifacts
    artifact_path = os.path.join(os.path.dirname(__file__), "..", "build", "SlashingGuardVault.json")
    if not os.path.exists(artifact_path):
        logging.error(f"Artifact not found at {artifact_path}. Run solc compilation first.")
        sys.exit(1)

    with open(artifact_path, "r", encoding="utf-8") as f:
        artifact = json.load(f)

    abi = artifact["abi"]
    bytecode = artifact["bytecode"]

    if not PRIVATE_KEY:
        # Generate or report address for user
        acct = Account.create()
        logging.warning("No EVM_PRIVATE_KEY supplied in environment.")
        logging.info(f"Generated new deployer account: {acct.address}")
        logging.info(f"Private Key: {acct.key.hex()}")
        logging.info("Fund this address with testnet ETH (faucet) and re-run with EVM_PRIVATE_KEY set.")
        
        # Save placeholder manifest for development
        manifest = {
            "chain_id": chain_id,
            "rpc_url": EVM_RPC_URL,
            "vault_address": "0x3Fa9b23f81902c34918239482910394817e12a89",
            "authorized_relay": acct.address,
            "owner": acct.address,
            "status": "PENDING_FUNDING",
            "account": acct.address,
            "private_key": acct.key.hex()
        }
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "build", "vault_deployment.json")
        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, indent=2)
        logging.info(f"Saved deployment config to {manifest_path}")
        return

    account = Account.from_key(PRIVATE_KEY)
    deployer = account.address
    balance = w3.eth.get_balance(deployer)
    logging.info(f"Deployer Address: {deployer} | Balance: {w3.from_wei(balance, 'ether')} ETH")

    relay_addr = AUTHORIZED_RELAY.strip() if AUTHORIZED_RELAY else deployer
    relay_addr = Web3.to_checksum_address(relay_addr)

    vault_factory = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    logging.info(f"Preparing deployment transaction with authorizedRelay: {relay_addr}...")
    nonce = w3.eth.get_transaction_count(deployer)
    gas_price = w3.eth.gas_price

    construct_txn = vault_factory.constructor(relay_addr).build_transaction({
        "from": deployer,
        "nonce": nonce,
        "gas": 3000000,
        "gasPrice": gas_price,
        "chainId": chain_id
    })

    signed_tx = w3.eth.account.sign_transaction(construct_txn, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    logging.info(f"Broadcasted deployment tx: {tx_hash.hex()}")

    logging.info("Waiting for transaction receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    vault_address = receipt.contractAddress
    logging.info(f"SlashingGuardVault deployed successfully at: {vault_address} (Block #{receipt.blockNumber})")

    # Save deployment details
    manifest = {
        "chain_id": chain_id,
        "rpc_url": EVM_RPC_URL,
        "vault_address": vault_address,
        "deployment_tx_hash": tx_hash.hex(),
        "deployment_block": receipt.blockNumber,
        "authorized_relay": relay_addr,
        "owner": deployer,
        "status": "DEPLOYED"
    }

    manifest_path = os.path.join(os.path.dirname(__file__), "..", "build", "vault_deployment.json")
    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2)
    logging.info(f"Wrote deployment manifest to {manifest_path}")

if __name__ == "__main__":
    main()
