#!/usr/bin/env python3
"""
DexArbRadar: Multi-DEX Arbitrage Scanner with Telegram Alerts
"""

import asyncio
import yaml
import logging
from web3 import Web3
from telegram import Bot
from typing import Optional

class Dex:
    def __init__(self, name: str, factory_addr: str, w3: Web3) -> None:
        """
        :param name: Name of the DEX (e.g., "UniswapV2")
        :param factory_addr: Factory contract address
        :param w3: Web3 instance
        """
        self.name = name
        self.w3 = w3
        # Convert to checksum address
        address = Web3.to_checksum_address(factory_addr)
        self.factory = w3.eth.contract(
            address=address,
            abi=[
                {
                    "constant": True,
                    "inputs": [
                        {"name": "tokenA", "type": "address"},
                        {"name": "tokenB", "type": "address"}
                    ],
                    "name": "getPair",
                    "outputs": [{"name": "pair", "type": "address"}],
                    "type": "function"
                }
            ]
        )

    async def price(self, token0: str, token1: str) -> Optional[float]:
        """
        Fetch price token1 per token0 on this DEX
        :returns: price or None if no pool exists
        """
        pair_addr = self.factory.functions.getPair(token0, token1).call()
        if pair_addr == "0x0000000000000000000000000000000000000000":
            return None

        pair = self.w3.eth.contract(
            address=pair_addr,
            abi=[
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "_reserve0", "type": "uint112"},
                        {"name": "_reserve1", "type": "uint112"},
                        {"name": "_blockTimestampLast", "type": "uint32"}
                    ],
                    "type": "function"
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "type": "function"
                }
            ]
        )
        r0, r1, _ = pair.functions.getReserves().call()
        t0_addr = pair.functions.token0().call()
        return (r1 / r0) if (t0_addr.lower() == token0.lower()) else (r0 / r1)

async def monitor_pair(cfg: dict, dex_objs: list, bot: Optional[Bot]) -> None:
    t0 = Web3.to_checksum_address(cfg["pairs"][0]["token0"])
    t1 = Web3.to_checksum_address(cfg["pairs"][0]["token1"])
    threshold = cfg["threshold_spread"] / 100.0
    interval = cfg["poll_interval"]

    while True:
        prices = {}
        for dex in dex_objs:
            try:
                price = await dex.price(t0, t1)
                if price is not None:
                    prices[dex.name] = price
                    logging.info(f"{dex.name} price: {price:.6f}")
            except Exception as e:
                logging.warning(f"{dex.name} error: {e}")

        names = list(prices.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                pa, pb = prices[a], prices[b]
                spread = abs(pa - pb) / min(pa, pb)
                if spread >= threshold:
                    msg = (
                        f"🚨 Arbitrage Alert 🚨\n"
                        f"{a}: {pa:.6f}\n"
                        f"{b}: {pb:.6f}\n"
                        f"Spread: {spread*100:.2f}%"
                    )
                    logging.info(msg.replace("\n", " | "))
                    if bot:
                        await bot.send_message(cfg["telegram"]["chat_id"], msg)

        await asyncio.sleep(interval)

async def main() -> None:
    cfg = yaml.safe_load(open("config.yaml"))

    w3 = Web3(Web3.HTTPProvider(cfg["rpc_endpoints"]["ethereum"]))
    if not w3.is_connected():
        raise ConnectionError("Unable to connect to RPC endpoint.")

    dex_objs = [Dex(d["name"], d["factory"], w3) for d in cfg["dexes"]]

    bot = None
    token = cfg.get("telegram", {}).get("bot_token")
    if token:
        bot = Bot(token=token)

    await monitor_pair(cfg, dex_objs, bot)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    asyncio.run(main())

