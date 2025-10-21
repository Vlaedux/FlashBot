import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

# Імпорт хендлерів
from handlers import commands_basic, commands_ai, commands_extra

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Реєстрація хендлерів
    dp.include_router(commands_basic.router)
    dp.include_router(commands_ai.router)
    dp.include_router(commands_extra.router)

    print("🤖 FlashBot запущено. Готовий до команд.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
