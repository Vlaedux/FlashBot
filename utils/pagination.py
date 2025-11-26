# utils/pagination.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

PAGE_SIZE = 1 

def paginate_list(items: list, page_size: int = PAGE_SIZE) -> list:
    """Розділяє список елементів на сторінки."""
    if not items:
        return []
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]


def build_keyboard_view(current_page: int, total_pages: int, theme: str, card_id: int, showing_answer: bool) -> InlineKeyboardMarkup:
    """Створює клавіатуру для пагінації в режимі ПЕРЕГЛЯДУ (/mycards)."""
    
    keyboard_buttons = []
    
    # Ряд 1: Кнопки дії (Показати/Редагувати/Видалити)
    action_buttons = []

    if not showing_answer:
        action_buttons.append(
            InlineKeyboardButton(text="📖 Показати відповідь", callback_data=f"show_answer:{theme}:{current_page}")
        )
    
    action_buttons.append(
        InlineKeyboardButton(text="✏️ Редагувати", callback_data=f"edit_card:{card_id}")
    )
    # Додаємо card_id, theme, current_page для повернення після видалення
    action_buttons.append(
        InlineKeyboardButton(text="❌ Видалити", callback_data=f"delete_card_conf:{card_id}:{theme}:{current_page}") 
    )
    
    
    # Ряд 2: Навігація
    nav_buttons = []
    
    if current_page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"view_page:{theme}:{current_page - 1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="ignore")
    )
    
    if current_page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"view_page:{theme}:{current_page + 1}")
        )

    return InlineKeyboardMarkup(inline_keyboard=[action_buttons, nav_buttons])