import os
import asyncio
from pyrogram import Client, filters
from flask import Flask, request

# =========================
# ENV VARIABLES
# =========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))   # Channel where files will be stored

# Hardcoded Webhook URL (Render app ka public URL)
WEBHOOK_URL = "https://telegram-filestore-bot-1.onrender.com/webhook"

PORT = int(os.getenv("PORT", 8080))

# =========================
# PYROGRAM BOT
# =========================
bot = Client(
    "filestore-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=4,
    in_memory=True
)

# /start
@bot.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply(
        "👋 Hi! I'm your File Store Bot.\n\n"
        "📤 Send me any file and I'll save it to the channel and give you back a link."
    )

# Broadcast (admin only)
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split()] if os.getenv("ADMINS") else []

@bot.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, message):
    if not message.reply_to_message:
        return await message.reply("⚠️ Reply to a message to broadcast.")
    count = 0
    async for user in bot.get_dialogs():
        try:
            await message.reply_to_message.copy(user.chat.id)
            count += 1
        except Exception:
            pass
    await message.reply(f"✅ Broadcast sent to {count} users.")

# File handling
@bot.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_file(client, message):
    if CHANNEL_ID != 0:
        saved = await message.copy(CHANNEL_ID)
        await message.reply(
            f"✅ File saved in channel!\n"
            f"📌 File ID: `{saved.id}`\n\n"
            "You can request this again anytime."
        )

# =========================
# FLASK SERVER
# =========================
flask_app = Flask(__name__)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json()
    if update:
        bot.process_update(update)
    return "ok"

@flask_app.route("/", methods=["GET"])
def home():
    return "🤖 Bot is running with Webhook!"

# =========================
# START
# =========================
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start())
    print("🚀 Bot started with Webhook...")
    flask_app.run(host="0.0.0.0", port=PORT)
