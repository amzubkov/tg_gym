from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(has_active_program: bool = False) -> InlineKeyboardMarkup:
    """Главное меню."""
    builder = InlineKeyboardBuilder()
    if has_active_program:
        builder.row(
            InlineKeyboardButton(text="💪 Сегодняшняя тренировка", callback_data="today_workout")
        )
    builder.row(
        InlineKeyboardButton(text="📋 Выбрать программу", callback_data="select_program")
    )
    builder.row(
        InlineKeyboardButton(text="📚 Все тренировки", callback_data="all_workouts")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Своё упражнение", callback_data="custom_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Подобрать упражнения", callback_data="ai_exercises")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")
    )
    return builder.as_markup()


def admin_menu_kb(has_active_program: bool = False) -> InlineKeyboardMarkup:
    """Меню админа."""
    builder = InlineKeyboardBuilder()
    if has_active_program:
        builder.row(
            InlineKeyboardButton(text="💪 Сегодняшняя тренировка", callback_data="today_workout")
        )
    builder.row(
        InlineKeyboardButton(text="📋 Выбрать программу", callback_data="select_program")
    )
    builder.row(
        InlineKeyboardButton(text="📚 Все тренировки", callback_data="all_workouts")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ Своё упражнение", callback_data="custom_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 Подобрать AI упражнения", callback_data="ai_exercises")
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
        InlineKeyboardButton(text="🏷 Теги", callback_data="manage_tags")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить...", callback_data="delete_menu")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="manage_users")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def all_workouts_kb() -> InlineKeyboardMarkup:
    """Подменю 'Все тренировки'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 По программам", callback_data="programs")
    )
    builder.row(
        InlineKeyboardButton(text="🏷 По тегу", callback_data="tags_menu")
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
        InlineKeyboardButton(text="« Назад", callback_data="all_workouts")
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


def exercise_detail_kb(exercise_id: int, day_id: int, is_admin: bool = False, next_exercise_id: int = None) -> InlineKeyboardMarkup:
    """Кнопки для конкретного упражнения."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💪 Записать подход",
            callback_data=f"log:{exercise_id}"
        )
    )
    # Пропустить — только если есть следующее упражнение
    if next_exercise_id:
        builder.row(
            InlineKeyboardButton(
                text="⏭ Пропустить",
                callback_data=f"exercise:{next_exercise_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="📈 История",
            callback_data=f"history:{exercise_id}"
        )
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(
                text="🏷 Теги",
                callback_data=f"edit_tags:{exercise_id}"
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


def weight_type_kb() -> InlineKeyboardMarkup:
    """Выбор типа веса для упражнения."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ Гантели (5-50кг)", callback_data="wt:10")
    )
    builder.row(
        InlineKeyboardButton(text="🏋️ Штанга (50-100кг)", callback_data="wt:100")
    )
    builder.row(
        InlineKeyboardButton(text="🤸 Без веса", callback_data="wt:0")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()


def select_program_kb(programs: list) -> InlineKeyboardMarkup:
    """Выбор программы для начала."""
    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"start_program:{p['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def today_workout_kb(day_id: int) -> InlineKeyboardMarkup:
    """Клавиатура текущей тренировки."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Упражнения дня", callback_data=f"day:{day_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Закончить день", callback_data="complete_day")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def program_finished_kb() -> InlineKeyboardMarkup:
    """Программа завершена."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Выбрать новую программу", callback_data="select_program")
    )
    builder.row(
        InlineKeyboardButton(text="« В меню", callback_data="back_to_main")
    )
    return builder.as_markup()


def custom_exercise_kb(recent_exercises: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для своего упражнения."""
    builder = InlineKeyboardBuilder()
    if recent_exercises:
        for name in recent_exercises:
            builder.row(
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"quick_custom:{name[:50]}"
                )
            )
    builder.row(
        InlineKeyboardButton(text="✏️ Ввести новое", callback_data="new_custom")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


# ==================== TAGS ====================

def tags_kb(tags: list) -> InlineKeyboardMarkup:
    """Список тегов для фильтрации."""
    builder = InlineKeyboardBuilder()
    for tag in tags:
        count = tag.get("exercise_count", 0)
        builder.row(
            InlineKeyboardButton(
                text=f"#{tag['name']} ({count})",
                callback_data=f"tag:{tag['name']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="all_workouts")
    )
    return builder.as_markup()


def tag_exercises_kb(exercises: list, tag_name: str) -> InlineKeyboardMarkup:
    """Список упражнений по тегу."""
    builder = InlineKeyboardBuilder()
    for ex in exercises:
        # Показываем программу в названии
        builder.row(
            InlineKeyboardButton(
                text=f"{ex['name']} ({ex['program_name']})",
                callback_data=f"exercise:{ex['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="tags_menu")
    )
    return builder.as_markup()


# ==================== QUICK INPUT ====================

def weight_kb(weight_type: int = 10) -> InlineKeyboardMarkup | None:
    """Быстрый выбор веса.

    weight_type:
        0 - без веса (возвращает None, шаг пропускается)
        10 - гантели (5-50 кг)
        100 - штанга (50-100 кг)
    """
    if weight_type == 0:
        return None

    builder = InlineKeyboardBuilder()

    if weight_type == 100:
        # Штанга: 50-100 кг
        weights = [50, 60, 70, 80, 90, 100]
    else:
        # Гантели: 5-50 кг (по умолчанию)
        weights = [5, 10, 15, 20, 25, 30, 40, 50]

    # По 4 кнопки в ряд
    for i in range(0, len(weights), 4):
        row = weights[i:i+4]
        builder.row(*[
            InlineKeyboardButton(text=f"{w} кг", callback_data=f"w:{w}")
            for w in row
        ])
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()


def reps_kb() -> InlineKeyboardMarkup:
    """Быстрый выбор повторений."""
    builder = InlineKeyboardBuilder()
    reps = [8, 10, 12, 15, 20, 30]
    # По 3 кнопки в ряд
    for i in range(0, len(reps), 3):
        row = reps[i:i+3]
        builder.row(*[
            InlineKeyboardButton(text=str(r), callback_data=f"r:{r}")
            for r in row
        ])
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()


def sets_kb() -> InlineKeyboardMarkup:
    """Быстрый выбор подходов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="2", callback_data="s:2"),
        InlineKeyboardButton(text="3", callback_data="s:3"),
        InlineKeyboardButton(text="4", callback_data="s:4"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")
    )
    return builder.as_markup()


def after_log_kb(exercise_id: int, next_exercise_id: int = None, day_id: int = None) -> InlineKeyboardMarkup:
    """Клавиатура после записи подхода."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Ещё подход", callback_data=f"log:{exercise_id}")
    )
    if next_exercise_id:
        builder.row(
            InlineKeyboardButton(text="➡️ Следующее", callback_data=f"exercise:{next_exercise_id}")
        )
    if day_id:
        builder.row(
            InlineKeyboardButton(text="✅ Закончить день", callback_data="complete_day")
        )
    builder.row(
        InlineKeyboardButton(text="« К упражнению", callback_data=f"exercise:{exercise_id}")
    )
    return builder.as_markup()


def day_completed_kb(day_id: int = None, show_next: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура после завершения дня."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 Скопировать итог", callback_data="copy_summary")
    )
    if show_next and day_id:
        builder.row(
            InlineKeyboardButton(text="➡️ К следующему дню", callback_data=f"day:{day_id}")
        )
    builder.row(
        InlineKeyboardButton(text="« В меню", callback_data="back_to_main")
    )
    return builder.as_markup()

