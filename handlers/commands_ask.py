from aiogram import Router, types
from aiogram.filters import Command
from ai.gemini_api import ask_gemini

router = Router()

# Словник для відстеження стану: чи чекаємо ми питання від користувача
user_waiting_question = {} 

@router.message(Command("ask"))
async def cmd_ask(message: types.Message):
    user_waiting_question[message.from_user.id] = True
    await message.answer("❓ Надішліть ваше питання, і я дам відповідь.")

@router.message()
async def receive_question(message: types.Message):
    user_id = message.from_user.id

    # Якщо ми не чекаємо питання від цього користувача — ігноруємо
    if user_waiting_question.get(user_id) is not True:
        return 

    question = message.text
    # Видаляємо користувача зі списку очікування, щоб він не спамив
    user_waiting_question.pop(user_id, None)

    wait_msg = await message.answer("⏳ Думаю...")

    answer = await ask_gemini(question)

    await wait_msg.delete()

    # Виводимо відповідь без Markdown, щоб не було помилок форматування
    await message.answer(
        f"💬 Ваше питання:\n{question}\n\n"
        f"🤖 Відповідь:\n{answer}"
    )