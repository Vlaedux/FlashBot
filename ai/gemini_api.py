# ai/gemini_api.py
import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


def _extract_json(raw_text: str):
    """Допоміжна функція: вирізає JSON зі відповіді Gemini."""
    match = re.search(r"\[.*\]", raw_text, re.DOTALL)
    if match:
        return match.group(0)

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        return match.group(0)

    return None


def generate_flashcards_from_text(lecture_text: str):
    """Генерує нові картки з тексту."""
    prompt = f"""
    Створи 10–15 флеш-карток у форматі JSON:
    [
      {{"question": "...", "answer": "..."}}
    ]

    Ось текст:
    ---
    {lecture_text}
    ---
    """

    response = model.generate_content(prompt)
    json_raw = _extract_json(response.text)

    if not json_raw:
        return None

    try:
        result = json.loads(json_raw)
        if isinstance(result, dict):
            return [result]
        return result
    except json.JSONDecodeError:
        return None


def regenerate_flashcards(lecture_text: str):
    """Перегенерація — така ж логіка, але з іншим промптом."""
    prompt = f"""
    Перегенеруй флеш-картки з цього ж тексту.
    Структура:
    [
      {{"question": "...", "answer": "..."}}
    ]

    Текст:
    ---
    {lecture_text}
    ---
    """

    response = model.generate_content(prompt)
    json_raw = _extract_json(response.text)

    if not json_raw:
        return None

    try:
        result = json.loads(json_raw)
        if isinstance(result, dict):
            return [result]
        return result
    except json.JSONDecodeError:
        return None
