
from web3 import Web3
from flashbots import Flashbots
import yaml
import asyncio

def load_config():
    return yaml.safe_load(open("../scanner/config.yaml"))

def init_web3(cfg):
    return Web3(Web3.HTTPProvider(cfg["rpc_endpoints"]["ethereum"]))

def init_flashbots(w3, private_key_hex):
    acct = w3.eth.account.from_key(private_key_hex)
    return Flashbots(w3, acct)

async def execute_trade():
    cfg = load_config()
    w3 = init_web3(cfg)
    fb = init_flashbots(w3, cfg["executor"]["private_key"])
    # Beispiel: nur ein Druck, später Bundle senden
    print("Flashbots initialized for account", fb.account.address)

if __name__ == "__main__":
    asyncio.run(execute_trade())

