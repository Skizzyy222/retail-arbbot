import logging
import yaml
import os
import json
import asyncio
from wallets.wallet_manager import get_or_create_wallet
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from shared_state import user_state
from trade_executor import execute_trade

# --- Umgebungsvariablen laden ---
load_dotenv()
RPC_URL = os.getenv("RPC_URL_SEPOLIA", "http://localhost:8545")
web3 = Web3(Web3.HTTPProvider(RPC_URL))
DEV_PRIVATE_KEY = os.getenv("DEV_PRIVATE_KEY")
dev_account = Account.from_key(DEV_PRIVATE_KEY)

with open("config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

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

    spread_options = ["0.5", "1.0", "2.0"]
    spread_buttons = []
    if spread == "CUSTOM_PENDING":
        for s in spread_options:
            spread_buttons.append(
                InlineKeyboardButton(f"☐ {s}%", callback_data=f"SPREAD::{s}")
            )
        spread_buttons.append(
            InlineKeyboardButton("✅ Custom", callback_data="SPREAD::CUSTOM")
        )
    else:
        for s in spread_options:
            is_selected = (str(spread) == s)
            spread_buttons.append(
                InlineKeyboardButton(f"{'✅' if is_selected else '☐'} {s}%", callback_data=f"SPREAD::{s}")
            )
        is_custom = not str(spread) in spread_options
        spread_buttons.append(
            InlineKeyboardButton(f"{'✅' if is_custom else '☐'} Custom", callback_data="SPREAD::CUSTOM")
        )

    trade_button = InlineKeyboardButton(
        f"🚀 Trade jetzt!", callback_data="TRADE::NOW"
    )
    autotrade_button = InlineKeyboardButton(
        f"⚡ Autotrade {'✅ ON' if autotrade else '❌ OFF'}", callback_data="AUTOTRADE::TOGGLE"
    )

    keyboard = [
        [InlineKeyboardButton("💱 DEX Auswahl", callback_data="IGNORE")], *[[b] for b in dex_buttons],
        [InlineKeyboardButton("🪙 Tokenpaare", callback_data="IGNORE")], *[[b] for b in pair_buttons],
        [InlineKeyboardButton("📊 Spread Trigger", callback_data="IGNORE")], [*spread_buttons],
        [trade_button],
        [autotrade_button],
        [InlineKeyboardButton("📈 Hebel (bald verfügbar)", callback_data="IGNORE")],
        [InlineKeyboardButton("📋 Status anzeigen", callback_data="STATUS")]
    ]

    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    address, _ = get_or_create_wallet(user_id)
    user_state.setdefault(user_id, {
        "dexes": set(),
        "pairs": set(),
        "autotrade": False,
        "spread": "1.0"
    })

    msg = await update.message.reply_text(
        f"👋 <b>Willkommen beim Arbitrage-Bot!</b>\n"
        f"👛 <b>Deine Wallet-Adresse:</b>\n<code>{address}</code>\n\n"
        f"Nutze die Buttons unten, um deine Scanner-Einstellungen zu konfigurieren:",
        reply_markup=build_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )
    context.user_data["menu_message_id"] = msg.message_id

async def wallet_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_path = os.path.join("wallets", f"{user_id}.json")

    try:
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
        address = Web3.to_checksum_address(wallet_data["address"])
        eth_balance = web3.eth.get_balance(address)
        eth_display = web3.from_wei(eth_balance, "ether")
    except Exception as e:
        await update.message.reply_text("❌ Wallet nicht gefunden. Starte mit /start.", parse_mode=ParseMode.HTML)
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Adresse kopieren", callback_data=f"COPY::{address}")],
        [InlineKeyboardButton("📤 ETH senden (Dev)", callback_data="WITHDRAW::NOW")]
    ])

    msg = (
        f"💼 <b>Deine Wallet:</b>\n"
        f"<code>{address}</code>\n"
        f"💸 <b>ETH Balance:</b> {eth_display} ETH"
    )

    await update.message.reply_text(msg, reply_markup=keyboard, parse_mode=ParseMode.HTML)

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
    tx_hash_hex = web3.to_hex(tx_hash)
    return tx_hash_hex

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_state.setdefault(user_id, {"dexes": set(), "pairs": set(), "autotrade": False, "spread": "1.0"})

    parts = query.data.split("::")
    if len(parts) != 2:
        if query.data == "STATUS":
            return await show_status(query, state)
        return

    action, value = parts

    menu_message_id = context.user_data.get("menu_message_id")
    chat_id = query.message.chat_id

    notification_text = None

    if action == "DEX":
        if value in state["dexes"]:
            if len(state["dexes"]) > 2:
                state["dexes"].remove(value)
            else:
                notification_text = "❗ Mindestens zwei DEX müssen ausgewählt bleiben."
        else:
            state["dexes"].add(value)

    elif action == "PAIR":
        i = int(value)
        if i in state["pairs"]:
            if len(state["pairs"]) > 1:
                state["pairs"].remove(i)
            else:
                notification_text = "❗ Mindestens ein Tokenpaar muss ausgewählt bleiben."
        else:
            state["pairs"].add(i)

    elif action == "SPREAD":
        if value == "CUSTOM":
            state["spread"] = "CUSTOM_PENDING"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text="Bitte gib deinen gewünschten Spread in % an (z.B. 0.8):",
                reply_markup=build_keyboard(user_id),
                parse_mode=ParseMode.HTML
            )
            context.user_data["awaiting_spread"] = True
            return
        else:
            state["spread"] = value
            notification_text = f"✅ Spread gesetzt auf {value}%"

    elif action == "AUTOTRADE":
        state["autotrade"] = not state["autotrade"]
        notification_text = f"Autotrade {'aktiviert' if state['autotrade'] else 'deaktiviert'}."

    elif action == "TRADE":
        if not state["pairs"] or not state["dexes"]:
            notification_text = "❌ Bitte wähle mindestens 1 Paar und 2 DEX aus!"
        else:
            pair_idx = next(iter(state["pairs"]))
            dex_names = list(state["dexes"])
            pair = CONFIG["pairs"][pair_idx]
            dex_a = [d for d in CONFIG["dexes"] if d["name"] == dex_names[0]][0]["router"]
            dex_b = [d for d in CONFIG["dexes"] if d["name"] == dex_names[1]][0]["router"]
            token0 = pair["token0"]
            token1 = pair["token1"]

            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                execute_trade,
                user_id,
                token0,
                token1,
                dex_a,
                dex_b,
                1,
                lambda uid, msg: asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=uid, text=msg, parse_mode="HTML"),
                    loop
                )
            )
            notification_text = "🚦 Trade wird ausgeführt..."

    elif action == "COPY":
        notification_text = f"📋 Adresse kopiert:\n<code>{value}</code>"

    elif action == "WITHDRAW":
        tx_hash = await send_eth_to_user(user_id)
        notification_text = f"📤 0.01 Sepolia ETH gesendet!\n🔗 TX Hash: <code>{tx_hash}</code>"

    if menu_message_id:
        if notification_text:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text=notification_text,
                reply_markup=build_keyboard(user_id),
                parse_mode=ParseMode.HTML
            )
        else:
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=menu_message_id,
                reply_markup=build_keyboard(user_id)
            )

async def handle_custom_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    menu_message_id = context.user_data.get("menu_message_id")
    chat_id = update.effective_chat.id
    if context.user_data.get("awaiting_spread"):
        try:
            val = float(update.message.text)
            if not (0.1 <= val <= 10.0):
                raise ValueError("Spread außerhalb des erlaubten Bereichs.")
            state = user_state[user_id]
            state["spread"] = str(val)
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text=f"✅ Spread gesetzt auf {val}%",
                reply_markup=build_keyboard(user_id),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            user_state[user_id]["spread"] = "1.0"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=menu_message_id,
                text="❌ Ungültiger Wert. Bitte gib eine Zahl zwischen 0.1 und 10.0 ein.",
                reply_markup=build_keyboard(user_id),
                parse_mode=ParseMode.HTML
            )
        context.user_data["awaiting_spread"] = False

async def show_status(query, state):
    user_id = query.from_user.id
    wallet_path = os.path.join("wallets", f"{user_id}.json")

    try:
        with open(wallet_path, "r") as f:
            wallet_data = json.load(f)
        address = Web3.to_checksum_address(wallet_data["address"])
        eth_balance = web3.eth.get_balance(address)
        eth_display = web3.from_wei(eth_balance, "ether")
    except Exception:
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
        f"🧾 <b>Deine Konfiguration:</b>\n"
        f"📛 Wallet: <code>{address}</code>\n"
        f"💸 ETH (Sepolia): {eth_display} ETH\n"
        f"\n"
        f"DEXes: {dexes}\n"
        f"Paare: {pairs}\n"
        f"Spread: {spread}%\n"
        f"Autotrade: {auto}"
    )
    await query.message.reply_text(msg, parse_mode=ParseMode.HTML)

# =============== NEU: /tradelog und /profit ===============

async def tradelog_handler(update, context):
    user_id = update.effective_user.id
    log_file = os.path.join("trades", f"tradelog_{user_id}.json")

    if not os.path.exists(log_file):
        await update.message.reply_text("❌ Kein Tradelog gefunden. Starte einen Trade, um Einträge zu erzeugen!")
        return

    with open(log_file, "r") as f:
        trades = json.load(f)

    if not trades:
        await update.message.reply_text("📄 Noch keine Trades vorhanden.")
        return

    msg = "<b>Letzte Trades:</b>\n"
    max_trades = 10
    for t in trades[-max_trades:]:
        status = "✅" if t.get("status") == "SUCCESS" else "❌"
        msg += (
            f"\n{status} <b>{t['pair']}</b>\n"
            f"Zeit: <code>{t['timestamp']}</code>\n"
            f"DEX: {t['dex_a']} ➔ {t['dex_b']}\n"
            f"Profit: <b>{t.get('profit', 0):.6f} ETH</b>\n"
            f"Gas: {t.get('gas_used', 'N/A')}\n"
            f"TX: <code>{t['tx_hashes'][-1] if t['tx_hashes'] else '-'}</code>\n"
        )
        if t.get('dev_cut', 0):
            msg += f"Dev-Cut: <b>{t['dev_cut']:.6f} ETH</b>\n"
        if t.get('error'):
            msg += f"Fehler: <code>{t['error']}</code>\n"
        msg += "—" * 12

    await update.message.reply_text(msg, parse_mode="HTML")

async def profit_handler(update, context):
    user_id = update.effective_user.id
    log_file = os.path.join("trades", f"tradelog_{user_id}.json")

    if not os.path.exists(log_file):
        await update.message.reply_text("❌ Kein Tradelog gefunden. Starte einen Trade, um Gewinne zu sehen!")
        return

    with open(log_file, "r") as f:
        trades = json.load(f)

    profit_total = sum(t.get("profit", 0) for t in trades if t.get("status") == "SUCCESS" and t.get("profit") is not None)
    dev_cut_total = sum(t.get("dev_cut", 0) for t in trades if t.get("status") == "SUCCESS" and t.get("dev_cut") is not None)

    msg = (
        f"💰 <b>Dein Gesamtprofit:</b> <code>{profit_total:.6f} ETH</code>\n"
        f"🏦 <b>Abgeführter Dev-Cut:</b> <code>{dev_cut_total:.6f} ETH</code>\n"
        f"(Trades: {len(trades)})"
    )
    await update.message.reply_text(msg, parse_mode="HTML")

# =============== ENDE NEU ===============

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN fehlt in .env Datei.")
        return

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", wallet_info))
    app.add_handler(CommandHandler("tradelog", tradelog_handler))   # <-- NEU
    app.add_handler(CommandHandler("profit", profit_handler))       # <-- NEU
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_spread))

    print("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()


