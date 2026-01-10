from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Тренировки", callback_data="programs")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")
    )
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Меню админа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Тренировки", callback_data="programs")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Управление", callback_data="admin_menu")
    )
    return builder.as_markup()


def admin_panel_kb() -> InlineKeyboardMarkup:
    """Панель управления для админа."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить программу", callback_data="add_program")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить день", callback_data="add_day")
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить упражнение", callback_data="add_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить...", callback_data="delete_menu")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def programs_kb(programs: list, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Список программ."""
    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"program:{p['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def days_kb(days: list, program_id: int) -> InlineKeyboardMarkup:
    """Список дней программы."""
    builder = InlineKeyboardBuilder()
    for d in days:
        day_name = d["name"] if d["name"] else f"День {d['day_number']}"
        builder.row(
            InlineKeyboardButton(
                text=day_name,
                callback_data=f"day:{d['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="programs")
    )
    return builder.as_markup()


def exercises_kb(exercises: list, day_id: int) -> InlineKeyboardMarkup:
    """Список упражнений дня."""
    builder = InlineKeyboardBuilder()
    for i, ex in enumerate(exercises, 1):
        builder.row(
            InlineKeyboardButton(
                text=f"{i}. {ex['name']}",
                callback_data=f"exercise:{ex['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=f"back_to_days:{day_id}")
    )
    return builder.as_markup()


def exercise_detail_kb(exercise_id: int, day_id: int) -> InlineKeyboardMarkup:
    """Кнопки для конкретного упражнения."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💪 Записать подход",
            callback_data=f"log:{exercise_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📈 История",
            callback_data=f"history:{exercise_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data=f"day:{day_id}")
    )
    return builder.as_markup()


def back_to_exercise_kb(exercise_id: int) -> InlineKeyboardMarkup:
    """Кнопка назад к упражнению."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="« Назад",
            callback_data=f"exercise:{exercise_id}"
        )
    )
    return builder.as_markup()


def confirm_kb(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Подтверждение действия."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"confirm_{action}:{item_id}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data="cancel_action"
        )
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    """Кнопка пропустить."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Пропустить", callback_data=callback_data)
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()