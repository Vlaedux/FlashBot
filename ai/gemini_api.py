import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

# Налаштування Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Використовуємо модель 2.5-flash
model = genai.GenerativeModel("gemini-2.5-flash")

def _extract_json(raw_text: str):
    """Вирізає JSON зі відповіді Gemini для запобігання помилкам парсингу."""
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
    """
    Генерує картки з тексту лекції. 
    Додано поле 'options' для підтримки режиму тестів з кнопками.
    """
    prompt = f"""
    Проаналізуй текст і створи 10–15 флеш-карток у форматі JSON.
    Поверни лише чистий JSON масив.

    Кожен об'єкт ПОВИНЕН мати таку структуру:
    {{
      "question": "Питання українською",
      "answer": "Правильна відповідь",
      "options": ["Неправильний варіант 1", "Неправильний варіант 2", "Неправильний варіант 3"]
    }}

    Важливо: поле 'options' обов'язково має містити 3 неправильні, але правдоподібні варіанти.

    Ось текст лекції:
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
        
        # Перетворення поодинокого об'єкта в список
        if isinstance(result, dict):
            result = [result]
            
        # Гарантуємо наявність поля options для кожної картки
        for item in result:
            if "options" not in item:
                item["options"] = []
                
        return result
    except Exception as e:
        print(f"Помилка генерації (2.5): {e}")
        return None

async def regenerate_flashcards(lecture_text: str):
    """Перегенерація карток з варіантами відповідей."""
    prompt = f"""
    Перегенеруй флеш-картки з цього ж тексту. Зроби інші питання.
    
    Формат JSON:
    [
      {{
        "question": "...",
        "answer": "...",
        "options": ["варіант1", "варіант2", "варіант3"]
      }}
    ]
    
    Обов'язково додай 3 неправильні варіанти в 'options'.

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
            result = [result]
            
        for item in result:
            if "options" not in item:
                item["options"] = []
                
        return result
    except Exception as e:
        print(f"Помилка перегенерації (2.5): {e}")
        return None

async def check_answer_gemini(question: str, correct_answer: str, user_answer: str):
    """Перевіряє текстову відповідь студента в режимі 'Самоперевірка'."""
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
    """Отримує пряму відповідь на довільне питання користувача."""
    try:
        response = await model.generate_content_async(question)
        return response.text
    except Exception as e:
        print(f"Помилка ask_gemini: {e}")
        return "Вибачте, я не зміг отримати відповідь від Gemini. Спробуйте пізніше."