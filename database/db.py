# database/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "flashbot.db"


def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE flashcards ADD COLUMN theme TEXT DEFAULT 'Без теми';")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


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
    
    # Таблиця training_stats (для статистики квізу)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS training_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            theme TEXT NOT NULL,
            score INTEGER NOT NULL,
            total_cards INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()

    migrate_db()


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

def save_training_result(user_id: int, theme: str, score: int, total_cards: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO training_stats (user_id, theme, score, total_cards) VALUES (?, ?, ?, ?)",
        (user_id, theme, score, total_cards)
    )

    conn.commit()
    conn.close()


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


def get_cards_by_theme(user_id: int, theme: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Отримуємо ID, question, answer
    cur.execute(
        "SELECT id, question, answer FROM flashcards WHERE user_id = ? AND theme = ?",
        (user_id, theme)
    )
    rows = cur.fetchall()
    conn.close()

    return [{"id": c_id, "question": q, "answer": a} for c_id, q, a in rows]


def update_card(card_id: int, question: str, answer: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "UPDATE flashcards SET question = ?, answer = ? WHERE id = ?",
        (question, answer, card_id)
    )
    conn.commit()
    conn.close()

def delete_card(card_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()

def delete_theme(user_id: int, theme: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM flashcards WHERE user_id = ? AND theme = ?", (user_id, theme))
    conn.commit()
    conn.close()