import random
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# Твої оригінальні імпорти
from database.db import get_user_themes, get_cards_by_theme, save_training_result 
from ai.gemini_api import check_answer_gemini

router = Router()

# --- СТАНИ ---
class QuizState(StatesGroup):
    waiting_for_answer = State()       # Твій стан
    waiting_for_test_answer = State()  # Стан для кнопок

# ------------------------------------
# 1. КОМАНДА /quiz (Твій оригінальний старт)
# ------------------------------------
@router.message(F.text == "🧠 Тренування")
@router.message(Command("quiz"))
async def quiz_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    themes = get_user_themes(user_id) 

    if not themes:
        return await message.answer("У вас немає збережених карток. Скористайтеся /generate.")

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=theme, callback_data=f"pre_quiz:{theme}")] 
        for theme in themes
    ])

    await message.answer("🧠 **Оберіть тему** для проходження квізу:", reply_markup=keyboard, parse_mode="Markdown")

# ------------------------------------
# 2. ВИБІР РЕЖИМУ (Інтеграція від Дева 2)
# ------------------------------------
@router.callback_query(F.data.startswith("pre_quiz:"))
async def select_quiz_mode(callback: types.CallbackQuery):
    theme = callback.data.split(":")[1]
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Тест (Кнопки)", callback_data=f"start_test:{theme}")],
        [types.InlineKeyboardButton(text="🗣 Самоперевірка (Текст)", callback_data=f"start_classic:{theme}")]
    ])
    
    await callback.message.edit_text(
        f"Тема: *{theme}*\nЯк хочете тренуватись?", 
        reply_markup=keyboard, 
        parse_mode="Markdown"
    )

# ====================================
# РЕЖИМ 1: ТЕСТ (КНОПКИ)
# ====================================

@router.callback_query(F.data.startswith("start_test:"))
async def start_test_mode(callback: types.CallbackQuery, state: FSMContext):
    theme = callback.data.split(":")[1]
    cards = get_cards_by_theme(callback.from_user.id, theme)
    
    # Фільтруємо картки: беремо тільки ті, де є варіанти (options)
    valid_cards = [c for c in cards if c.get('options') and len(c['options']) > 0]
    
    if not valid_cards:
        await callback.answer("У цій темі немає тестів (старі картки). Спробуйте 'Самоперевірка'.", show_alert=True)
        return

    await state.update_data(cards=valid_cards, current_index=0, score=0, theme=theme, total_cards=len(valid_cards))
    await send_test_question(callback.message, state)

async def send_test_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    idx = data['current_index']
    cards = data['cards']
    
    if idx >= len(cards):
        return await finish_quiz_session(message, state)

    card = cards[idx]
    
    # Формуємо варіанти: правильний + неправильні
    options = card['options'][:3] + [card['answer']]
    random.shuffle(options)
    
    buttons = []
    for opt in options:
        is_correct = "1" if opt == card['answer'] else "0"
        btn_text = (opt[:30] + '..') if len(opt) > 30 else opt
        buttons.append([types.InlineKeyboardButton(text=btn_text, callback_data=f"ans:{is_correct}")])
    
    buttons.append([types.InlineKeyboardButton(text="🏁 Завершити", callback_data="finish_quiz")])
    
    await message.edit_text(
        f"❓ *Питання {idx+1}/{len(cards)}*\n\n{card['question']}", 
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown"
    )
    await state.set_state(QuizState.waiting_for_test_answer)

@router.callback_query(F.data.startswith("ans:"), QuizState.waiting_for_test_answer)
async def process_test_answer(cb: types.CallbackQuery, state: FSMContext):
    is_correct = cb.data.split(":")[1] == "1"
    data = await state.get_data()
    
    if is_correct:
        await state.update_data(score=data['score'] + 1)
        await cb.answer("✅ Правильно!")
    else:
        correct = data['cards'][data['current_index']]['answer']
        await cb.answer(f"❌ Помилка! Правильно: {correct}", show_alert=True)
    
    await state.update_data(current_index=data['current_index'] + 1)
    await send_test_question(cb.message, state)

# ====================================
# РЕЖИМ 2: САМОПЕРЕВІРКА (Твій оригінальний код)
# ====================================

@router.callback_query(F.data.startswith("start_classic:"))
async def start_classic_mode(callback: types.CallbackQuery, state: FSMContext):
    theme = callback.data.split(":")[1]
    cards = get_cards_by_theme(callback.from_user.id, theme)
    
    await state.update_data(cards=cards, current_index=0, score=0, theme=theme, total_cards=len(cards))
    await callback.message.edit_text(f"✅ Починаємо самоперевірку з теми: **{theme}**", parse_mode="Markdown")
    await ask_classic_question(callback.message, state)

async def ask_classic_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cards = data['cards']
    index = data['current_index']

    if index < len(cards):
        question = cards[index]['question']
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➡️ Пропустити", callback_data="skip_classic")],
            [types.InlineKeyboardButton(text="🏁 Завершити", callback_data="finish_quiz")]
        ])
        await message.answer(f"📝 **Питання {index + 1}/{len(cards)}:**\n\n{question}", reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(QuizState.waiting_for_answer)
    else:
        await finish_quiz_session(message, state)

@router.message(QuizState.waiting_for_answer)
async def handle_classic_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    card = data['cards'][data['current_index']]
    
    msg = await message.answer("🤔 Аналізую відповідь...")
    ai_result = await check_answer_gemini(card['question'], card['answer'], message.text)
    await msg.delete()

    status = ai_result.get("status", "Невизначено")
    if status == "Правильно":
        await state.update_data(score=data['score'] + 1)

    await message.answer(f"{'✅' if status == 'Правильно' else '❌'} **{status}**\n{ai_result.get('feedback', '')}", parse_mode="Markdown")
    await state.update_data(current_index=data['current_index'] + 1)
    await ask_classic_question(message, state)

# ------------------------------------
# ЗАГАЛЬНИЙ ФІНІШ
# ------------------------------------
@router.callback_query(F.data == "finish_quiz")
async def finish_quiz_session(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get('score', 0)
    total = data.get('total_cards', 0)
    theme = data.get('theme', 'Не визначено')
    
    # Розрахунок відсотка успішності
    percent = (score / total * 100) if total > 0 else 0
    
    # Вибір емодзі залежно від результату
    if percent == 100: rank = "🏆 Ідеально!"
    elif percent >= 70: rank = "🌟 Чудовий результат!"
    elif percent >= 40: rank = "📚 Добре, але варто ще повторити."
    else: rank = "👨‍💻 Потрібно більше практики."

    text = (
        f"🏁 **Тренування завершено!**\n\n"
        f"📘 Тема: *{theme}*\n"
        f"📊 Результат: `{score}` з `{total}`\n"
        f"📈 Успішність: `{percent:.1f}%`\n\n"
        f"{rank}"
    )

    save_training_result(message.chat.id, theme, score, total)
    await message.answer(text, parse_mode="Markdown")
    await state.clear()