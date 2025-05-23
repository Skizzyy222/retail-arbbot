# Retail Arbitrage Bot (MEV Arbitrage Bot via Telegram)

## Projektziel

Ein Minimal Viable Product (**MVP**) für einen Arbitrage-Bot, der mit Hilfe von MEV-Technologie und DeFi-Strategien Preisunterschiede zwischen DEXes aufspürt und ausnutzt. Der Bot wird vollständig über ein **Telegram-Interface** gesteuert, sodass auch User ohne Coding-Skills alles konfigurieren und triggern können.  
**Später** sollen eigene Nodes (z.B. Arbitrum/Mainnet) genutzt werden, aktuell liegt der Fokus auf **Testing/Strategien/Gas-Tests im Sepolia-Testnet**.

---

## Features (MVP)

- Wallet-Erstellung & Verwaltung für jeden Telegram-Nutzer
- Übersichtliche Telegram-UI mit Inline-Buttons zur Bot-Steuerung
- Auswahl von DEXes, Tokenpaaren, Spreads, Autotrading u.v.m.
- Anzeige der ETH-Balance & Konfiguration via Telegram
- Einfaches Versenden von Test-ETH an User
- Containerisierung via Docker (Trennung von Bot & Scanner)
- Verbindung zum Sepolia-Testnet (Infura/Public RPC)
- **Kein Lighthouse-Node notwendig für den MVP**

---

## Projektstruktur (Wichtigste Dateien/Ordner)

.
├── bot_control.py # Main Telegram Bot-Controller (UI, Wallet mgmt, User-Interaktion)
├── scanner/
│ └── async_scanner.py # Der Scanner zur Marktüberwachung (wird parallel zum Bot ausgeführt)
├── wallets/ # Hier werden User-Wallets als JSON gespeichert
├── config.yaml # Zentrale Konfiguration (Token, DEXes, etc.)
├── shared_state.py # Globaler State für User-Einstellungen
├── Dockerfile # Build-File für den Bot
├── docker-compose.yml # Orchestriert Bot & Scanner
└── .env # Umgebungsvariablen (API-Keys, RPC-URLs, etc.)

markdown
Kopieren
Bearbeiten

---

## Schnellstart: Lokales Setup

### Voraussetzungen

- [Docker](https://www.docker.com/) installiert
- Telegram-Account & eigenen Bot erstellt ([BotFather](https://t.me/BotFather))
- Einen Sepolia-Account/Key bei [Infura](https://infura.io/) oder anderen RPC-Anbietern (z.B. Alchemy)

### 1. `.env` Datei anlegen (im Projektordner):

```env
TELEGRAM_BOT_TOKEN=dein_telegram_bot_token
DEV_PRIVATE_KEY=dein_sepolia_private_key_mit_test_eth
RPC_URL_SEPOLIA=https://sepolia.infura.io/v3/DEIN_INFURA_KEY
Hinweis: DEV_PRIVATE_KEY muss ETH besitzen, um an User zu senden/testen!

2. config.yaml befüllen
Konfiguriere die DEXes, Tokenpaare, etc. Beispiel:

yaml
Kopieren
Bearbeiten
dexes:
  - name: UniswapV2
    router: '0x...'   # Sepolia Adresse
  - name: SushiSwap
    router: '0x...'

pairs:
  - name: WETH/USDC
    token0: '0x...'
    token1: '0x...'
Passe die Token/DEX-Adressen an dein Testnetzwerk an!

3. Docker Compose starten
bash
Kopieren
Bearbeiten
docker compose up --build
Das startet sowohl Bot als auch Scanner in getrennten Containern.

Der Bot ist erreichbar & steuert alles per Telegram.

Der Scanner überwacht die Märkte.

Telegram-User Interface
Starte deinen Bot via /start und folge dem Menü:

Wallet-Adresse und Einstellungen werden dir direkt angezeigt.

Über Buttons kannst du DEXes, Tokenpaare, Spread, Autotrading auswählen.

Mit /wallet siehst du jederzeit die Wallet-Balance (Sepolia).

ETH-Test-Transfers sind via Button möglich.

Typische Fehlerquellen & Lösungen
Wallet wird nicht gefunden:
Der Scanner sollte ebenfalls laufen, da dieser manchmal initial Wallets/States anlegt.

Fehlerhafte Sonderzeichen:
Wir nutzen HTML-Parsemode statt Markdown, um Telegram-Bugs mit Zeichen wie - oder _ zu vermeiden.

"Orphan Container" Warnung:
Kann ignoriert werden, oder docker compose up --remove-orphans verwenden.

Lighthouse nicht starten:
Der Bot & Scanner brauchen keinen eigenen Beacon-Node für MVP-Tests auf Sepolia!

Langsame Reaktion:
Prüfe Internetverbindung, Infura-Limit oder Bot/Scanner Crash im Log.

Entwicklung / Eigene Netzwerke
Später kann das Projekt auf beliebige EVM-Chains erweitert werden.

Aktuell ist der Fokus: Strategien, Gas-Tests & Telegram-UI MVP.

Für Mainnet/Arbitrum: Eigene Nodes/Provider konfigurieren (siehe .env).
"# retail-arbbot" 
