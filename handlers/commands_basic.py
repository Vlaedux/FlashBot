# handlers/commands_basic.py
from aiogram import F, Router, types
from aiogram.filters import Command
from database.db import get_user_themes, get_cards_by_theme

router = Router()


# -------------------------
# /start
# -------------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Привітальне повідомлення, яке зʼявляється при запуску бота.
    """
    await message.answer(
        "👋 Привіт! Я — FlashBot.\n\n"
        "Моя мета — допомогти тобі вчитись ефективніше.\n"
        "Я можу перетворювати текст лекцій у флеш-картки для самоперевірки.\n\n"
        "🧠 Просто скористайся командою /generate, щоб надіслати текст лекції.\n\n"
        "ℹ️ Щоб дізнатись про всі доступні команди — напиши /help."
    )


# -------------------------
# /help
# -------------------------
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Відповідь на команду /help — короткий опис усіх можливостей.
    """
    await message.answer(
        "📚 *Список доступних команд:*\n\n"
        "✅ /start — почати роботу з ботом\n"
        "❓ /ask — поставити будь-яке питання Gemini\n"
        "💡 /generate — створити флеш-картки з тексту лекції\n"
        "💾 /mycards — переглянути збережені картки\n"
        "ℹ️ /help — показати довідку\n\n",
        parse_mode="Markdown"
    )


# -------------------------
# /mycards
# -------------------------
@router.message(Command("mycards"))
async def cmd_mycards(message: types.Message):
    user_id = message.from_user.id

    themes = get_user_themes(user_id)

    if not themes:
        return await message.answer("📭 У вас поки немає збережених карток.")

    # Створюємо кнопки тем
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=theme, callback_data=f"theme:{theme}")]
            for theme in themes
        ]
    )

    await message.answer(
        "📚 *Ваші теми карток*\n\nОберіть тему:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# --- CALLBACK: користувач обрав тему ---
@router.callback_query(F.data.startswith("theme:"))
async def show_cards_by_theme(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    theme = callback.data.split("theme:")[1]

    cards = get_cards_by_theme(user_id, theme)

    if not cards:
        return await callback.answer("У цій темі нема карток.")

    # Формуємо нумерований список карток
    text_list = "\n\n".join([
        f"*{i}.*\n❓ *{c['question']}*\n✅ {c['answer']}"
        for i, c in enumerate(cards, 1)
    ])


    await callback.message.answer(
        f"📘 *Тема:* {theme}\n"
        f"Знайдено карток: {len(cards)}\n\n"
        f"{text_list}",
        parse_mode="Markdown"
    )

    await callback.answer()
