import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

# Налаштування
genai.configure(api_key=GEMINI_API_KEY)

# --- ВИКОРИСТОВУЄМО ЗАПИТАНУ МОДЕЛЬ 2.5 ---
model = genai.GenerativeModel("gemini-2.5-flash")

def _extract_json(raw_text: str):
    """Допоміжна функція: вирізає JSON зі відповіді Gemini."""
    # Шукаємо масив [...]
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if match:
        return match.group(0)

    # Шукаємо об'єкт {...}
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        return match.group(0)

    return None

async def generate_flashcards_from_text(lecture_text: str):
    """Генерує нові картки з тексту (Асинхронно)."""
    prompt = f"""
    Створи 10–15 флеш-карток у форматі JSON:
    [
      {{"question": "...", "answer": "..."}}
    ]
    Питання та відповіді українською мовою.

    Ось текст:
    ---
    {lecture_text}
    ---
    """

    try:
        response = await model.generate_content_async(prompt)
        json_raw = _extract_json(response.text)

        if not json_raw:
            return None

        result = json.loads(json_raw)
        if isinstance(result, dict):
            return [result]
        return result
    except Exception as e:
        print(f"Помилка генерації (2.5): {e}")
        return None

async def regenerate_flashcards(lecture_text: str):
    """Перегенерація (Асинхронно)."""
    prompt = f"""
    Перегенеруй флеш-картки з цього ж тексту. Зроби інші питання.
    Структура JSON:
    [
      {{"question": "...", "answer": "..."}}
    ]

    Текст:
    ---
    {lecture_text}
    ---
    """

    try:
        response = await model.generate_content_async(prompt)
        json_raw = _extract_json(response.text)

        if not json_raw:
            return None

        result = json.loads(json_raw)
        if isinstance(result, dict):
            return [result]
        return result
    except Exception as e:
        print(f"Помилка перегенерації (2.5): {e}")
        return None

async def check_answer_gemini(question: str, correct_answer: str, user_answer: str):
    """
    Перевіряє відповідь студента (Асинхронно).
    """
    prompt = f"""
    Ти — викладач. Перевір відповідь студента.
    
    Питання: {question}
    Правильна відповідь: {correct_answer}
    Відповідь студента: {user_answer}

    1. Порівняй відповідь з правильною.
    2. Оціни статус: "Правильно", "Частково" або "Неправильно".
    3. Дай короткий коментар (feedback).

    Поверни JSON:
    {{
        "status": "Правильно" | "Частково" | "Неправильно",
        "feedback": "Твій коментар"
    }}
    """

    try:
        response = await model.generate_content_async(prompt)
        json_raw = _extract_json(response.text)
        
        if json_raw:
            return json.loads(json_raw)
        else:
            return {"status": "Неправильно", "feedback": "Не вдалося розпізнати відповідь ШІ."}
            
    except Exception as e:
        print(f"Помилка перевірки (2.5): {e}")
        return {"status": "Помилка", "feedback": "Помилка з'єднання з ШІ."}

async def ask_gemini(question: str):
    """
    Проста функція: отримує питання і повертає текстову відповідь від Gemini 2.5.
    """
    # Використовуємо ту ж модель, що і всюди
    model = genai.GenerativeModel("gemini-2.5-flash") # Або 1.5-flash, якщо 2.5 не працює

    try:
        response = await model.generate_content_async(question)
        return response.text
    except Exception as e:
        print(f"Помилка ask_gemini: {e}")
        return "Вибачте, я не зміг отримати відповідь від Gemini. Спробуйте пізніше."