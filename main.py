import asyncio
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from name_updater import update_name

# ================== تنظیمات ==================
# Load environment variables
api_id_env = os.getenv("API_ID")
api_id = int(api_id_env) if api_id_env and api_id_env.isdigit() else None
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")
owner_id_env = os.getenv("OWNER_ID")
OWNER_ID = int(owner_id_env) if owner_id_env and owner_id_env.isdigit() else None


# Initialize the client as None initially
client = None
if all([api_id, api_hash, session_string]):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
else:
    # Print an error message if variables are missing and exit
    missing_vars = []
    if not api_id: missing_vars.append("API_ID")
    if not api_hash: missing_vars.append("API_HASH")
    if not session_string: missing_vars.append("SESSION_STRING")
    print(f"❌ Error: The following environment variables are missing or invalid: {', '.join(missing_vars)}")
    exit()

if not OWNER_ID:
    print("⚠️  Warning: OWNER_ID environment variable not set. The bot will respond to everyone.")

# ================== Keep-alive Web Server ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "Auto-sender and Name-updater bot is running!"

# ================== دیتای کاربر ==================
# ذخیره موقت عکس، متن، گروه‌ها، زمان و تسک ارسال برای هر کاربر
user_data = {}

# ================== تعامل با کاربر (ربات ارسال‌کننده) ==================
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    # Only allow the owner to use the bot
    if OWNER_ID and event.sender_id != OWNER_ID:
        return
    user_id = event.sender_id

    # Stop any existing task before starting a new one
    if user_id in user_data and 'task' in user_data[user_id]:
        user_data[user_id]['task'].cancel()

    user_data[user_id] = {}
    await event.respond("سلام! 👋\nربات ارسال‌کننده و آپدیت‌کننده‌ی نام آماده است.\nبرای تنظیم ارسال خودکار، لطفا عکس مورد نظر را ارسال کنید.\nبرای توقف، از دستور /stop استفاده کنید.")

@client.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    # Only allow the owner to use the bot
    if OWNER_ID and event.sender_id != OWNER_ID:
        return

    user_id = event.sender_id
    if user_id in user_data and 'task' in user_data[user_id] and not user_data[user_id]['task'].done():
        user_data[user_id]['task'].cancel()
        # Clean up user data
        if user_id in user_data:
            del user_data[user_id]
        await event.respond("ارسال خودکار متوقف شد. ✅")
    else:
        await event.respond("هیچ فرآیند ارسال خودکاری برای متوقف کردن وجود ندارد.")


@client.on(events.NewMessage)
async def handle_messages(event):
    # Ignore commands
    if event.text and event.text.startswith('/'):
        return

    # Only allow the owner to use the bot
    if OWNER_ID and event.sender_id != OWNER_ID:
        return

    user_id = event.sender_id
    # Ensure user has started the conversation
    if user_id not in user_data:
        # Don't interfere with other bots or unexpected messages
        return

    # Do not process if a task is already running
    if 'task' in user_data[user_id] and not user_data[user_id]['task'].done():
        return

    data = user_data[user_id]

    # Ignore text messages if a photo is expected first
    if 'photo' not in data and not event.photo:
        return

    # مرحله دریافت عکس
    if 'photo' not in data and event.photo:
        data['photo'] = await event.download_media()
