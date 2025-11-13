# handlers/commands_ai.py
from aiogram import Router, types
from aiogram.filters import Command
from ai.gemini_api import generate_flashcards_from_text, regenerate_flashcards

router = Router()

# Локальна пам’ять користувача
user_last_text = {}   # user_id -> lecture text


@router.message(Command("generate"))
async def cmd_generate(message: types.Message):
    await message.answer(
        "🔥 Надішліть текст лекції — я згенерую флеш-картки."
    )

    # Зберігаємо стан
    user_last_text[message.from_user.id] = "__waiting__"


@router.message()
async def receive_text(message: types.Message):
    user_id = message.from_user.id

    # Якщо користувач не викликав /generate
    if user_last_text.get(user_id) != "__waiting__":
        return

    lecture_text = message.text
    user_last_text[user_id] = lecture_text  # зберігаємо оригінал

    wait = await message.answer("⏳ Генерую картки, зачекайте...")

    cards = generate_flashcards_from_text(lecture_text)

    await wait.delete()

    if not cards:
        return await message.answer("❌ Не вдалося згенерувати картки. Спробуйте інший текст.")

    # Кнопка перегенерації
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔁 Перегенерувати тему", callback_data="regen")]
        ]
    )

    await message.answer(
        f"✅ Згенеровано {len(cards)} карток!",
        reply_markup=keyboard
    )

    # Показати одну картку
    q = cards[0]["question"]
    a = cards[0]["answer"]

    await message.answer(f"📘 *Приклад картки*\n\n❓ {q}\n✅ {a}", parse_mode="Markdown")


# --- CALLBACK — перегенерація ---
@router.callback_query(lambda c: c.data == "regen")
async def regenerate_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in user_last_text:
        return await callback.answer("Помилка: не знайдено текст.")

    lecture_text = user_last_text[user_id]

    await callback.answer("🔄 Генерую нову версію...")

    new_cards = regenerate_flashcards(lecture_text)

    if not new_cards:
        return await callback.message.edit_text("❌ Помилка генерації. Спробуйте /generate.")

    # Нова кнопка
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🔁 Перегенерувати тему", callback_data="regen")]
        ]
    )

    await callback.message.edit_text(
        f"🔄 Оновлено! Нових карток: {len(new_cards)}",
        reply_markup=keyboard
    )

    q = new_cards[0]["question"]
    a = new_cards[0]["answer"]

    await callback.message.answer(
        f"📘 *Нова картка*\n\n❓ {q}\n✅ {a}",
        parse_mode="Markdown"
    )
