from web3 import Web3
from wallet_manager import load_wallet
import os
from dotenv import load_dotenv
import json

load_dotenv()

NETWORK = os.getenv("NETWORK", "sepolia")
RPC_URL = os.getenv("RPC_URL_MAINNET") if NETWORK == "mainnet" else os.getenv("RPC_URL_SEPOLIA")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Approve ABI & Router ABI minimal
ERC20_ABI = json.loads('[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]')

# --- Hauptfunktion für simulierten Arbitrage-Trade ---
def execute_trade(user_id, token0, token1, dex_a, dex_b, leverage=1):
    address, private_key = load_wallet(user_id)
    if not address or not private_key:
        print(f"❌ Keine Wallet für User {user_id} gefunden.")
        return

    print(f"📤 Sende Trade für User {user_id} mit {leverage}x Hebel...")

    try:
        nonce = web3.eth.get_transaction_count(address)

        # Unterscheide ETH/WETH Transfer oder Token Swap
        is_eth_swap = token0.lower() == "0x4200000000000000000000000000000000000006"  # WETH-Adresse auf Sepolia

        if is_eth_swap:
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(dex_a),  # z. B. Router
                'value': Web3.to_wei(0.001 * leverage, 'ether'),
                'gas': 250_000,
                'gasPrice': web3.to_wei('5', 'gwei'),
                'chainId': web3.eth.chain_id
            }
        else:
            # Approve Token zuerst
            token = web3.eth.contract(address=Web3.to_checksum_address(token0), abi=ERC20_ABI)
            approve_tx = token.functions.approve(Web3.to_checksum_address(dex_a), Web3.to_wei(1000, 'ether')).build_transaction({
                'from': address,
                'nonce': nonce,
                'gas': 100_000,
                'gasPrice': web3.to_wei('5', 'gwei'),
                'chainId': web3.eth.chain_id
            })
            signed_approve = web3.eth.account.sign_transaction(approve_tx, private_key)
            approve_hash = web3.eth.send_raw_transaction(signed_approve.rawTransaction)
            print(f"✅ Approve gesendet: {web3.to_hex(approve_hash)}")

            nonce += 1

            # Dummy Trade als zweiter Schritt (normalerweise Router aufrufen)
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(dex_a),
                'value': 0,
                'gas': 250_000,
                'gasPrice': web3.to_wei('5', 'gwei'),
                'chainId': web3.eth.chain_id
            }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        print(f"✅ TX gesendet: {web3.to_hex(tx_hash)}")

    except Exception as e:
        print(f"❌ Fehler beim Senden der TX: {e}")

