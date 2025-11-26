# database/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "flashbot.db"


# --- Migrations (додає поле theme, якщо його нема) ---
def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE flashcards ADD COLUMN theme TEXT DEFAULT 'Без теми';")
    except sqlite3.OperationalError:
        pass  # поле вже існує
    conn.commit()
    conn.close()


# --- 1. Ініціалізація БД ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            theme TEXT DEFAULT 'Без теми'
        );
    """)

    conn.commit()
    conn.close()

    migrate_db()


# --- 2. Збереження карток під тему ---
def save_flashcards(user_id: int, cards: list, theme: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for card in cards:
        cur.execute(
            "INSERT INTO flashcards (user_id, question, answer, theme) VALUES (?, ?, ?, ?)",
            (user_id, card["question"], card["answer"], theme)
        )

    conn.commit()
    conn.close()


# --- 3. Отримати список тем ---
def get_user_themes(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT DISTINCT theme FROM flashcards WHERE user_id = ?",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


# --- 4. Отримати картки по темі ---
def get_cards_by_theme(user_id: int, theme: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT question, answer FROM flashcards WHERE user_id = ? AND theme = ?",
        (user_id, theme)
    )
    rows = cur.fetchall()
    conn.close()

    return [{"question": q, "answer": a} for q, a in rows]


# --- 5. Видалити картки по темі (опціонально) ---
def clear_theme(user_id: int, theme: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM flashcards WHERE user_id = ? AND theme = ?", (user_id, theme))

    conn.commit()
    conn.close()
