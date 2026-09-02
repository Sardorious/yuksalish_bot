import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import admin, student, teacher
from keyboards import reminder_keyboard
from tzutil import TIMEZONE_NAME, now

LOG_FILE = os.getenv("LOG_FILE", "bot.log")
os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def reminder_worker(bot: Bot):
    """Background task to send reminders at the configured time."""
    last_sent_minute = None
    while True:
        try:
            now_str = now().strftime("%H:%M")
            if now_str != last_sent_minute:
                due = await db.get_due_reminders(now_str)
                for r in due:
                    try:
                        await bot.send_message(
                            r["user_id"],
                            "⏰ Eslatma: Bugun vazifalar va kitob o'qishni belgilashni unutmang!",
                            reply_markup=reminder_keyboard()
                        )
                    except Exception as e:
                        logger.error(f"Failed to send reminder to {r['user_id']}: {e}")
                last_sent_minute = now_str
            
            # Menedjer minut o'tishini kutmasligi uchun 10 soniya kutish
            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error in reminder_worker: {e}")
            await asyncio.sleep(10)


async def main():
    await db.init_db()
    logger.info("Database initialised ✔")
    logger.info(f"Vaqt mintaqasi: {TIMEZONE_NAME} (hozir {now():%Y-%m-%d %H:%M})")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp  = Dispatcher(storage=MemoryStorage())

    # Order matters: student router first so /start is caught before admin
    dp.include_router(student.router)
    dp.include_router(admin.router)
    dp.include_router(teacher.router)

    # Start notification worker. Havolani saqlaymiz, aks holda task GC
    # tomonidan yig'ib yuborilishi mumkin; `docker stop` (SIGTERM) da esa
    # uni tartibli to'xtatamiz.
    worker = asyncio.create_task(reminder_worker(bot))

    logger.info("Bot is running…")
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass


