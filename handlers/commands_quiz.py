from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ai.gemini_api import check_answer_gemini # Ваша функція перевірки з минулого кроку

router = Router()

# Визначаємо стани
class QuizState(StatesGroup):
    waiting_for_answer = State() # Стан, коли бот чекає відповідь від студента

# --- Функція, яка задає поточне питання ---
async def ask_current_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cards = data.get('cards')
    index = data.get('current_index', 0)

    if index < len(cards):
        question = cards[index]['question']
        # Ми НЕ показуємо відповідь, тільки питання!
        await message.answer(f"📝 **Питання {index + 1}/{len(cards)}:**\n\n{question}")
        
        # Переходимо в стан очікування відповіді
        await state.set_state(QuizState.waiting_for_answer)
    else:
        # Якщо питання закінчилися
        score = data.get('score', 0)
        await message.answer(f"🏁 **Тестування завершено!**\n\nТвій результат: {score} правильних відповідей з {len(cards)}.")
        await state.clear()

# --- Обробник відповіді користувача ---
@router.message(QuizState.waiting_for_answer)
async def handle_user_answer(message: types.Message, state: FSMContext):
    user_answer = message.text
    data = await state.get_data()
    
    cards = data['cards']
    index = data['current_index']
    current_card = cards[index]
    
    # Правильна відповідь (вона прихована від користувача, але є в пам'яті)
    correct_answer_db = current_card['answer'] 
    question_text = current_card['question']

    msg = await message.answer("🤔 Аналізую твою відповідь...")

    # --- ВИКЛИК GEMINI ДЛЯ ПЕРЕВІРКИ ---
    # Ми надсилаємо: Питання + Правильну відповідь + Відповідь студента
    ai_result = await check_answer_gemini(question_text, correct_answer_db, user_answer)
    
    status = ai_result.get("status", "Невизначено")
    feedback = ai_result.get("feedback", "")

    # Видаляємо повідомлення "Аналізую...", щоб не смітити
    await msg.delete()

    # --- Формуємо вердикт ---
    if status == "Правильно":
        # Нараховуємо бал
        new_score = data['score'] + 1
        await state.update_data(score=new_score)
        await message.answer(f"✅ **Правильно!**\n\n{feedback}")
        
    elif status == "Частково":
        # Можна давати 0.5 балу або 0
        await message.answer(f"⚠️ **Майже правильно.**\n{feedback}\n\n📖 *Правильна відповідь була:* {correct_answer_db}", parse_mode="Markdown")
        
    else:
        await message.answer(f"❌ **Неправильно.**\n{feedback}\n\n📖 *Правильна відповідь була:* {correct_answer_db}", parse_mode="Markdown")

    # --- Переходимо до наступного питання ---
    await state.update_data(current_index=index + 1)
    
    # Невелика пауза для комфорту (можна прибрати)
    # import asyncio; await asyncio.sleep(1) 
    
    await ask_current_question(message, state)