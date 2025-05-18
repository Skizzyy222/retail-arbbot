import os, json
from eth_account import Account

WALLET_DIR = "./wallets"

def generate_wallet(user_id):
    acct = Account.create()
    data = {
        "address": acct.address,
        "private_key": acct.key.hex()
    }
    os.makedirs(WALLET_DIR, exist_ok=True)
    with open(f"{WALLET_DIR}/{user_id}.json", "w") as f:
        json.dump(data, f)
    return data["address"], data["private_key"]

def load_wallet(user_id):
    try:
        with open(f"{WALLET_DIR}/{user_id}.json") as f:
            data = json.load(f)
        return data["address"], data["private_key"]
    except FileNotFoundError:
        return generate_wallet(user_id)
