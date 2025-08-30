# 📂 Telegram File Store Bot

A Telegram bot to save & share files with expiry system.  
Deployed easily on **Render**.

## 🚀 Features
- File saving with expiry (default 24h, user can set custom expiry).
- Auto delete expired files.
- No forward option (protect content).
- Admin Panel (/stats, /users, /files).
- Broadcast message to all users.

## ⚙️ Deploy on Render
1. Fork/Clone this repo.
2. Connect repo on [Render](https://render.com).
3. Create a **Worker Service**.
4. Add Environment Variables:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `MONGO_URL`
   - `ADMIN_ID`
5. Build Command:

6. pip install -r requirements.txt

6. Start Command:

python bot.py

Bot will start automatically 🚀
