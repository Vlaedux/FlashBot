from aiogram import Router, types
from aiogram.filters import Command
from config import GEMINI_API_KEY
from ai.gemini_api import generate_flashcards_from_text

router = Router()
user_states = {}

@router.message(Command("generate"))
async def handle_generate(message: types.Message):
    user_states[message.chat.id] = "awaiting_lecture_text"
    await message.answer(
        "🔥 Чудово! Тепер просто надішли мені текст лекції, "
        "і я перетворю його на флеш-картки."
    )

@router.message(lambda msg: user_states.get(msg.chat.id) == "awaiting_lecture_text")
async def receive_lecture_text(message: types.Message):
    user_id = message.chat.id
    lecture_text = message.text

    try:
        wait_msg = await message.answer("Обробляю ваш текст... ⏳ Це може зайняти хвилину.")
        user_states.pop(user_id, None)

        flashcards = generate_flashcards_from_text(lecture_text, GEMINI_API_KEY)

        await message.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)

        if flashcards and len(flashcards) > 0:
            print(f"Симуляція: Збережено {len(flashcards)} карток для {user_id}.")
            await message.answer(
                f"✅ Готово! Згенеровано та збережено {len(flashcards)} флеш-карток.\n\n"
                "Можете починати тестування."
            )
            first_card = flashcards[0]
            await message.answer(
                f"Приклад першої картки:\n\nПитання: {first_card['question']}\nВідповідь: {first_card['answer']}"
            )
        else:
            await message.answer(
                "❌ Не вдалося розпізнати текст або згенерувати картки. "
                "Можливо, текст був занадто коротким або незрозумілим. Спробуйте ще раз."
            )

    except Exception as e:
        print(f"Критична помилка в receive_lecture_text: {e}")
        user_states.pop(user_id, None)
        await message.answer("❌ Ой, сталася неочікувана помилка під час генерації. Спробуйте ще раз.")
