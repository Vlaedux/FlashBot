from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ai.gemini_api import generate_flashcards_from_text, regenerate_flashcards, check_answer_gemini
from database.db import save_flashcards

router = Router()

# --- Стани для Квізу ---
class QuizFlow(StatesGroup):
    waiting_for_text = State()       # Чекаємо лекцію
    answering_question = State()     # Чекаємо відповідь на питання
    waiting_for_theme_save = State() # Чекаємо назву для збереження

# 1. Старт генерації
@router.message(Command("generate"))
async def cmd_generate(message: types.Message, state: FSMContext):
    await message.answer("🔥 Надішліть текст лекції.")
    await state.set_state(QuizFlow.waiting_for_text)

# 2. Обробка тексту лекції
@router.message(QuizFlow.waiting_for_text)
async def receive_lecture_text(message: types.Message, state: FSMContext):
    await state.update_data(original_text=message.text)
    
    wait_msg = await message.answer("⏳ Gemini 2.5 аналізує текст...")

    # --- ВАЖЛИВО: Додано await ---
    cards = await generate_flashcards_from_text(message.text)
    
    await wait_msg.delete()

    if not cards:
        return await message.answer("❌ Не вдалося створити картки. Перевірте доступ до моделі 2.5 або спробуйте інший текст.")

    # Зберігаємо картки і починаємо з індексу 0
    await state.update_data(cards=cards, current_index=0, score=0)
    
    await message.answer(f"✅ Створено {len(cards)} питань! Починаємо тест.")
    await ask_current_question(message, state)

# Допоміжна функція: Задати питання
async def ask_current_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cards = data['cards']
    index = data['current_index']

    if index < len(cards):
        question = cards[index]['question']
        # Показуємо ТІЛЬКИ питання
        await message.answer(f"📝 **Питання {index + 1}/{len(cards)}:**\n\n{question}", parse_mode="Markdown")
        await state.set_state(QuizFlow.answering_question)
    else:
        await finish_quiz(message, state)

# 3. Перевірка відповіді
@router.message(QuizFlow.answering_question)
async def handle_answer(message: types.Message, state: FSMContext):
    user_answer = message.text
    data = await state.get_data()
    
    cards = data['cards']
    index = data['current_index']
    current_card = cards[index]
    
    msg = await message.answer("🤔 Перевіряю...")

    # --- ВАЖЛИВО: Додано await для перевірки ---
    result = await check_answer_gemini(current_card['question'], current_card['answer'], user_answer)
    
    await msg.delete()

    status = result.get("status", "Невизначено")
    feedback = result.get("feedback", "")
    
    if status == "Правильно":
        new_score = data['score'] + 1
        await state.update_data(score=new_score)
        await message.answer(f"✅ **Правильно!**\n{feedback}", parse_mode="Markdown")
    elif status == "Частково":
        await message.answer(f"⚠️ **Майже правильно.**\n{feedback}\n\n📖 *Правильна відповідь:* {current_card['answer']}", parse_mode="Markdown")
    else:
        await message.answer(f"❌ **Неправильно.**\n{feedback}\n\n📖 *Правильна відповідь:* {current_card['answer']}", parse_mode="Markdown")

    # Наступне питання
    await state.update_data(current_index=index + 1)
    await ask_current_question(message, state)

# 4. Фініш і кнопки
async def finish_quiz(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get('score', 0)
    total = len(data.get('cards', []))

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔁 Перегенерувати (Gemini 2.5)", callback_data="regen")],
            [types.InlineKeyboardButton(text="💾 Зберегти результат", callback_data="save")]
        ]
    )
    
    await message.answer(
        f"🏁 **Тест завершено!**\nТвій результат: {score} з {total}.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# --- CALLBACKS ---

@router.callback_query(lambda c: c.data == "regen")
async def callback_regenerate(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    original_text = data.get('original_text')

    if not original_text:
        return await callback.answer("Текст втрачено.")

    await callback.message.edit_text("🔄 Gemini 2.5 генерує нові питання...")
    
    # --- ВАЖЛИВО: Додано await ---
    new_cards = await regenerate_flashcards(original_text)
    
    if not new_cards:
        return await callback.message.answer("Помилка генерації.")

    await state.update_data(cards=new_cards, current_index=0, score=0)
    await ask_current_question(callback.message, state)

@router.callback_query(lambda c: c.data == "save")
async def callback_save(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📌 Введіть назву теми для збереження:")
    await state.set_state(QuizFlow.waiting_for_theme_save)
    await callback.answer()

@router.message(QuizFlow.waiting_for_theme_save)
async def save_handler(message: types.Message, state: FSMContext):
    theme = message.text
    data = await state.get_data()
    cards = data.get('cards')
    
    if cards:
        save_flashcards(message.from_user.id, cards, theme)
        await message.answer(f"💾 Збережено: *{theme}*", parse_mode="Markdown")
    
    await state.clear()