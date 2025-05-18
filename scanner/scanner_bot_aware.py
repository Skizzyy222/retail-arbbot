import logging
import time
import sys
import os
import yaml

# Telegram shared state laden
sys.path.append(r"C:\Users\skizz\Desktop\retail-arbbot\telegrambot")
from shared_state import user_state

# --- Konfiguration laden ---
with open("config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

def get_price_from_dex(dex_name, token0, token1):
    # Dummy: Rückgabe von 1.0 für alle
    return 1.0

def check_spread(p1, p2):
    if p1 == 0:
        return 0.0
    return abs(p1 - p2) / min(p1, p2) * 100

def scan():
    print("🔍 Starte Scanner...")
    while True:
        for user_id, state in user_state.items():
            selected_dexes = list(state.get("dexes", []))
            selected_pairs = list(state.get("pairs", []))
            spread_limit = float(state.get("spread", 1.0))
            autotrade = state.get("autotrade", False)

            if len(selected_dexes) < 2 or len(selected_pairs) < 1:
                continue  # Bedingungen aus Bot werden hier nur überprüft

            for pair_index in selected_pairs:
                pair = CONFIG["pairs"][pair_index]
                token0, token1 = pair["token0"], pair["token1"]

                prices = {}
                for dex_name in selected_dexes:
                    prices[dex_name] = get_price_from_dex(dex_name, token0, token1)

                dex_names = list(prices.keys())
                for i in range(len(dex_names)):
                    for j in range(i + 1, len(dex_names)):
                        d1, d2 = dex_names[i], dex_names[j]
                        s = check_spread(prices[d1], prices[d2])
                        if s >= spread_limit:
                            logging.info(f"User {user_id}: SPREAD {s:.2f}% zw. {d1} und {d2} für {token0[:6]}/{token1[:6]}")
                            if autotrade:
                                print(f"🚀 Trade triggered für User {user_id} auf {d1} → {d2}")

        time.sleep(5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scan()

