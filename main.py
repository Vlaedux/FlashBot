import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

from handlers import commands_basic, commands_ai, commands_quiz, commands_ask
from database.db import init_db

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Ініціалізація БД
    init_db()

    dp.include_router(commands_basic.router)
    dp.include_router(commands_ai.router)
    dp.include_router(commands_quiz.router)
    dp.include_router(commands_ask.router)


    print("🤖 FlashBot запущено!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

