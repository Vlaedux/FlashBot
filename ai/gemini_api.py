import json
import google.generativeai as genai
import re

def generate_flashcards_from_text(lecture_text, GEMINI_API_KEY):
    """
    Надсилає текст до Gemini та просить згенерувати Q/A пари.
    Ця версія "вирізає" JSON з відповіді.
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"Помилка конфігурації Gemini: {e}")
        return None

    prompt = f"""
    Твоє завдання – створити флеш-картки з наданого тексту лекції.
    Проаналізуй текст нижче і згенеруй на його основі 10-15 пар "питання-відповідь".

    Вимоги до результату:
    1. Поверни результат у форматі JSON-масиву.
    2. Кожен об'єкт у масиві повинен мати два ключі: "question" та "answer".

    Приклад формату:
    [
      {{"question": "Що таке фотосинтез?", "answer": "Процес перетворення світлової енергії на хімічну."}}
    ]

    Ось текст лекції:
    ---
    {lecture_text}
    ---
    """

    try:
        response = gemini_model.generate_content(prompt)
        raw_text = response.text

        # Потужний парсинг JSON (шукаємо текст між [ та ])
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)

        json_text = ""
        if match:
            json_text = match.group(0)
        else:
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if match:
                json_text = match.group(0)
            else:
                print(f"Помилка: Не вдалося знайти JSON у відповіді: {raw_text}")
                return None

        flashcards = json.loads(json_text)
        print(json.dumps(flashcards, indent=2, ensure_ascii=False))


        if isinstance(flashcards, list) and all(isinstance(item, dict) for item in flashcards):
            return flashcards
        elif isinstance(flashcards, dict):
            return [flashcards]
        else:
            print(f"Помилка: Gemini повернув дивний JSON: {json_text}")
            return None

    except json.JSONDecodeError:
        print(f"Помилка декодування JSON. Сира відповідь: {response.text}")
        return None
    except Exception as e:
        print(f"Виникла помилка API Gemini: {e}")
        return None
