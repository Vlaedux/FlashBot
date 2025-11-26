from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
# Імпортуємо всі функції БД, включаючи збереження статистики
from database.db import get_user_themes, get_cards_by_theme, save_training_result 
from ai.gemini_api import check_answer_gemini

router = Router()

# --- Стани для Квізу ---
class QuizState(StatesGroup):
    waiting_for_answer = State() 


# ------------------------------------
# 1. КОМАНДА /quiz: Старт та вибір теми
# ------------------------------------
@router.message(Command("quiz"))
async def quiz_start(message: types.Message):
    user_id = message.from_user.id
    themes = get_user_themes(user_id) 

    if not themes:
        return await message.answer("У вас немає збережених карток. Скористайтеся /generate.")

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=theme, callback_data=f"start_quiz:{theme}")] 
        for theme in themes
    ])

    await message.answer("🧠 **Оберіть тему** для проходження квізу:", reply_markup=keyboard, parse_mode="Markdown")


# ------------------------------------
# 2. CALLBACK: Обробка вибору теми та ЗАПУСК FSM
# ------------------------------------
@router.callback_query(F.data.startswith("start_quiz:"))
async def start_training_quiz_session(callback: types.CallbackQuery, state: FSMContext):
    theme = callback.data.split(":")[1]
    user_id = callback.from_user.id

    await callback.message.edit_text(f"🧠 Завантажую картки з теми: **{theme}**...")

    cards = get_cards_by_theme(user_id, theme) 
    
    if not cards:
        return await callback.message.edit_text("Помилка: Картки не завантажені.")

    await state.update_data(
        cards=cards,
        current_index=0,
        score=0,
        theme=theme,
        total_cards=len(cards)
    )
    
    await callback.message.edit_text(f"✅ Готово! Починаємо квіз. Картки: {len(cards)}")
    
    await ask_current_question(callback.message, state) 
    await callback.answer()


# ------------------------------------
# 3. ФУНКЦІЯ: Задати поточне питання 
# ------------------------------------
async def ask_current_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cards = data.get('cards')
    index = data.get('current_index', 0)

    if index < len(cards):
        question = cards[index]['question']
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➡️ Пропустити", callback_data="skip_question")]
        ])
        
        await message.answer(
            f"📝 **Питання {index + 1}/{len(cards)}:**\n\n{question}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        await state.set_state(QuizState.waiting_for_answer)
    else:
        # Фіналізація та збереження статистики
        score = data.get('score', 0)
        total_cards = len(cards)
        theme = data.get('theme', 'Не визначено')

        save_training_result(message.from_user.id, theme, score, total_cards)
        stats_msg = "\n*Статистика тренування збережена.*"

        await message.answer(
            f"🏁 **Тестування завершено!**\n\nТвій результат: {score} правильних відповідей з {total_cards}."
            f"{stats_msg}"
        )
        await state.clear()


# ------------------------------------
# 4. ОБРОБНИК: Пропуск питання
# ------------------------------------
@router.callback_query(F.data == "skip_question")
async def skip_question(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data.get('current_index', 0)
    
    await state.update_data(current_index=index + 1)
    
    await callback.message.edit_text("⏭️ Питання пропущено.")
    
    await ask_current_question(callback.message, state)
    await callback.answer()


# ------------------------------------
# 5. ОБРОБНИК: Перевірка відповіді 
# ------------------------------------
@router.message(QuizState.waiting_for_answer)
async def handle_user_answer(message: types.Message, state: FSMContext):
    user_answer = message.text
    data = await state.get_data()
    
    cards = data['cards']
    index = data['current_index']
    current_card = cards[index]
    
    correct_answer_db = current_card['answer'] 
    question_text = current_card['question']

    msg = await message.answer("🤔 Аналізую твою відповідь...")

    ai_result = await check_answer_gemini(question_text, correct_answer_db, user_answer)
    
    status = ai_result.get("status", "Невизначено")
    feedback = ai_result.get("feedback", "")

    await msg.delete()

    # Обов'язково використовуємо parse_mode="Markdown" для тексту від Gemini
    if status == "Правильно":
        new_score = data['score'] + 1
        await state.update_data(score=new_score)
        await message.answer(f"✅ **Правильно!**\n\n{feedback}", parse_mode="Markdown")
        
    elif status == "Частково":
        await message.answer(f"⚠️ **Майже правильно.**\n{feedback}\n\n📖 *Правильна відповідь була:* {correct_answer_db}", parse_mode="Markdown")
        
    else:
        await message.answer(f"❌ **Неправильно.**\n{feedback}\n\n📖 *Правильна відповідь була:* {correct_answer_db}", parse_mode="Markdown")

    await state.update_data(current_index=index + 1)
    await ask_current_question(message, state)