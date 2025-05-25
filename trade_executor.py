import os
import json
from datetime import datetime
from web3 import Web3
from dotenv import load_dotenv
from wallets.wallet_manager import get_or_create_wallet

# --- ENV & Web3 Init ---
load_dotenv()
NETWORK = os.getenv("NETWORK", "sepolia")
RPC_URL = os.getenv("RPC_URL_MAINNET") if NETWORK == "mainnet" else os.getenv("RPC_URL_SEPOLIA")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

DEV_WALLET = os.getenv("DEV_WALLET")
DEV_WALLET = Web3.to_checksum_address(DEV_WALLET) if DEV_WALLET else None

# --- Approve ABI (ERC20 minimal) ---
ERC20_ABI = json.loads(
    '[{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]'
)

# --- Logger: Schreibe in pro-User-Log ---
def log_trade(user_id, trade_data):
    log_file = os.path.join("trades", f"tradelog_{user_id}.json")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                logs = json.load(f)
            except Exception:
                logs = []
    else:
        logs = []
    logs.append(trade_data)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=2)

# --- Dummy-Funktion für Telegram Feedback ---
def telegram_notify(user_id, message):
    print(f"[TELEGRAM -> {user_id}] {message}")

# --- ETH an DevWallet senden ---
def send_dev_cut(from_address, private_key, profit_eth, user_id, notify, nonce):
    if not DEV_WALLET:
        notify(user_id, "⚠️ DEV_WALLET nicht gesetzt. Dev-Cut wird übersprungen!")
        return None

    cut_amount = profit_eth * 0.35
    if cut_amount <= 0:
        notify(user_id, "Kein Profit erzielt, kein Dev-Cut nötig.")
        return None

    try:
        tx = {
            'nonce': nonce,
            'to': DEV_WALLET,
            'value': Web3.to_wei(cut_amount, "ether"),
            'gas': 21_000,
            'gasPrice': web3.to_wei('5', 'gwei'),
            'chainId': web3.eth.chain_id
        }
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        notify(user_id, f"💸 35% Profit-Cut ({cut_amount:.6f} ETH) an Dev gesendet!\nTX: <code>{web3.to_hex(tx_hash)}</code>")
        return web3.to_hex(tx_hash)
    except Exception as e:
        notify(user_id, f"❌ Fehler beim Senden des Dev-Cuts: {e}")
        return None

# --- Hauptfunktion für einen Arbitrage-Trade ---
def execute_trade(user_id, token0, token1, dex_a, dex_b, leverage=1, telegram_callback=None):
    address, private_key = get_or_create_wallet(user_id)
    notify = telegram_callback or telegram_notify

    if not address or not private_key:
        notify(user_id, "❌ Keine Wallet gefunden. Bitte mit /start beginnen.")
        return

    try:
        nonce = web3.eth.get_transaction_count(address)
        is_eth_swap = token0.lower() == "0x4200000000000000000000000000000000000006"  # Sepolia WETH

        gas_price = web3.to_wei('5', 'gwei')
        trade_amount = 0.001 * leverage  # Minimaler Test-Betrag!

        tx_hashes = []
        gas_used = None
        profit = None
        devcut_tx = None

        # Pre-Balance
        balance_before = web3.eth.get_balance(address)

        # --- Schritt 1: Approve, falls nötig ---
        if not is_eth_swap:
            try:
                token = web3.eth.contract(address=Web3.to_checksum_address(token0), abi=ERC20_ABI)
                approve_tx = token.functions.approve(
                    Web3.to_checksum_address(dex_a),
                    Web3.to_wei(1000, 'ether')
                ).build_transaction({
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
                # Warte optional auf Approve Bestätigung (kann weg für speed)
                web3.eth.wait_for_transaction_receipt(approve_hash)
                nonce += 1
            except Exception as e:
                notify(user_id, f"❌ Approve fehlgeschlagen: {e}")
                raise

        # --- Schritt 2: Haupt-Trade (simulate swap) ---
        try:
            tx = {
                'nonce': nonce,
                'to': Web3.to_checksum_address(dex_a),
                'value': Web3.to_wei(trade_amount, 'ether') if is_eth_swap else 0,
                'gas': 250_000,
                'gasPrice': gas_price,
                'chainId': web3.eth.chain_id
            }
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hashes.append(web3.to_hex(tx_hash))
            print(f"✅ Swap TX gesendet: {web3.to_hex(tx_hash)}")
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            gas_used = receipt.gasUsed
            nonce += 1
        except Exception as e:
            notify(user_id, f"❌ Swap fehlgeschlagen: {e}")
            raise

        # --- Schritt 3: Profit berechnen (grob, auf Sepolia oft 0) ---
        balance_after = web3.eth.get_balance(address)
        profit = float(web3.from_wei(balance_after - balance_before, "ether"))

        # --- Schritt 4: DEV CUT (35%) ---
        if profit > 0.000001:
            devcut_tx = send_dev_cut(address, private_key, profit, user_id, notify, nonce)
            if devcut_tx:
                tx_hashes.append(devcut_tx)
        else:
            notify(user_id, "Kein Profit, daher kein Dev-Cut.")

        # --- Logging ---
        trade_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pair": f"{token0}/{token1}",
            "dex_a": dex_a,
            "dex_b": dex_b,
            "leverage": leverage,
            "amount_in": trade_amount,
            "profit": profit,
            "dev_cut": profit * 0.35 if profit and profit > 0 else 0,
            "gas_used": gas_used,
            "gas_price_gwei": 5,
            "tx_hashes": tx_hashes,
            "status": "SUCCESS"
        }
        log_trade(user_id, trade_data)
        notify(user_id, (
            f"🚀 Trade erfolgreich!\n"
            f"Profit: <b>{profit:.6f}</b> ETH\n"
            f"Dev-Cut (35%): <b>{trade_data['dev_cut']:.6f}</b> ETH\n"
            f"Gas Used: <b>{gas_used}</b>\n"
            f"TX: <code>{tx_hashes[-1]}</code>"
        ))

        return trade_data

    except Exception as e:
        error_msg = f"❌ Fehler beim Trade: {e}"
        notify(user_id, error_msg)
        trade_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pair": f"{token0}/{token1}",
            "dex_a": dex_a,
            "dex_b": dex_b,
            "leverage": leverage,
            "amount_in": trade_amount if 'trade_amount' in locals() else None,
            "profit": None,
            "dev_cut": None,
            "gas_used": None,
            "gas_price_gwei": 5,
            "tx_hashes": tx_hashes if 'tx_hashes' in locals() else [],
            "status": "FAILED",
            "error": str(e)
        }
        log_trade(user_id, trade_data)
        return None



