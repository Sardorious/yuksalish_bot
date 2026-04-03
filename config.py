import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
_raw_ids = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: list[int] = [int(i.strip()) for i in _raw_ids.split(",") if i.strip().isdigit()]

_raw_super = os.getenv("SUPERUSER_IDS", "")
SUPERUSER_IDS: list[int] = [int(i.strip()) for i in _raw_super.split(",") if i.strip().isdigit()]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
