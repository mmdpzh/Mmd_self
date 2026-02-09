from telethon.tl.functions.account import UpdateProfileRequest
import datetime
import pytz
import asyncio

# --- Your Name ---
NAME = "𝒎𝒂𝒎𝒂𝒅"

# --- Invisible separator ---
ZW = "\u200b"  # zero-width space

# --- Timezone ---
TIME_ZONE = "Asia/Tehran"

# --- Time format ---
TIME_FORMAT = "%H:%M"

# --- Small number map ---
SMALL_NUMS = {
    "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
    "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
    ":": "ː"
}

def small_time(time_str):
    return "".join(SMALL_NUMS.get(ch, ch) for ch in time_str)

async def update_name(client):
    print("🕒 Name updater started...")
    while True:
        try:
            tz = pytz.timezone(TIME_ZONE)
            current_time = datetime.datetime.now(tz).strftime(TIME_FORMAT)
            tiny_time = small_time(current_time)

            new_name = f"{NAME}{ZW}{tiny_time}"

            await client(UpdateProfileRequest(first_name=new_name))

        except Exception as e:
            print(f"❌ Error: {e}")

        await asyncio.sleep(60)
