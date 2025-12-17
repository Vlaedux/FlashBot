# handlers/commands_basic.py
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database.db import get_user_themes, get_cards_by_theme, delete_card, delete_theme
from utils.pagination import paginate_list, build_keyboard_view 

router = Router()

# --- ГОЛОВНЕ МЕНЮ (Дев 2) ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💡 Створити картки"), KeyboardButton(text="🧠 Тренування")],
        [KeyboardButton(text="💾 Мої картки"), KeyboardButton(text="❓ Запитати")]
    ],
    resize_keyboard=True
)

# -------------------------
# /start та /help (Збережено твій текст)
# -------------------------
@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привіт! Я — FlashBot.\n\n"
        "Моя мета — допомогти тобі вчитись ефективніше.\n"
        "Я можу перетворювати текст лекцій у флеш-картки для самоперевірки.\n\n"
        "🧠 Просто скористайся командою /generate або кнопками нижче 👇",
        reply_markup=main_menu
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

# Додана обробка текстових кнопок меню
@router.message(F.text == "💾 Мої картки")
async def btn_mycards_text(message: types.Message):
    await cmd_mycards(message)

# -------------------------
# /mycards (Py Dev 1: вибір теми)
# Додана функція видалення тем (Дев 3)
# -------------------------
@router.message(Command("mycards"))
async def cmd_mycards(message: types.Message):
    user_id = message.from_user.id
    themes = get_user_themes(user_id)

    if not themes:
        return await message.answer("📭 У вас поки немає збережених карток.")

    # Оновлена клавіатура: Перегляд + Видалення теми
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text=f"📖 {theme}", callback_data=f"view_theme:{theme}:1"),
                types.InlineKeyboardButton(text="🗑 Видалити тему", callback_data=f"conf_del_theme:{theme}")
            ] for theme in themes
        ]
    )

    await message.answer(
        "📚 *Ваші теми карток*\n\nОберіть тему для перегляду або видалення:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# Хендлер видалення всієї теми (Дев 3)
@router.callback_query(F.data.startswith("conf_del_theme:"))
async def confirm_delete_theme_handler(callback: types.CallbackQuery):
    theme = callback.data.split(":")[1]
    delete_theme(callback.from_user.id, theme)
    await callback.message.edit_text(f"✅ Тему *{theme}* та всі її картки успішно видалено.", parse_mode="Markdown")
    await callback.answer()

# -------------------------
# CALLBACK: Твій оригінальний код пагінації залишається БЕЗ ЗМІН
# -------------------------
@router.callback_query(F.data.startswith("view_theme:"))
async def open_theme_view(callback: types.CallbackQuery):
    # Виправлено розпаковку для уникнення ValueError
    parts = callback.data.split(":")
    theme, page = parts[1], int(parts[2])
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

@router.callback_query(F.data.startswith("view_page:"))
async def card_pagination(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    theme, page = parts[1], int(parts[2])
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

@router.callback_query(F.data.startswith("show_answer:"))
async def show_card_answer(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    theme, page = parts[1], int(parts[2])
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

@router.callback_query(F.data.startswith("delete_card_conf:"))
async def confirm_delete_card_handler(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    card_id = int(parts[1])
    theme = parts[2]
    
    delete_card(card_id)

    cards = get_cards_by_theme(callback.from_user.id, theme)

    if not cards:
        await callback.message.edit_text(
            f"✅ Картка видалена. Тема *{theme}* більше не містить карток.", parse_mode="Markdown"
        )
        return await callback.answer("Картку видалено.")

    await callback.answer("Картку видалено. Оновлення сторінки...")
    await card_pagination(callback)
    
@router.callback_query(F.data.startswith("edit_card:"))
async def edit_card_start_handler(callback: types.CallbackQuery):
    await callback.answer("✏️ Редагування: Функція буде реалізована у наступних спринтах.")