import asyncio
import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from name_updater import update_name

# ================== Bold Writer (FA + EN) ==================
BOLD_MAP = {
    # English lowercase
    "a":"𝗮","b":"𝗯","c":"𝗰","d":"𝗱","e":"𝗲","f":"𝗳","g":"𝗴","h":"𝗵","i":"𝗶","j":"𝗷",
    "k":"𝗸","l":"𝗹","m":"𝗺","n":"𝗻","o":"𝗼","p":"𝗽","q":"𝗾","r":"𝗿","s":"𝗼","t":"𝗿",
    "u":"𝘂","v":"𝘃","w":"𝘄","x":"𝘅","y":"𝘆","z":"𝘇",

    # English uppercase
    "A":"𝗔","B":"𝗕","C":"𝗖","D":"𝗗","E":"𝗘","F":"𝗙","G":"𝗚","H":"𝗛","I":"𝗜","J":"𝗝",
    "K":"𝗞","L":"𝗟","M":"𝗠","N":"𝗡","O":"𝗢","P":"𝗣","Q":"𝗤","R":"𝗥","S":"𝗦","T":"𝗧",
    "U":"𝗨","V":"𝗩","W":"𝗪","X":"𝗫","Y":"𝗬","Z":"𝗭",

    # Numbers
    "0":"𝟬","1":"𝟭","2":"𝟮","3":"𝟯","4":"𝟰",
    "5":"𝟱","6":"𝟲","7":"𝟳","8":"𝟴","9":"𝟵"
}

def bold_text(text: str) -> str:
    return "".join(BOLD_MAP.get(ch, ch) for ch in text)

# ================== تنظیمات ==================
api_id_env = os.getenv("API_ID")
api_id = int(api_id_env) if api_id_env and api_id_env.isdigit() else None
api_hash = os.getenv("API_HASH")
session_string = os.getenv("SESSION_STRING")
owner_id_env = os.getenv("OWNER_ID")
OWNER_ID = int(owner_id_env) if owner_id_env and owner_id_env.isdigit() else None

client = None
if all([api_id, api_hash, session_string]):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
else:
    missing_vars = []
    if not api_id: missing_vars.append("API_ID")
    if not api_hash: missing_vars.append("API_HASH")
    if not session_string: missing_vars.append("SESSION_STRING")
    print(f"❌ Error: The following environment variables are missing or invalid: {', '.join(missing_vars)}")
    exit()

if not OWNER_ID:
    print("⚠️ Warning: OWNER_ID environment variable not set. The bot will respond to everyone.")

# ================== Keep-alive Web Server ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "Auto-sender and Name-updater bot is running!"

# ================== دیتای کاربر ==================
user_data = {}

# ================== تعامل با کاربر ==================
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if OWNER_ID and event.sender_id != OWNER_ID:
        return

    user_id = event.sender_id

    if user_id in user_data and 'task' in user_data[user_id]:
        user_data[user_id]['task'].cancel()

    user_data[user_id] = {'bold': True}  # پیش‌فرض بولد روشن
    await event.respond(
        "سلام! 👋\n"
        "ربات ارسال‌کننده و آپدیت‌کننده‌ی نام آماده است.\n"
        "برای تنظیم ارسال خودکار، لطفا عکس مورد نظر را ارسال کنید.\n"
        "برای توقف، از دستور /stop استفاده کنید.\n"
        "برای روشن یا خاموش کردن بولد، از دستور .bold on یا .bold off استفاده کنید."
    )

@client.on(events.NewMessage(pattern='/stop'))
async def stop(event):
    if OWNER_ID and event.sender_id != OWNER_ID:
        return

    user_id = event.sender_id
    if user_id in user_data and 'task' in user_data[user_id] and not user_data[user_id]['task'].done():
        user_data[user_id]['task'].cancel()
        del user_data[user_id]
        await event.respond("ارسال خودکار متوقف شد. ✅")
    else:
        await event.respond("هیچ فرآیند ارسال خودکاری برای متوقف کردن وجود ندارد.")

@client.on(events.NewMessage)
async def handle_messages(event):
    if event.text and event.text.startswith('/'):
        return

    if OWNER_ID and event.sender_id != OWNER_ID:
        return

    user_id = event.sender_id
    if user_id not in user_data:
        user_data[user_id] = {'bold': True}  # اگر کاربر جدیده، پیش‌فرض بولد روشن

    # ================== کنترل بولد ==================
    if event.text == ".bold on":
        user_data[user_id]['bold'] = True
        await event.respond("بولد فعال شد ✅")
        return

    if event.text == ".bold off":
        user_data[user_id]['bold'] = False
        await event.respond("بولد غیرفعال شد ✅")
        return

    if 'task' in user_data[user_id] and not user_data[user_id]['task'].done():
        return

    data = user_data[user_id]

    if 'photo' not in data and not event.photo:
        return

    if 'photo' not in data and event.photo:
        data['photo'] = await event.download_media()
        await event.respond("عکس دریافت شد ✅\nحالا متن پیام مورد نظر را وارد کنید.")
        return

    if 'photo' in data and 'text' not in data:
        if user_data[user_id].get('bold', True):
            data['text'] = bold_text(event.text)
        else:
            data['text'] = event.text
        await event.respond("متن دریافت شد ✅\nلطفا آیدی یا یوزرنیم گروه‌ها را وارد کنید (با فاصله جدا کنید):")
        return

    if 'text' in data and 'groups' not in data:
        data['groups'] = event.text.split()
        await event.respond("گروه‌ها دریافت شد ✅\nلطفا زمان بین ارسال‌ها را به دقیقه وارد کنید:")
        return

    if 'groups' in data and 'interval' not in data:
        try:
            data['interval'] = int(event.text)
            await event.respond(
                f"تنظیم شد ✅\n"
                f"از حالا هر {data['interval']} دقیقه یکبار، پیام شما ارسال خواهد شد."
            )
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
        return

    try:
        while True:
            for group in groups:
                try:
                    await client.send_file(group, photo_path, caption=text)
                except Exception as e:
                    print(f"❌ Error sending to {group}: {e}")
            await asyncio.sleep(interval_minutes * 60)
    except asyncio.CancelledError:
        pass
    finally:
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)

# ================== اجرای کلاینت ==================
async def main_runner():
    await client.start()
    print("🤖 Bot is ready and listening...")

    asyncio.create_task(update_name(client))
    await client.run_until_disconnected()

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_runner())

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
