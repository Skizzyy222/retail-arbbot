import asyncio
import os
import sys
import logging
from dotenv import load_dotenv
from web3 import Web3
import yaml

# Telegram shared_state laden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'telegrambot')))
from shared_state import user_state


# --- ENV & CONFIG ---
load_dotenv()
NETWORK = os.getenv("NETWORK", "sepolia")
RPC_URL = os.getenv("RPC_URL_MAINNET") if NETWORK == "mainnet" else os.getenv("RPC_URL_SEPOLIA")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

with open("config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# --- Dummy Router Interface (Uniswap/SushiV2 getAmountsOut) ---
ROUTER_ABI = [
    {
        "name": "getAmountsOut",
        "type": "function",
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view"
    }
]

# --- Preis abrufen ---
async def get_price(router_address, token0, token1):
    try:
        router = web3.eth.contract(address=Web3.to_checksum_address(router_address), abi=ROUTER_ABI)
        amount_in = Web3.to_wei(1, 'ether')  # 1 Token0
        amounts = router.functions.getAmountsOut(amount_in, [token0, token1]).call()
        return Web3.from_wei(amounts[1], 'ether')
    except Exception as e:
        logging.debug(f"Preisfehler: {e}")
        return None

# --- Spread berechnen ---
def calculate_spread(a, b):
    if not a or not b or a == 0:
        return 0
    return abs(a - b) / min(a, b) * 100

# --- Scanner Loop ---
async def scan_loop():
    print("🚀 Async High-Speed Scanner gestartet...")
    while True:
        tasks = []

        for user_id, state in user_state.items():
            dex_names = list(state.get("dexes", []))
            pair_ids = list(state.get("pairs", []))
            spread_limit = float(state.get("spread", 1.0))
            autotrade = state.get("autotrade", False)

            if len(dex_names) < 2 or not pair_ids:
                continue

            for pair_id in pair_ids:
                pair = CONFIG['pairs'][pair_id]
                token0 = Web3.to_checksum_address(pair['token0'])
                token1 = Web3.to_checksum_address(pair['token1'])
                name = pair.get("name", f"{token0[:6]}/{token1[:6]}")

                best_spread = 0
                best_combo = None

                combinations = [
                    (a, b) for i, a in enumerate(dex_names)
                    for j, b in enumerate(dex_names) if i < j
                ]

                price_tasks = {
                    (a, b): (
                        asyncio.to_thread(get_price, get_router(a), token0, token1),
                        asyncio.to_thread(get_price, get_router(b), token0, token1)
                    )
                    for a, b in combinations
                }

                resolved = await asyncio.gather(*[
                    asyncio.gather(a_task, b_task)
                    for a_task, b_task in price_tasks.values()
                ])

                for ((dex_a, dex_b), (price_a, price_b)) in zip(price_tasks.keys(), resolved):
                    spread = calculate_spread(price_a, price_b)
                    if spread >= spread_limit and spread > best_spread:
                        best_spread = spread
                        best_combo = (dex_a, dex_b)

                if best_combo:
                    dex_a, dex_b = best_combo
                    logging.info(f"[User {user_id}] Best Spread {best_spread:.2f}% bei {name} zwischen {dex_a} und {dex_b}")
                    if autotrade:
                        trigger_trade(user_id, token0, token1, dex_a, dex_b)

        await asyncio.sleep(1)

# --- Router-Adresse holen ---
def get_router(name):
    for dex in CONFIG['dexes']:
        if dex['name'] == name:
            return dex['factory']  # Ggf. Router statt Factory eintragen
    return None

# --- Trade auslösen ---
def trigger_trade(user_id, token0, token1, dex_a, dex_b):
    print(f"🔥 Trade ausgelöst für User {user_id}: {token0[:6]}/{token1[:6]} von {dex_a} → {dex_b}")
    # executor.execute(user_id, ...)

# --- Main ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scan_loop())

