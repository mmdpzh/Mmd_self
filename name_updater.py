from telethon.tl.functions.account import UpdateProfileRequest
import datetime
import pytz
import asyncio

# --- Your Name ---
NAME = "‍‍"
# --- Timezone ---
TIME_ZONE = "Asia/Tehran"
# --- Time format ---
TIME_FORMAT = "%H:%M"

async def update_name(client):
    """Continuously updates the user's profile name with the current time."""
    print("🕒 Name updater started...")
    while True:
        try:
            time_zone = pytz.timezone(TIME_ZONE)
            current_time = datetime.datetime.now(time_zone).strftime(TIME_FORMAT)

            new_name = f"{NAME} | {current_time}"

            # print(f"Updating name to: {new_name}") # Optional: uncomment for debugging

            await client(UpdateProfileRequest(first_name=new_name))

            # print("Name updated successfully.") # Optional: uncomment for debugging

        except Exception as e:
            print(f"❌ An error occurred in name updater: {e}")

        # Wait for 60 seconds before the next update
        await asyncio.sleep(60)
