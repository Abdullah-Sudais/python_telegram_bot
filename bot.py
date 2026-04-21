from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import asyncio
import os

TOKEN = os.getenv("TOKEN")

user_target = {}
user_data = {}

# ✅ Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
        "👋 Welcome to BTC Alert Bot!\n\n"
        "📌 Available Commands:\n"
        "/set <coin> <price> - Set target price e.g., /set BTC 70000\n"
        "/track <step> - Track price changes\n"
        # "/help - Show this menu again\n"
        "/stop - Stop tracking\n"
    )


    await update.message.reply_text(message)

# ✅ Set price command
async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    try:
        coin = context.args[0].upper() + "USDT"
        target = float(context.args[1])

        if user_id not in user_target:
            user_target[user_id] = {}

        user_target[user_id][coin] = target

        await update.message.reply_text(f"✅ {coin} target set at {target}")

    except:
        await update.message.reply_text("Usage: /set BTC 80000")

# ✅ Keep this SIMPLE (sync function)
def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    data = response.json()
    return float(data['price'])

# ✅ Background task
async def check_price(app):
    while True:
        try:
            # --- Target price alerts ---
            for user_id, coins in list(user_target.items()):
                to_remove = []

                for coin, target in list(coins.items()):  # ✅ snapshot
                    price = get_price(coin)

                    if price >= target:
                        await app.bot.send_message(
                            chat_id=user_id,
                            text=f"🚀 {coin} reached {price}"
                        )
                        to_remove.append(coin)

                for coin in to_remove:              # ✅ delete after loop
                    del user_target[user_id][coin]

                if user_id in user_target and not user_target[user_id]:
                    del user_target[user_id]

            # --- Step tracking ---
            btc_price = get_price("BTCUSDT")

            for user_id, data in list(user_data.items()):
                step = data["step"]
                last_price = data["last_price"]

                if abs(btc_price - last_price) >= step:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=f"📊 BTC moved to {btc_price}"
                    )
                    user_data[user_id]["last_price"] = btc_price

        except Exception as e:
            print(f"[check_price error] {e}")  # ✅ never die silently

        await asyncio.sleep(10)

# ✅ Proper startup hook
async def start_background(app):
    asyncio.create_task(check_price(app))


async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_target.pop(user_id, None)  # ✅ clear target tracking if setting step

    try:
        step = float(context.args[0])

        btc_price = get_price("BTCUSDT")

        user_data[user_id] = {
            "step": step,
            "last_price": btc_price
        }

        await update.message.reply_text(f"📊 Current Price: {btc_price} Tracking every {step}$ change")

    except:
        await update.message.reply_text("Usage: /track 100")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id in user_target or user_id in user_data:
        user_target.pop(user_id, None)
        user_data.pop(user_id, None)
        await update.message.reply_text("Tracking stopped.")
    else:
        await update.message.reply_text("No active tracking.")

# ✅ Build app
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("set", set_price))
app.add_handler(CommandHandler("track", track))

# ✅ Run background task after bot starts
app.post_init = start_background

# ✅ Start bot
app.run_polling()