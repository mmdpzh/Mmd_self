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
        await event.respond("عکس دریافت شد ✅\nحالا متن پیام مورد نظر را وارد کنید.")
        return

    # مرحله دریافت متن
    if 'photo' in data and 'text' not in data:
        data['text'] = event.text
        await event.respond("متن دریافت شد ✅\nلطفا آیدی یا یوزرنیم گروه‌ها را وارد کنید (با فاصله جدا کنید):")
        return

    # مرحله دریافت گروه‌ها
    if 'text' in data and 'groups' not in data:
        data['groups'] = event.text.split()
        await event.respond("گروه‌ها دریافت شد ✅\nلطفا زمان بین ارسال‌ها را به دقیقه وارد کنید:")
        return

    # مرحله دریافت زمان ارسال خودکار
    if 'groups' in data and 'interval' not in data:
        try:
            data['interval'] = int(event.text)
            await event.respond(f"تنظیم شد ✅\nاز حالا هر {data['interval']} دقیقه یکبار، عکس و متن شما به گروه‌ها ارسال خواهد شد.")
            # Create and store the task
            task = asyncio.create_task(auto_send(user_id))
            user_data[user_id]['task'] = task
        except ValueError:
            await event.respond("لطفا فقط یک عدد معتبر وارد کنید.")

# ================== ارسال خودکار ==================
async def auto_send(user_id):
    if user_id not in user_data:
        return

    data = user_data[user_id]
    photo_path = data.get('photo')
    text = data.get('text', '')
    groups = data.get('groups', [])
    interval_minutes = data.get('interval')

    if not all([photo_path, groups, interval_minutes]):
        print(f"❌ User {user_id} has incomplete data for auto-sending.")
        return

    print(f"🚀 Starting auto-sender for user {user_id} every {interval_minutes} minutes.")
    try:
        while True:
            for group in groups:
                try:
                    await client.send_file(group, photo_path, caption=text)
                    print(f"✅ Message sent to {group} for user {user_id}")
                except Exception as e:
                    print(f"❌ Error sending to {group} for user {user_id}: {e}")
            await asyncio.sleep(interval_minutes * 60)
    except asyncio.CancelledError:
        print(f"🛑 Auto-sender for user {user_id} was cancelled.")
    finally:
        # Clean up the downloaded photo if it exists
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
            print(f"🗑️ Cleaned up media for user {user_id}.")


# ================== اجرای کلاینت ==================
async def main_runner():
    await client.start()
    print("🤖 Bot is ready and listening...")

    # Start the name updater as a background task
    asyncio.create_task(update_name(client))

    # Run the client until disconnected (handles incoming messages)
    await client.run_until_disconnected()

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_runner())

if __name__ == "__main__":
    # Run the bot in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Run the Flask app in the main thread
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
