import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from handlers import admin, student, teacher
from keyboards import reminder_keyboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def reminder_worker(bot: Bot):
    """Background task to send reminders at the configured time."""
    while True:
        try:
            now_str = datetime.now().strftime("%H:%M")
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
            
            # Wait 60 seconds before next check
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in reminder_worker: {e}")
            await asyncio.sleep(60)


async def main():
    await db.init_db()
    logger.info("Database initialised ✔")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp  = Dispatcher(storage=MemoryStorage())

    # Order matters: student router first so /start is caught before admin
    dp.include_router(student.router)
    dp.include_router(admin.router)
    dp.include_router(teacher.router)

    # Start notification worker
    asyncio.create_task(reminder_worker(bot))

    logger.info("Bot is running…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


