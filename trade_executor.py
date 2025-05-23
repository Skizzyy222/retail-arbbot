import os
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv
from wallets.wallet_manager import load_wallet, get_or_create_wallet

# --- ENV & Web3 Init ---
load_dotenv()
NETWORK = os.getenv("NETWORK", "sepolia")
RPC_URL = os.getenv("RPC_URL_MAINNET") if NETWORK == "mainnet" else os.getenv("RPC_URL_SEPOLIA")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# --- Approve ABI (ERC20 minimal) ---
ERC20_ABI = json.loads(
    '[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]'
)

# --- Logger: Schreibe in pro-User-Log ---
def log_trade(user_id, trade_data):
    log_file = os.path.join("trades", f"tradelog_{user_id}.json")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(trade_data)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

# --- Dummy-Funktion für Telegram Feedback ---
def telegram_notify(user_id, message):
    # TODO: Im Bot-Modul implementieren – hier nur Platzhalter!
    print(f"[TELEGRAM -> {user_id}] {message}")

# --- Hauptfunktion für einen Arbitrage-Trade ---
def execute_trade(user_id, token0, token1, dex_a, dex_b, leverage=1, telegram_callback=None):
    address, private_key = get_or_create_wallet(user_id)
    if not address or not private_key:
        notify = telegram_callback or telegram_notify
        notify(user_id, "❌ Keine Wallet gefunden. Bitte mit /start beginnen.")
        return

    try:
        nonce = web3.eth.get_transaction_count(address)
        is_eth_swap = token0.lower() == "0x4200000000000000000000000000000000000006"  # Sepolia WETH

        gas_price = web3.to_wei('5', 'gwei')
        trade_amount = 0.001 * leverage  # Beispielwert für Test

        tx_hashes = []
        profit = None

        # Pre-Balance
        balance_before = web3.eth.get_balance(address)

        notify = telegram_callback or telegram_notify

        if is_eth_swap:
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(dex_a),
                'value': Web3.to_wei(trade_amount, 'ether'),
                'gas': 250_000,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            }
        else:
            # Approve-Transaktion
            token = web3.eth.contract(address=Web3.to_checksum_address(token0), abi=ERC20_ABI)
            approve_tx = token.functions.approve(Web3.to_checksum_address(dex_a), Web3.to_wei(1000, 'ether')).build_transaction({
                'from': address,
                'nonce': nonce,
                'gas': 100_000,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            })
            signed_approve = web3.eth.account.sign_transaction(approve_tx, private_key)
            approve_hash = web3.eth.send_raw_transaction(signed_approve.rawTransaction)
            tx_hashes.append(web3.to_hex(approve_hash))
            print(f"✅ Approve TX gesendet: {web3.to_hex(approve_hash)}")
            notify(user_id, f"✅ Approve gesendet!\nTX: <code>{web3.to_hex(approve_hash)}</code>")

            nonce += 1
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(dex_a),
                'value': 0,
                'gas': 250_000,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            }

        # Haupt-Trade (swap, etc.)
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        tx_hashes.append(web3.to_hex(tx_hash))
        print(f"✅ TX gesendet: {web3.to_hex(tx_hash)}")

        # --- Auf Bestätigung warten (optional, sonst async!) ---
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        gas_used = receipt.gasUsed

        # Post-Balance (grob, für Demo)
        balance_after = web3.eth.get_balance(address)
        profit = web3.from_wei(balance_after - balance_before, "ether")

        # --- Logging ---
        trade_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pair": f"{token0}/{token1}",
            "dex_a": dex_a,
            "dex_b": dex_b,
            "leverage": leverage,
            "amount_in": trade_amount,
            "profit": float(profit),
            "gas_used": gas_used,
            "gas_price_gwei": 5,
            "tx_hashes": tx_hashes,
            "status": "SUCCESS"
        }
        log_trade(user_id, trade_data)
        notify(user_id, f"🚀 Trade erfolgreich!\nProfit: <b>{profit:.6f}</b> ETH\nGas Used: <b>{gas_used}</b>\nTX: <code>{web3.to_hex(tx_hash)}</code>")

        return trade_data

    except Exception as e:
        notify = telegram_callback or telegram_notify
        notify(user_id, f"❌ Fehler beim Trade: {e}")
        trade_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pair": f"{token0}/{token1}",
            "dex_a": dex_a,
            "dex_b": dex_b,
            "leverage": leverage,
            "amount_in": 0.001 * leverage,
            "profit": None,
            "gas_used": None,
            "gas_price_gwei": 5,
            "tx_hashes": [],
            "status": "FAILED",
            "error": str(e)
        }
        log_trade(user_id, trade_data)
        return None


