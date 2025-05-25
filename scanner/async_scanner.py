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

# --- Preis abrufen (async, aber via Thread wegen web3 call) ---
def get_price(router_address, token0, token1):
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

# --- Router-Adresse holen (KORRIGIERT: router, nicht factory) ---
def get_router(name):
    for dex in CONFIG['dexes']:
        if dex['name'] == name:
            return dex['router']
    return None

# --- Trade auslösen inkl. Telegram-Callback (Bot Notification) ---
def trigger_trade(user_id, token0, token1, dex_a, dex_b, spread, bot_notify=None):
    print(f"🔥 Trade ausgelöst für User {user_id}: {token0[:6]}/{token1[:6]} von {dex_a} → {dex_b} ({spread:.2f}%)")
    # Importiere execute_trade nur hier (Importzyklen vermeiden)
    from trade_executor import execute_trade

    router_a = get_router(dex_a)
    router_b = get_router(dex_b)

    # Lambda zum Telegram-Benachrichtigen
    # (bot_notify ist ein async-callback, z.B. vom Bot)
    def notify(uid, msg):
        if bot_notify:
            asyncio.run_coroutine_threadsafe(
                bot_notify(uid, msg), asyncio.get_event_loop()
            )
        else:
            print(f"[{uid}] {msg}")

    # In eigenem Thread ausführen (executor kann blocken)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        None,
        execute_trade,
        user_id, token0, token1, router_a, router_b, 1,
        notify
    )

# --- Scanner Loop ---
async def scan_loop(bot_notify=None):
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

                # Preise für alle DEXe gleichzeitig holen (async)
                price_tasks = []
                for a, b in combinations:
                    ra = get_router(a)
                    rb = get_router(b)
                    if not ra or not rb:
                        continue
                    # Threaded, da Web3 nicht async
                    price_tasks.append((
                        (a, b),
                        asyncio.to_thread(get_price, ra, token0, token1),
                        asyncio.to_thread(get_price, rb, token0, token1)
                    ))

                for (dex_a, dex_b), t1, t2 in price_tasks:
                    price_a, price_b = await asyncio.gather(t1, t2)
                    spread = calculate_spread(price_a, price_b)
                    if spread >= spread_limit and spread > best_spread:
                        best_spread = spread
                        best_combo = (dex_a, dex_b)

                if best_combo:
                    dex_a, dex_b = best_combo
                    logging.info(f"[User {user_id}] Best Spread {best_spread:.2f}% bei {name} zwischen {dex_a} und {dex_b}")
                    if autotrade:
                        trigger_trade(user_id, token0, token1, dex_a, dex_b, best_spread, bot_notify=bot_notify)

        await asyncio.sleep(5)  # Etwas längeres Intervall, damit Sepolia-Rate-Limits nicht greifen

# --- Main für Standalone-Test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scan_loop())

