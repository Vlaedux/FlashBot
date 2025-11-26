# handlers/commands_basic.py
from aiogram import F, Router, types
from aiogram.filters import Command
from database.db import get_user_themes, get_cards_by_theme, delete_card, delete_theme
from utils.pagination import paginate_list, build_keyboard_view 

router = Router()


# -------------------------
# /start та /help (Ваші існуючі хендлери залишаються)
# -------------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привіт! Я — FlashBot.\n\n"
        "Моя мета — допомогти тобі вчитись ефективніше.\n"
        "Я можу перетворювати текст лекцій у флеш-картки для самоперевірки.\n\n"
        "🧠 Просто скористайся командою /generate, щоб надіслати текст лекції.\n\n"
        "ℹ️ Щоб дізнатись про всі доступні команди — напиши /help."
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 *Список доступних команд:*\n\n"
        "✅ /start — почати роботу з ботом\n"
        "❓ /ask — поставити будь-яке питання Gemini\n"
        "💡 /generate — створити флеш-картки з тексту лекції\n"
        "🧠 /quiz — розпочати тренування на збережених картках\n"
        "💾 /mycards — переглянути збережені картки\n"
        "ℹ️ /help — показати довідку\n\n",
        parse_mode="Markdown"
    )

# -------------------------
# /mycards (Py Dev 1: вибір теми)
# -------------------------
@router.message(Command("mycards"))
async def cmd_mycards(message: types.Message):
    user_id = message.from_user.id
    themes = get_user_themes(user_id)

    if not themes:
        return await message.answer("📭 У вас поки немає збережених карток.")

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=theme, callback_data=f"view_theme:{theme}:1")]
            for theme in themes
        ]
    )

    await message.answer(
        "📚 *Ваші теми карток*\n\nОберіть тему для перегляду:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# -------------------------
# CALLBACK: Перегляд першої сторінки теми (Py Dev 1)
# -------------------------
@router.callback_query(F.data.startswith("view_theme:"))
async def open_theme_view(callback: types.CallbackQuery):
    _, theme, page = callback.data.split(":")
    page = int(page)
    user_id = callback.from_user.id

    cards = get_cards_by_theme(user_id, theme)
    pages = paginate_list(cards) 
    total_pages = len(pages)

    if total_pages == 0:
        await callback.message.edit_text(f"📘 Тема: *{theme}*\n\nКарток у цій темі немає 😢", parse_mode="Markdown")
        return await callback.answer()

    if page > total_pages:
        page = total_pages
        
    current_card = pages[page-1][0]

    text = f"📘 **Тема:** {theme}\n*Картка {page}/{total_pages}*\n\n" \
           f"❓ **{current_card['question']}**"

    keyboard = build_keyboard_view(page, total_pages, theme, current_card['id'], showing_answer=False)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# -------------------------
# CALLBACK: Пагінація (Гортання) (Py Dev 1)
# -------------------------
@router.callback_query(F.data.startswith("view_page:"))
async def card_pagination(callback: types.CallbackQuery):
    _, theme, page = callback.data.split(":")
    page = int(page)
    user_id = callback.from_user.id

    cards = get_cards_by_theme(user_id, theme)
    pages = paginate_list(cards)
    total_pages = len(pages)

    if page < 1 or page > total_pages:
        return await callback.answer("Сторінка поза межами")

    current_card = pages[page-1][0]

    text = f"📘 **Тема:** {theme}\n*Картка {page}/{total_pages}*\n\n" \
           f"❓ **{current_card['question']}**"

    keyboard = build_keyboard_view(page, total_pages, theme, current_card['id'], showing_answer=False)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# -------------------------
# CALLBACK: Показати відповідь (Py Dev 1)
# -------------------------
@router.callback_query(F.data.startswith("show_answer:"))
async def show_card_answer(callback: types.CallbackQuery):
    _, theme, page = callback.data.split(":")
    page = int(page)
    user_id = callback.from_user.id

    cards = get_cards_by_theme(user_id, theme)
    pages = paginate_list(cards)
    total_pages = len(pages)
    
    current_card = pages[page-1][0]
    
    text = f"📘 **Тема:** {theme}\n*Картка {page}/{total_pages}*\n\n" \
           f"❓ **{current_card['question']}**\n" \
           f"✅ {current_card['answer']}"

    keyboard = build_keyboard_view(page, total_pages, theme, current_card['id'], showing_answer=True)
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# ----------------------------------------
# CALLBACK: Управління (Видалення)
# ----------------------------------------

@router.callback_query(F.data.startswith("delete_card_conf:"))
async def confirm_delete_card_handler(callback: types.CallbackQuery):
    _, card_id_str, theme, page_str = callback.data.split(":")
    card_id = int(card_id_str)
    
    delete_card(card_id) # Викликаємо функцію з db.py

    # Перевіряємо, чи залишилися картки у темі, інакше повертаємося до /mycards
    cards = get_cards_by_theme(callback.from_user.id, theme)

    if not cards:
        await callback.message.edit_text(
            f"✅ Картка видалена. Тема *{theme}* більше не містить карток.", parse_mode="Markdown"
        )
        return await callback.answer("Картку видалено.")

    # Логіка оновлення після видалення
    # Викликаємо функцію пагінації знову, щоб оновити UI
    await callback.answer("Картку видалено. Оновлення сторінки...")
    await card_pagination(callback)
    
# Хендлер для редагування (поки що заглушка)
@router.callback_query(F.data.startswith("edit_card:"))
async def edit_card_start_handler(callback: types.CallbackQuery):
    await callback.answer("✏️ Редагування: Функція буде реалізована у наступних спринтах.")