import logging
import yaml
import os
import json
from wallets.wallet_manager import get_or_create_wallet
from dotenv import load_dotenv
import logging
import yaml
import os
import json
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from wallets.wallet_manager import get_or_create_wallet
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from shared_state import user_state

# --- Umgebungsvariablen laden ---
load_dotenv()

# --- Web3 Setup für lokale Sepolia Node ---
RPC_URL = os.getenv("RPC_URL_SEPOLIA", "http://localhost:8545")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# --- Developer Wallet (für Withdraw/Testzahlungen) ---
DEV_PRIVATE_KEY = os.getenv("DEV_PRIVATE_KEY")
dev_account = Account.from_key(DEV_PRIVATE_KEY)

# --- Konfiguration laden ---
with open("config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# --- Inline-UI bauen ---
def build_keyboard(user_id):
    state = user_state.get(user_id, {})
    selected_dexes = state.get("dexes", set())
    selected_pairs = state.get("pairs", set())
    autotrade = state.get("autotrade", False)
    spread = state.get("spread", "1.0")

    dex_buttons = [
        InlineKeyboardButton(
            f"{'✅' if d['name'] in selected_dexes else '☐'} {d['name']}",
            callback_data=f"DEX::{d['name']}"
        ) for d in CONFIG.get("dexes", [])
    ]

    pair_buttons = [
    InlineKeyboardButton(
        f"{'✅' if idx in selected_pairs else '☐'} " +
        p.get("name", f"{p['token0'][:6]}/{p['token1'][:6]}"),
        callback_data=f"PAIR::{idx}"
    )
    for idx, p in enumerate(CONFIG.get("pairs", []))
]


    spread_buttons = []
    for s in ["0.5", "1.0", "2.0"]:
        is_selected = (s == spread)
        spread_buttons.append(
            InlineKeyboardButton(f"{'✅' if is_selected else '☐'} {s}%", callback_data=f"SPREAD::{s}")
        )
    is_custom = spread not in ["0.5", "1.0", "2.0"] and not str(spread).startswith("CUSTOM")
    spread_buttons.append(InlineKeyboardButton(f"{'✅' if is_custom else '☐'} Custom", callback_data="SPREAD::CUSTOM"))

    trade_button = InlineKeyboardButton(
        f"🚀 Autotrade {'✅ ON' if autotrade else '❌ OFF'}",
        callback_data="AUTOTRADE::TOGGLE"
    )

    keyboard = [
        [InlineKeyboardButton("💱 DEX Auswahl", callback_data="IGNORE")], *[[b] for b in dex_buttons],
        [InlineKeyboardButton("🪙 Tokenpaare", callback_data="IGNORE")], *[[b] for b in pair_buttons],
        [InlineKeyboardButton("📊 Spread Trigger", callback_data="IGNORE")], [*spread_buttons],
        [trade_button],
        [InlineKeyboardButton("📈 Hebel (bald verfügbar)", callback_data="IGNORE")],
        [InlineKeyboardButton("📋 Status anzeigen", callback_data="STATUS")]
    ]

    return InlineKeyboardMarkup(keyboard)

# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address, _ = get_or_create_wallet(user_id)
    user_state.setdefault(user_id, {
        "dexes": set(),
        "pairs": set(),
        "autotrade": False,
        "spread": "1.0"
    })
    await update.message.reply_text(
        f"👋 Willkommen beim Arbitrage-Bot!\n"
        f"👛 Deine Wallet-Adresse:\n`{address}`\n\n"
        "Nutze die Buttons unten, um deine Scanner-Einstellungen zu konfigurieren:",
        reply_markup=build_keyboard(user_id),
        parse_mode="Markdown"
    )

# --- /wallet Command ---
async def wallet_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_path = os.path.join("wallets", f"{user_id}.json")

    try:
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
        address = Web3.to_checksum_address(wallet_data["address"])
        eth_balance = web3.eth.get_balance(address)
        eth_display = web3.from_wei(eth_balance, "ether")
    except:
        await update.message.reply_text("❌ Wallet nicht gefunden. Starte mit /start.")
        return

    escaped_address = escape_markdown(address, version=2)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Adresse kopieren", callback_data=f"COPY::{address}")],
        [InlineKeyboardButton("📤 ETH senden (Dev)", callback_data="WITHDRAW::NOW")]
    ])

    msg = (
        f"*💼 Deine Wallet:*\n"
        f"`{escaped_address}`\n"
        f"💸 *ETH Balance:* {eth_display} ETH"
    )

    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

# --- ETH Transfer (Dev → User) ---
async def send_eth_to_user(user_id):
    wallet_path = os.path.join("wallets", f"{user_id}.json")
    with open(wallet_path, "r") as f:
        wallet_data = json.load(f)
    recipient = Web3.to_checksum_address(wallet_data["address"])

    nonce = web3.eth.get_transaction_count(dev_account.address)
    tx = {
        "to": recipient,
        "value": web3.to_wei(0.01, "ether"),
        "gas": 21000,
        "gasPrice": web3.eth.gas_price,
        "nonce": nonce,
        "chainId": 11155111
    }

    signed_tx = web3.eth.account.sign_transaction(tx, private_key=DEV_PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    return web3.to_hex(tx_hash)

# --- Callback Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_state.setdefault(user_id, {"dexes": set(), "pairs": set(), "autotrade": False, "spread": "1.0"})

    parts = query.data.split("::")
    if len(parts) != 2:
        return
    action, value = parts

    if action == "DEX":
        if value in state["dexes"]:
            if len(state["dexes"]) > 2:
                state["dexes"].remove(value)
            else:
                await query.message.reply_text("❗ Mindestens zwei DEX müssen ausgewählt bleiben.")
        else:
            state["dexes"].add(value)

    elif action == "PAIR":
        i = int(value)
        if i in state["pairs"]:
            if len(state["pairs"]) > 1:
                state["pairs"].remove(i)
            else:
                await query.message.reply_text("❗ Mindestens ein Tokenpaar muss ausgewählt bleiben.")
        else:
            state["pairs"].add(i)

    elif action == "SPREAD":
        if value == "CUSTOM":
            await query.message.reply_text("Bitte gib deinen gewünschten Spread in % an (z. B. 0.8):")
            context.user_data["awaiting_spread"] = True
            state["spread"] = "CUSTOM_PENDING"
            return
        else:
            state["spread"] = value

    elif action == "AUTOTRADE":
        state["autotrade"] = not state["autotrade"]

    elif action == "STATUS":
        return await show_status(query, state)

    elif action == "COPY":
        await query.message.reply_text(f"📋 Adresse kopiert:\n`{value}`", parse_mode="Markdown")

    elif action == "WITHDRAW":
        tx_hash = await send_eth_to_user(user_id)
        await query.message.reply_text(
            f"📤 0.01 Sepolia ETH gesendet!\n🔗 TX Hash: `{tx_hash}`",
            parse_mode="Markdown"
        )

    await query.edit_message_reply_markup(reply_markup=build_keyboard(user_id))

# --- Custom Spread ---
async def handle_custom_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("awaiting_spread"):
        try:
            val = float(update.message.text)
            if not (0.1 <= val <= 10.0):
                raise ValueError("Spread außerhalb des erlaubten Bereichs.")
            state = user_state[user_id]
            state["spread"] = str(val)
            await update.message.reply_text(f"✅ Spread gesetzt auf {val}%")
        except Exception:
            user_state[user_id]["spread"] = "1.0"
            await update.message.reply_text("❌ Ungültiger Wert. Bitte gib eine Zahl zwischen 0.1 und 10.0 ein.")
        context.user_data["awaiting_spread"] = False

# --- Status anzeigen ---
async def show_status(query, state):
    user_id = query.from_user.id
    wallet_path = os.path.join("wallets", f"{user_id}.json")

    try:
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
        address = Web3.to_checksum_address(wallet_data["address"])
        eth_balance = web3.eth.get_balance(address)
        eth_display = web3.from_wei(eth_balance, "ether")
    except:
        address = "(nicht gefunden)"
        eth_display = "Fehler"

    dexes = ", ".join(state["dexes"] or ["(keine)"])
    pairs = ", ".join([
        f"{CONFIG['pairs'][i].get('name', CONFIG['pairs'][i]['token0'][:6] + '/' + CONFIG['pairs'][i]['token1'][:6])}"
        for i in state["pairs"]
    ]) or "(keine)"
    spread = state["spread"]
    auto = "Aktiv" if state["autotrade"] else "Inaktiv"

    msg = (
        f"\U0001F9FE *Deine Konfiguration:*\n"
        f"📛 Wallet: `{address}`\n"
        f"💸 ETH (Sepolia lokal): {eth_display} ETH\n"
        f"\n"
        f"DEXes: {dexes}\n"
        f"Paare: {pairs}\n"
        f"Spread: {spread}%\n"
        f"Autotrade: {auto}"
    )
    await query.message.reply_text(msg, parse_mode="Markdown")

# --- Bot starten ---
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN fehlt in .env Datei.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_info))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_spread))

    print("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

