import os
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pymongo import MongoClient

# ---------------- CONFIG ---------------- #
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # File storage channel
MONGO_URL = os.getenv("MONGO_URL")
ADMINS = [int(x) for x in os.getenv("ADMINS", "123456789").split(",")]

# ---------------- INIT ---------------- #
app = Client("filestorebot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = MongoClient(MONGO_URL).filestore
files_collection = db.files
users_collection = db.users

DEFAULT_EXPIRY = 24  # hours


def get_user_expiry(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["expiry"] if user else DEFAULT_EXPIRY


# ---------------- SAVE FILE ---------------- #
@app.on_message(filters.document | filters.video | filters.audio | filters.photo)
async def save_file(client, message):
    file_name = getattr(
        message.document or message.video or message.audio or message.photo,
        "file_name",
        "NoName"
    )

    # Save file in channel (Permanent)
    sent_msg = await message.copy(CHANNEL_ID)

    expiry_hours = get_user_expiry(message.from_user.id)
    expiry_time = datetime.utcnow() + timedelta(hours=expiry_hours)

    # Save in DB
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

    # Send back to user (Direct Send)
    await sent_msg.copy(
        chat_id=message.chat.id,
        protect_content=True,
        caption=f"✅ File Saved!\n📂 **Name:** {file_name}\n🆔 ID: `{sent_msg.id}`\n⏳ **Expiry:** {expiry_hours} Hours"
    )


# ---------------- GET FILE ---------------- #
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


# ---------------- BROADCAST ---------------- #
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


# ---------------- ADMIN COMMANDS ---------------- #
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


@app.on_message(filters.command("userinfo") & filters.user(ADMINS))
async def user_info(client, message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usage: /userinfo <user_id>")

    user_id = int(message.command[1])
    user = users_collection.find_one({"user_id": user_id})

    if not user:
        return await message.reply("❌ User not found.")

    await message.reply(f"👤 **User ID:** {user_id}\n⏳ **Expiry:** {user['expiry']} hours")


# ---------------- START ---------------- #
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply("👋 Welcome to FileStore Bot!\n\n📂 Send me any file, I'll store it permanently in my channel and give you a link to access it.\n\n⏳ Expiry system active.")


print("🤖 Bot Started!")
app.run()
