import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import admin, student, teacher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    await db.init_db()
    logger.info("Database initialised ✔")

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    # Order matters: student router first so /start is caught before admin
    dp.include_router(student.router)
    dp.include_router(admin.router)
    dp.include_router(teacher.router)

    logger.info("Bot is running…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
