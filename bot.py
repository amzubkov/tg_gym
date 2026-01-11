import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from middleware import AccessMiddleware
from handlers import (
    access_router,
    start_router,
    exercises_router,
    tracking_router,
    history_router,
    admin_router,
    custom_router,
    ai_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # Инициализация БД
    await init_db()
    logger.info("Database initialized")

    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware для проверки доступа
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    # Регистрация роутеров (access первый!)
    dp.include_router(access_router)
    dp.include_router(start_router)
    dp.include_router(exercises_router)
    dp.include_router(tracking_router)
    dp.include_router(history_router)
    dp.include_router(admin_router)
    dp.include_router(custom_router)
    dp.include_router(ai_router)

    logger.info("Starting bot...")

    # Запуск
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())