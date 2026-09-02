"""Markazlashgan vaqt mintaqasi yordamchilari.

Bot serveri UTC da ishlashi mumkin, foydalanuvchilar esa Toshkent vaqtida.
Shu sababli `date.today()` / `datetime.now()` o'rniga hamma joyda shu
moduldagi `today()` va `now()` ishlatiladi.

Mintaqani .env dagi TIMEZONE o'zgaruvchisi orqali o'zgartirish mumkin.
"""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TIMEZONE_NAME: str = os.getenv("TIMEZONE", "Asia/Tashkent")

try:
    TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except Exception:  # noqa: BLE001 - noto'g'ri nom berilsa ham bot ishga tushsin
    TIMEZONE_NAME = "Asia/Tashkent"
    TIMEZONE = ZoneInfo(TIMEZONE_NAME)


def now() -> datetime:
    """Sozlangan mintaqadagi hozirgi vaqt."""
    return datetime.now(TIMEZONE)


def today() -> date:
    """Sozlangan mintaqadagi bugungi sana."""
    return now().date()
