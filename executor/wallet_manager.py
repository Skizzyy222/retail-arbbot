from eth_account import Account
import os
import json

WALLET_DIR = "wallets"

# Wallet generieren und speichern (json pro User)
def create_wallet(user_id):
    acct = Account.create()
    os.makedirs(WALLET_DIR, exist_ok=True)
    filepath = os.path.join(WALLET_DIR, f"{user_id}.json")
    with open(filepath, "w") as f:
        json.dump({"address": acct.address, "private_key": acct.key.hex()}, f)
    return acct.address

# Wallet laden (Adresse + privater Schlüssel)
def load_wallet(user_id):
    filepath = os.path.join(WALLET_DIR, f"{user_id}.json")
    if not os.path.exists(filepath):
        return None, None
    with open(filepath) as f:
        data = json.load(f)
    return data["address"], data["private_key"]

