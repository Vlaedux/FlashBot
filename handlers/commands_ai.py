from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import save_flashcards 
from ai.gemini_api import generate_flashcards_from_text, regenerate_flashcards 

router = Router()

# handlers/commands_ai.py

@router.message(Command("generate"))
@router.message(F.text == "💡 Створити картки") # Додаємо реакцію на кнопку
async def cmd_generate(message: types.Message, state: FSMContext):
    await message.answer("🔥 Надішліть текст лекції — я згенерую флеш-картки.")
    await state.set_state(GenerationFlow.waiting_for_text)

# --- ОНОВЛЕНІ СТАНИ для процесу Генерації ---
class GenerationFlow(StatesGroup):
    waiting_for_text = State()          
    cards_ready = State()               
    waiting_for_theme_name = State()    # Стан для очікування назви теми

# ------------------------------------
# 1. /generate: Старт генерації
# ------------------------------------
@router.message(Command("generate"))
async def cmd_generate(message: types.Message, state: FSMContext):
    await message.answer("🔥 Надішліть текст лекції — я згенерую флеш-картки.")
    await state.set_state(GenerationFlow.waiting_for_text)


# ------------------------------------
# 2. Обробка тексту лекції та Генерація
# ------------------------------------
@router.message(GenerationFlow.waiting_for_text)
async def receive_lecture_text(message: types.Message, state: FSMContext):
    lecture_text = message.text
    
    await state.update_data(original_text=lecture_text) 
    
    wait_msg = await message.answer("⏳ Gemini 2.5 аналізує текст та генерує картки...")

    cards = await generate_flashcards_from_text(lecture_text)
    
    await wait_msg.delete()

    if not cards:
        await state.clear()
        return await message.answer("❌ Не вдалося створити картки. Спробуйте інший текст.")

    await state.update_data(generated_cards=cards)
    await display_cards_and_buttons(message, cards)
    
    await state.set_state(GenerationFlow.cards_ready)


# ------------------------------------
# ДОПОМІЖНА ФУНКЦІЯ: Відображення карток та кнопок
# ------------------------------------
async def display_cards_and_buttons(message: types.Message, cards: list):
    """Форматує та відображає згенеровані картки з кнопками."""
    
    card_list_text = "\n\n".join([
        f"*{i}.*\n❓ *{c['question']}*\n✅ {c['answer']}"
        for i, c in enumerate(cards, 1)
    ])

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔄 Перегенерувати тему", callback_data="regen_cards")],
        [types.InlineKeyboardButton(text="💾 Зберегти картки", callback_data="save_cards")]
    ])
    
    await message.answer(
        f"✅ Згенеровано {len(cards)} карток!\n\n{card_list_text}",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ------------------------------------
# 3. CALLBACK: Зберегти картки (Ініціація очікування теми)
# ------------------------------------
@router.callback_query(F.data == "save_cards", GenerationFlow.cards_ready)
async def callback_save_cards(callback: types.CallbackQuery, state: FSMContext):
    
    # ⭐️ ВИПРАВЛЕННЯ: Надсилаємо НОВЕ повідомлення і прибираємо кнопки зі старого!
    await callback.message.answer("📌 Введіть назву теми, під якою зберегти картки:")
    await callback.message.edit_reply_markup(reply_markup=None) 
    
    await state.set_state(GenerationFlow.waiting_for_theme_name)
    await callback.answer()


# ------------------------------------
# 4. ОБРОБНИК: Збереження (Реагує тільки на НОВИЙ СТАН)
# ------------------------------------
@router.message(GenerationFlow.waiting_for_theme_name)
async def save_handler(message: types.Message, state: FSMContext):
    
    data = await state.get_data()
    cards = data.get('generated_cards')
    
    if not cards:
        await state.clear()
        return await message.answer("Помилка: Картки для збереження не знайдено.")

    theme = message.text.strip()
    
    save_flashcards(message.from_user.id, cards, theme)
    
    await message.answer(f"💾 Картки успішно збережено під темою: *{theme}*.\n\n"
                     "Ви можете переглянути їх за допомогою меню 'Мої картки'.", 
                     parse_mode="Markdown")
    
    await state.clear()


# ------------------------------------
# 5. CALLBACK: Перегенерувати тему 
# ------------------------------------
@router.callback_query(F.data == "regen_cards", GenerationFlow.cards_ready)
async def regenerate_handler(callback: types.CallbackQuery, state: FSMContext):
    
    data = await state.get_data()
    lecture_text = data.get('original_text')
    
    if not lecture_text:
        await callback.answer("Текст лекції втрачено.")
        return

    await callback.message.edit_text("🔄 Gemini 2.5 генерує нову версію карток...")

    new_cards = await regenerate_flashcards(lecture_text)

    if not new_cards:
        await callback.message.edit_text("❌ Помилка перегенерації.")
        return

    await state.update_data(generated_cards=new_cards)
    
    await display_cards_and_buttons(callback.message, new_cards)
    await callback.answer("Картки оновлено!")