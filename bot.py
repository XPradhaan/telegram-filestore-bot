import os
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pymongo import MongoClient

# 🔧 Config Vars (Render के Dashboard से set करना)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # file storage channel
MONGO_URL = os.getenv("MONGO_URL")
ADMINS = [int(x) for x in os.getenv("ADMINS", "123456789").split(",")]

# ⚡ Bot & DB init
app = Client("filestorebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = MongoClient(MONGO_URL).filestore
files_collection = db.files
users_collection = db.users

# Default expiry in hours
DEFAULT_EXPIRY = 24

def get_user_expiry(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["expiry"] if user else DEFAULT_EXPIRY

# ✅ Save File Handler
@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_file(client, message):
    file_name = getattr(message.document or message.video or message.audio or message.photo, "file_name", "NoName")

    # Step 1 → Save file in channel
    sent_msg = await message.copy(CHANNEL_ID)

    expiry_hours = get_user_expiry(message.from_user.id)
    expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)

    # Step 2 → Save metadata
    files_collection.insert_one({
        "message_id": sent_msg.id,
        "file_name": file_name,
        "user_id": message.from_user.id,
        "expiry": expiry_time
    })

    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"user_id": message.from_user.id, "expiry": expiry_hours}},
        upsert=True
    )

    # Step 3 → Send file back
    await sent_msg.copy(
        chat_id=message.chat.id,
        protect_content=True,
        caption=f"✅ File Saved!\n📂 **Name:** {file_name}\n🆔 ID: `{sent_msg.id}`\n⏳ **Expiry:** {expiry_hours} Hours"
    )

# 🔎 /get command
@app.on_message(filters.command("get"))
async def get_file(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /get <file_id>")

    try:
        file_id = int(message.command[1])
    except:
        return await message.reply("⚠️ File ID must be a number")

    file_data = files_collection.find_one({"message_id": file_id})
    if not file_data:
        return await message.reply("❌ File not found in database.")

    if file_data["expiry"] < datetime.utcnow():
        return await message.reply("⏳ This file has expired. Contact admin.")

    await app.copy_message(
        chat_id=message.chat.id,
        from_chat_id=CHANNEL_ID,
        message_id=file_data["message_id"],
        protect_content=True
    )

# 📢 Broadcast Command (admin only)
@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /broadcast <your message>")

    text = message.text.split(" ", 1)[1]
    users = users_collection.find()
    success, fail = 0, 0

    for user in users:
        try:
            await app.send_message(user["user_id"], f"📢 Broadcast:\n\n{text}")
            success += 1
        except:
            fail += 1

    await message.reply(f"✅ Broadcast Done\n👤 Success: {success}\n❌ Failed: {fail}")

# ⚙️ Admin command: /setexpiry <user_id> <hours>
@app.on_message(filters.command("setexpiry") & filters.user(ADMINS))
async def set_expiry(client, message):
    if len(message.command) < 3:
        return await message.reply("⚠️ Usage: /setexpiry <user_id> <hours>")

    user_id = int(message.command[1])
    hours = int(message.command[2])

    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"expiry": hours}},
        upsert=True
    )
    await message.reply(f"✅ Expiry for user {user_id} set to {hours} hours.")

# 🏃 Run Bot
print("🤖 Bot Started!")
app.run()
