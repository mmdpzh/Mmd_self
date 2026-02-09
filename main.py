# =======================
# main.py - نسخه نهایی سلف‌بات
# =======================
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
from flask import Flask
import threading
import os
import yt_dlp
import glob
import re
import sys
import random

# =======================
# تنظیمات Telethon و اعتبارسنجی
# =======================
api_id = os.environ.get("API_ID")
api_hash = os.environ.get("API_HASH")
session_string = os.environ.get("SESSION")

# اعتبارسنجی متغیرهای محیطی
if not api_id or not api_hash or not session_string:
    print("خطا: لطفاً متغیرهای محیطی API_ID, API_HASH, و SESSION را به درستی تنظیم کنید.")
    sys.exit(1)

try:
    api_id = int(api_id)
except ValueError:
    print("خطا: API_ID باید یک عدد صحیح باشد.")
    sys.exit(1)

client = TelegramClient(StringSession(session_string), api_id, api_hash)

# =======================
# Flask برای زنده نگه داشتن Render
# =======================
app = Flask("")

@app.route("/")
def home():
    return "سلف‌بات فعال است ✅"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

threading.Thread(target=run_flask).start()

# =======================
# توابع کمکی دستور alo
# =======================
def read_dialog_from_file(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]
    return [ln for ln in lines if ln.strip() != ""]

def render_lines(lines, target_name):
    return [ln.format(target_name=target_name) for ln in lines]

# =======================
# تنظیمات دستور alo
# =======================
DIALOG_FILE = "dialog.txt"
DELAY_SECONDS = 0.3

# =======================
# دستورات ساده
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.ping"))
async def ping(event):
    await event.edit("Pong!")

@client.on(events.NewMessage(outgoing=True, pattern=r"\.hello"))
async def hello(event):
    await event.edit("Hello!")

# =======================
# دستور Alo
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.alo(?: (.+))?"))
async def alo_handler(event):
    target_name = event.pattern_match.group(1)
    if not target_name:
        await event.edit("❌ لطفاً اسم را بعد از دستور وارد کن: `.alo <target_name>`")
        return

    lines = read_dialog_from_file(DIALOG_FILE)
    if not lines:
        await event.edit(f"❌ فایل `{DIALOG_FILE}` پیدا نشد یا خالی است.")
        return

    # Delete the command message before sending the dialog
    await event.delete()

    to_send = render_lines(lines, target_name.strip())

    # Start sending the dialog messages
    for line in to_send:
        await client.send_message(event.chat_id, line)
        await asyncio.sleep(DELAY_SECONDS)

# =======================
# دستور Download
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.download(?: (mp3|mp4))? (.*)"))
async def download_media(event):
    await event.edit("📥 در حال دانلود...")

    # Parse arguments
    args = event.pattern_match.groups()
    format_pref = args[0] if args[0] else "mp4"
    url = args[1]

    output_template = "downloads/%(title)s.%(ext)s"

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if format_pref == 'mp4' else 'bestaudio/best',
        'outtmpl': output_template,
        'writethumbnail': True,
        'nopostoverwrites': True,
        'cookiefile': 'cookies_youtube.txt' if 'youtube.com' in url or 'youtu.be' in url else ('cookies_instagram.txt' if 'instagram.com' in url else None),
        'postprocessors': [],
    }

    if format_pref == 'mp4':
        ydl_opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})
    elif format_pref == 'mp3':
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })
        ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})

    # Create downloads directory if it doesn't exist
    if not os.path.isdir('downloads'):
        os.makedirs('downloads')

    downloaded_file = ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)

            base_filename = os.path.splitext(downloaded_file)[0]

            if format_pref == 'mp3':
                final_file = base_filename + '.mp3'
            else:
                final_file = base_filename + '.mp4'

        if not os.path.exists(final_file):
             await event.edit(f"❌ فایل دانلود شده پیدا نشد: `{final_file}`")
             # Cleanup failed download
             base_filename_no_ext = os.path.splitext(downloaded_file)[0]
             for f in glob.glob(base_filename_no_ext + '.*'):
                 os.remove(f)
             return

        await event.edit("📤 در حال آپلود...")

        thumbnail_path = base_filename + '.webp'
        if not os.path.exists(thumbnail_path):
             thumbnail_path = base_filename + '.jpg'
        if not os.path.exists(thumbnail_path):
            thumbnail_path = None

        await client.send_file(
            event.chat_id,
            file=final_file,
            thumb=thumbnail_path,
            caption=info.get('title', 'Downloaded Media'),
            reply_to=event.message.id
        )
        await event.delete()

    except Exception as e:
        error_message = str(e)
        await event.edit(f"❌ خطا در دانلود: {error_message}")

    finally:
        # Cleanup successful download
        if downloaded_file:
            base_filename_no_ext = os.path.splitext(downloaded_file)[0]
            for f in glob.glob(base_filename_no_ext + '.*'):
                os.remove(f)

# =======================
# متغیرهای دستورات
# =======================
bold_active = False
autospam_active = False
autospam_tasks = []

# متغیرهای مربوط به Enemy
enemy_id = None
enemy_active = False
enemy_responses = [
    "پیام نده ماد،ر ج،نده",
    "حر.وم زاد.ه پیام نده",
    "ز.نا زا.ده ما.درتو گا.ییدم",
    "خا.هرتو گا.ییدم",
    "کی.ر تو اول تا آخرت ",
    "کی.رم تو ک.ص نن.ت",
    "ب.ی نا.موس ماد.ر جن.ده",
    "خا.هر ما.درتو گایی.دم",
    "ک.ص ما.درت",
    "ک.ص خاه.رت",
]

# =======================
# دستور Bold
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.bold on"))
async def bold_on(event):
    global bold_active
    bold_active = True
    await event.edit("✅ بولد خودکار فعال شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r"\.bold off"))
async def bold_off(event):
    global bold_active
    bold_active = False
    await event.edit("🛑 بولد خودکار غیرفعال شد.")

# Handler to apply bold to non-command messages
@client.on(events.NewMessage(outgoing=True))
async def handle_bold_text(event):
    # Avoid applying bold to commands or empty messages
    if bold_active and event.text and not event.text.startswith('.'):
        # Add a small delay to ensure the command message is processed first
        await asyncio.sleep(0.1)
        await event.edit(f"**{event.text}**")

# =======================
# دستور Autospam
# =======================
# Note: The start handler uses a negative lookahead to avoid matching ".autospam off"
@client.on(events.NewMessage(outgoing=True, pattern=r"\.autospam(?! off)"))
async def start_autospam(event):
    global autospam_active, autospam_tasks
    if autospam_active:
        await event.edit("⚠️ ارسال خودکار قبلا فعال شده است.")
        return

    lines = event.raw_text.split("\n")[1:]
    if not lines:
        await event.edit("❌ لطفاً گروه‌ها و پیام‌ها را وارد کنید.")
        return

    try:
        # Check if the first line is the interval
        interval_line = lines[0].strip()
        interval = int(interval_line)
        content_lines = lines[1:]
    except (ValueError, IndexError):
        # Default interval if not specified or first line is not a number
        interval = 300
        content_lines = lines

    pairs = []
    for line in content_lines:
        if not line.strip():
            continue
        parts = line.strip().split(" ", 1)
        if len(parts) == 2:
            group, msg = parts
            pairs.append((group.strip(), msg.strip()))

    if not pairs:
        await event.edit("❌ فرمت دستور اشتباه است. مثال درست:\n.autospam 300\n@Group1 پیام اول\n@Group2 پیام دوم")
        return

    autospam_active = True
    await event.edit(f"✅ ارسال خودکار فعال شد. فاصله ارسال: {interval} ثانیه.")

    async def send_loop():
        while autospam_active:
            for group, msg in pairs:
                try:
                    await client.send_message(group, msg)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"❌ خطا در ارسال به {group}: {e}")
            await asyncio.sleep(interval)

    task = asyncio.create_task(send_loop())
    autospam_tasks.append(task)

@client.on(events.NewMessage(outgoing=True, pattern=r"\.autospam off"))
async def stop_autospam(event):
    global autospam_active, autospam_tasks
    if not autospam_active:
        await event.edit("⚠️ ارسال خودکار فعال نیست.")
        return

    autospam_active = False
    for task in autospam_tasks:
        task.cancel()
    autospam_tasks.clear()
    await event.edit("🛑 ارسال خودکار متوقف شد.")

# =======================
# دستور Enemy
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.enemy"))
async def enemy_handler(event):
    global enemy_id, enemy_active

    # .enemy off command
    if event.raw_text.strip() == ".enemy off":
        enemy_active = False
        enemy_id = None
        await event.edit("❌ سیستم enemy متوقف شد. دیگه ریپلای نمیزنم.")
        return

    # Must be a reply to a message
    if not event.is_reply:
        await event.edit("⚠️ برای فعال کردن enemy، باید روی پیام یک نفر ریپلای کنی.")
        return

    reply_msg = await event.get_reply_message()
    enemy_id = reply_msg.from_id.user_id
    enemy_active = True
    await event.edit(f"🎯 Enemy فعال شد برای کاربر: `{enemy_id}`")

# Handler for replying to the enemy
@client.on(events.NewMessage(incoming=True))
async def reply_to_enemy(event):
    if not enemy_active or not (event.is_private or event.is_group):
        return

    # Check if the message is from the enemy
    if enemy_id and event.message.from_id and event.message.from_id.user_id == enemy_id:
        # Choose a random response and reply
        response = random.choice(enemy_responses)
        await event.reply(response)


# =======================
# دستور Help
# =======================
@client.on(events.NewMessage(outgoing=True, pattern=r"\.help"))
async def send_help(event):
    help_text = """
✨🚀 **راهنمای دستورات سلف‌بات YASIN** 🚀✨

╭─🌐 **دستورات عمومی**
│ • `.ping` » بررسی آنلاین بودن ربات
│ • `.hello` » سلام کردن
│ • `.alo <نام>` » ارسال دیالوگ از `dialog.txt`
╰───────────────

╭─🎵 **دانلود مدیا**
│ • `.download mp4 <url>` » دانلود ویدیو
│ • `.download mp3 <url>` » دانلود صوت
│ *در صورت عدم تعیین فرمت، mp4 دانلود می‌شود*
╰───────────────

╭─🖋 **بولد خودکار**
│ • `.bold on` » فعال کردن بولد خودکار
│ • `.bold off` » غیرفعال کردن بولد خودکار
╰───────────────

╭─📤 **ارسال خودکار پیام**
│ • `.autospam` » فعال کردن ارسال خودکار
│ • `.autospam off` » متوقف کردن ارسال خودکار
│
│ 🔹 مثال:
│ `.autospam 300`
│ `@Group1 پیام شما برای گروه اول`
│ `@channel2 پیام شما برای کانال دوم`
│ *عدد 300 فاصله زمانی بین هر ارسال به ثانیه است (پیش‌فرض: ۳۰۰ ثانیه).*
╰───────────────

╭─😡 **سیستم دشمن**
│ • `.enemy` » (با ریپلای) فعال کردن دشمن
│ • `.enemy off` » غیرفعال کردن دشمن
╰───────────────

💡 **نکته:** برای بهترین تجربه، فاصله‌گذاری‌ها و بولدها را حفظ کنید تا متن حس مدرن و شفاف بده.
"""
    await event.edit(help_text)

# =======================
# اجرای Client
# =======================
print("سلف‌بات شروع به کار کرد ✅")
client.start()
client.run_until_disconnected()
