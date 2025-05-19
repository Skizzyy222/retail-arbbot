# retail-arbbot Docker Setup

## Starten:

1. Stelle sicher, dass Docker & Docker Compose installiert sind.
2. Lege eine `.env`-Datei im Projektverzeichnis an (sie wird **nicht ins Image kopiert**).
3. Starte alles mit:

```
docker-compose up --build
```

## Enthaltene Services:

- `geth`: lokale Sepolia-Testnet Node (Snap-Sync)
- `bot`: startet `bot_control.py` und nutzt `.env`

## Hinweise:
- `.env` bleibt lokal, sicher & unversioniert.
- Volumes sorgen dafür, dass Wallet-Daten & Chain-Daten erhalten bleiben.

