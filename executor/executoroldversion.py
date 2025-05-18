import os
import asyncio
import yaml
import logging
from pathlib import Path
from web3 import Web3
from web3.middleware import geth_poa_middleware
from flashbots import Flashbots
from eth_account import Account
from typing import Tuple, Any

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration loader ---
def load_config() -> dict:
    """
    Lädt die Konfiguration aus einer YAML-Datei.
    Die Datei enthält RPC-Endpoints für mehrere Netzwerke und Relay-URLs.
    """
    cfg_path = Path(__file__).parent.parent / "scanner" / "config.yaml"
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)

# --- Web3 Setup mit optionaler PoA-Middleware für Testnets ---
def init_web3(rpc_url: str) -> Web3:
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.isConnected():
        logger.error(f"Failed to connect to RPC: {rpc_url}")
        raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")
    # Inject PoA-Middleware für Testnetzwerke
    if w3.eth.chain_id in (5, 11155111):
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

# --- Flashbots Setup ---
def init_flashbots(w3: Web3, relay_url: str, signer: Account) -> Flashbots:
    return Flashbots(w3, signer, flashbot_url=relay_url)

# --- Executor-Funktion: führt einmal Simulation + Bundle send durch ---
async def run_once() -> Tuple[Any, Any]:
    cfg = load_config()
    network = os.getenv("NETWORK", cfg.get("networks", {}).get("default", "sepolia"))
    if network not in cfg["rpc_endpoints"] or network not in cfg["executor"]["relay_urls"]:
        raise ValueError(f"Unknown network '{network}' in config.yaml")

    rpc_url = cfg["rpc_endpoints"][network]
    relay_url = cfg["executor"]["relay_urls"][network]
    priv_env = cfg["executor"]["private_key_env_var"]
    priv_key = os.getenv(priv_env)
    if not priv_key:
        raise RuntimeError("Private key not found in environment variable")

    w3 = init_web3(rpc_url)
    account = Account.from_key(priv_key)
    fb = init_flashbots(w3, relay_url, account)
    logger.info(f"Flashbots ready for {account.address} on chain {w3.eth.chain_id} ({network})")

    # Transaktion aufbauen
    tx = {
        "to": cfg["executor"]["target_address"],
        "data": cfg["executor"]["calldata"],
        "value": int(cfg["executor"].get("value", 0)),
        "chainId": w3.eth.chain_id,
        "nonce": w3.eth.get_transaction_count(account.address),
    }

    # Gas schätzen und Fees setzen
    gas_est = w3.eth.estimate_gas({**tx, "from": account.address})
    block = w3.eth.get_block("latest")
    base_fee = block.get("baseFeePerGas", 0)
    max_priority = int(cfg["executor"].get("max_priority_fee", 0))
    tx.update({
        "gas": gas_est,
        "maxFeePerGas": base_fee + max_priority,
        "maxPriorityFeePerGas": max_priority,
    })

    # Signieren
    signed_tx = account.sign_transaction(tx)
    bundle = [{"signed_transaction": signed_tx.rawTransaction}]

    # Simulation + Senden mit Error-Handling
    try:
        sim = fb.simulate(bundle)
        logger.info(f"Simulation result: {sim}")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise

    try:
        send_result = fb.send_bundle(bundle, target_block_number=block.number + 1)
        receipt = await send_result.wait()
        logger.info(f"Bundle included: {receipt}")
    except Exception as e:
        logger.error(f"Bundle send failed: {e}")
        raise

    return sim, receipt

# --- Direkt ausführbares Skript für lokale Tests ---
if __name__ == "__main__":
    try:
        sim, receipt = asyncio.run(run_once())
        print("Simulation:", sim)
        print("Receipt:", receipt)
    except Exception as e:
        logger.error(f"Executor encountered an error: {e}")
