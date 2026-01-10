import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ACCESS_CODE = os.getenv("ACCESS_CODE", "gym2024")
DATABASE_PATH = "gym_bot.db"