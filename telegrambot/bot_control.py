import logging
import yaml
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from shared_state import user_state

# --- Lade Umgebungsvariablen ---
load_dotenv()

# --- Konfiguration laden ---
with open("config.yaml", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

# --- Helper: Callback-Keyboard erstellen ---
def build_keyboard(user_id):
    state = user_state.get(user_id, {})
    selected_dexes = state.get("dexes", set())
    selected_pairs = state.get("pairs", set())
    autotrade = state.get("autotrade", False)
    spread = state.get("spread", "1.0")

    # DEX Buttons
    dex_buttons = [
        InlineKeyboardButton(
            f"{'✅' if d['name'] in selected_dexes else '☐'} {d['name']}",
            callback_data=f"DEX::{d['name']}"
        ) for d in CONFIG.get("dexes", [])
    ]

    # Pair Buttons
    pair_buttons = [
        InlineKeyboardButton(
            f"{'✅' if idx in selected_pairs else '☐'} {p.get('name', p['token0'][:6] + '/' + p['token1'][:6])}",
            callback_data=f"PAIR::{idx}"
        ) for idx, p in enumerate(CONFIG.get("pairs", []))
    ]

    # Spread Buttons
    spreads = ["0.5", "1.0", "2.0"]
    spread_buttons = [
        InlineKeyboardButton(
            f"{'✅' if s == spread else '☐'} {s}%",
            callback_data=f"SPREAD::{s}"
        ) for s in spreads
    ]
    spread_buttons.append(InlineKeyboardButton("✏️ Custom", callback_data="SPREAD::CUSTOM"))

    # Autotrade Button
    trade_button = InlineKeyboardButton(
        f"🚀 Autotrade {'✅ ON' if autotrade else '❌ OFF'}",
        callback_data="AUTOTRADE::TOGGLE"
    )

    keyboard = [
        [InlineKeyboardButton("💱 DEX Auswahl", callback_data="IGNORE")], *[ [b] for b in dex_buttons ],
        [InlineKeyboardButton("🪙 Tokenpaare", callback_data="IGNORE")], *[ [b] for b in pair_buttons ],
        [InlineKeyboardButton("📊 Spread Trigger", callback_data="IGNORE")], [*spread_buttons],
        [trade_button],
        [InlineKeyboardButton("📈 Hebel (bald verfügbar)", callback_data="IGNORE")]

        [InlineKeyboardButton("📋 Status anzeigen", callback_data="STATUS")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state.setdefault(user_id, {"dexes": set(), "pairs": set(), "autotrade": False, "spread": "1.0"})
    await update.message.reply_text("Willkommen! Konfiguriere deinen Scanner:",
                                    reply_markup=build_keyboard(user_id))

# --- Callback Handler ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_state.setdefault(user_id, {"dexes": set(), "pairs": set(), "autotrade": False, "spread": "1.0"})

    parts = query.data.split("::")
    if len(parts) != 2:
        return  # z. B. bei Buttons wie "IGNORE" oder "STATUS"
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
            await query.message.reply_text("Bitte gib den gewünschten Spread in % an (z. B. 0.8):")
            context.user_data["awaiting_spread"] = True
            return
        else:
            state["spread"] = value

    elif action == "AUTOTRADE":
        state["autotrade"] = not state["autotrade"]

    elif action == "STATUS":
        return await show_status(query, state)

    await query.edit_message_reply_markup(reply_markup=build_keyboard(user_id))

async def handle_custom_spread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if context.user_data.get("awaiting_spread"):
        try:
            val = str(float(update.message.text))
            user_state[user_id]["spread"] = val
            await update.message.reply_text(f"Spread gesetzt auf {val}%")
        except ValueError:
            await update.message.reply_text("Ungültiger Wert. Bitte gib eine Zahl ein.")
        context.user_data["awaiting_spread"] = False

async def show_status(query, state):
    dexes = ", ".join(state["dexes"] or ["(keine)"])
    pairs = ", ".join([
        CONFIG['pairs'][i].get('name', f"{CONFIG['pairs'][i]['token0'][:6]}/{CONFIG['pairs'][i]['token1'][:6]}")
        for i in state["pairs"]
    ]) or "(keine)"
    spread = state["spread"]
    auto = "Aktiv" if state["autotrade"] else "Inaktiv"
    msg = (
        f"\U0001F9FE *Deine Konfiguration:*\n"
        f"DEXes: {dexes}\n"
        f"Paare: {pairs}\n"
        f"Spread: {spread}%\n"
        f"Autotrade: {auto}"
    )
    await query.message.reply_text(msg, parse_mode="Markdown")

# --- Bot Start ---
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN fehlt in .env Datei.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_spread))

    print("🤖 Bot läuft...")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()



