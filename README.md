# 📘 Projektüberblick: retail-arbbot – Elite Arbitrage MVP

## 🎯 Ziel

Ein hochperformanter Arbitrage-Bot, der:

* unter **5 ms** auf Preisdifferenzen zwischen DEXes reagiert
* für **Telegram-Nutzer extrem einfach** steuerbar ist
* auf **Benutzer-Wallets** tradet (keine Verwahrung)
* später **Flashbots/MEV-Schutz**, **Hebel-Trades** & **Mainnet-Kompatibilität** unterstützt

Das langfristige Ziel: **monatlich 10.000 €+ Gewinn** durch skalierbares Arbitrage-Trading.

---

## ✅ Aktueller Stand

### ✔ Funktional

* [x] Telegrambot mit Inline-Keyboard zur Konfiguration (DEX, Paare, Spread, Autotrade, Hebel "bald verfügbar")
* [x] Scanner `scanner_bot_aware.py`: asynchroner Spread-Scanner auf Basis der User-Auswahl
* [x] Executor `trade_executor.py`: nutzt User-Wallets, sendet echte TX, erkennt WETH-Transfers, macht `approve()` bei Token
* [x] Wallet-Manager: pro User eigene Wallet mit persistenter Speicherung
* [x] Lokale Geth Sepolia Node: getestet & verbunden
* [x] Token-Deploy-Skript via Hardhat (inkl. PEPE, FLOKI, etc.)

### 📁 Struktur

* `/telegrambot/` → Bot-Interface & User-Config
* `/scanner/` → Preisüberwachung + Trigger
* `/executor/` → TX-Ausführung (direkt oder später via Flashbots)
* `/wallets/` → 🔒 pro Nutzer: `address + private_key`
* `/dex_testnet/` → Smart Contracts + Deploy-Skripte

---

## 🔜 Nächste Schritte (Prio hoch → niedrig)

1. **Swap-Logik fertigstellen:** echte Token-Swaps via Uniswap/Sushiswap Router (kein Dummy-Transfer)
2. **Liquidity Pools erstellen:** eigene Liquidität auf Sepolia einfügen
3. **Balance-Checker integrieren:** Nutzerwarnung bei zu wenig ETH
4. **Trade-Logging ausbauen:** JSON, Telegram Push oder DB (Mongo?)
5. **Hebel-Option vorbereiten:** UI-Funktionalität + Vorbereitung für Flashloan/Leveraged Trade
6. **Flashbots-Anbindung planen:** für Mainnet-Launch vorbereiten (RPC + Relay)

---

## 🔐 Sicherheit & Struktur

* `.env` & `wallets/` sind per `.gitignore` geschützt
* Trades laufen über **nicht-custodiale** Wallets
* Codestruktur ist klar getrennt & dokumentiert

---

## 🚀 Vision

Ein MVP, der wie ein Profi-Bot agiert:

* voll asynchron
* nutzerfreundlich (Telegram-gesteuert)
* auf echte Marktbedingungen optimierbar
* bereit für den Übergang zum Mainnet mit Flashbots-Optimierung

Wir bauen kein Experiment. Wir bauen ein Trading-Werkzeug. 💼⚡
