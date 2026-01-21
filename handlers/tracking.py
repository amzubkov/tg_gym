import re
from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import cancel_kb, weight_kb, reps_kb, sets_kb, after_log_kb, date_select_kb, exercise_select_kb
import database as db

router = Router()


class LogWorkout(StatesGroup):
    """Состояния для записи тренировки."""
    waiting_for_date = State()
    waiting_for_weight = State()
    waiting_for_reps = State()
    waiting_for_sets = State()


class AddRecord(StatesGroup):
    """Состояния для добавления записи (из меню)."""
    waiting_for_date = State()


@router.callback_query(F.data.startswith("log:"))
async def start_logging(callback: CallbackQuery, state: FSMContext):
    """Начать запись подхода.

    Формат callback_data: log:{exercise_id}:{day_id}
    day_id может быть 0 если упражнение открыто не из дня.
    """
    parts = callback.data.split(":")
    exercise_id = int(parts[1])
    day_id = int(parts[2]) if len(parts) > 2 else 0

    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    # Если day_id=0, пытаемся найти первый день с этим упражнением
    if day_id == 0:
        exercise_days = await db.get_exercise_days(exercise_id)
        if exercise_days:
            day_id = exercise_days[0]["id"]

    # Находим следующее и первое упражнение (только если есть контекст дня)
    next_exercise_id = None
    first_exercise_id = None
    if day_id:
        exercises = await db.get_exercises_by_day(day_id)
        if exercises:
            first_exercise_id = exercises[0]["id"]
        for i, ex in enumerate(exercises):
            if ex["id"] == exercise_id and i + 1 < len(exercises):
                next_exercise_id = exercises[i + 1]["id"]
                break

    # weight_type: 0=без веса, 10=гантели, 100=штанга
    weight_type = exercise["weight_type"] if "weight_type" in exercise.keys() else 10

    await state.update_data(
        exercise_id=exercise_id,
        exercise_name=exercise["name"],
        day_id=day_id,
        next_exercise_id=next_exercise_id,
        first_exercise_id=first_exercise_id,
        weight_type=weight_type
    )

    # Спрашиваем дату
    await state.set_state(LogWorkout.waiting_for_date)
    await callback.message.answer(
        f"💪 {exercise['name']}\n\n"
        f"За какую дату записать?",
        reply_markup=date_select_kb()
    )
    await callback.answer()


async def proceed_to_weight(message_or_callback, state: FSMContext, user_id: int):
    """Перейти к вводу веса после выбора даты."""
    data = await state.get_data()
    exercise_name = data["exercise_name"]
    exercise_id = data["exercise_id"]
    weight_type = data["weight_type"]

    # Если weight_type=0, пропускаем шаг с весом
    if weight_type == 0:
        await state.update_data(weight=0)
        await state.set_state(LogWorkout.waiting_for_reps)
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.message.answer(
                f"💪 {exercise_name}\n\n"
                f"Выбери повторения:",
                reply_markup=reps_kb()
            )
        else:
            await message_or_callback.answer(
                f"💪 {exercise_name}\n\n"
                f"Выбери повторения:",
                reply_markup=reps_kb()
            )
    else:
        # Получаем последнюю тренировку для подсказки
        last_workout = await db.get_last_workout(user_id, exercise_id)
        hint = ""
        if last_workout:
            last = last_workout[0]
            hint = f"\n\n💡 В прошлый раз: {last['weight']} кг × {last['reps']}"

        await state.set_state(LogWorkout.waiting_for_weight)
        if hasattr(message_or_callback, 'message'):
            await message_or_callback.message.answer(
                f"💪 {exercise_name}\n\n"
                f"Выбери вес (кг) или введи свой:{hint}",
                reply_markup=weight_kb(weight_type)
            )
        else:
            await message_or_callback.answer(
                f"💪 {exercise_name}\n\n"
                f"Выбери вес (кг) или введи свой:{hint}",
                reply_markup=weight_kb(weight_type)
            )


@router.callback_query(F.data.startswith("date:"))
async def select_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для записи."""
    from datetime import timedelta

    date_choice = callback.data.split(":")[1]

    if date_choice == "today":
        selected_date = date.today().isoformat()
        await state.update_data(date=selected_date)
        await proceed_to_weight(callback, state, callback.from_user.id)
        await callback.answer()
    elif date_choice == "yesterday":
        selected_date = (date.today() - timedelta(days=1)).isoformat()
        await state.update_data(date=selected_date)
        await proceed_to_weight(callback, state, callback.from_user.id)
        await callback.answer()
    elif date_choice == "custom":
        await state.set_state(LogWorkout.waiting_for_date)
        await callback.message.answer(
            "Введи дату в формате ДД.ММ или ДД.ММ.ГГГГ:",
            reply_markup=cancel_kb()
        )
        await callback.answer()


@router.message(LogWorkout.waiting_for_date)
async def process_custom_date(message: Message, state: FSMContext):
    """Обработка ввода произвольной даты."""
    text = message.text.strip()

    # Парсим дату
    try:
        parts = text.split(".")
        if len(parts) == 2:
            day, month = int(parts[0]), int(parts[1])
            year = date.today().year
        elif len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
        else:
            raise ValueError("Invalid format")

        selected_date = date(year, month, day)

        # Проверяем что дата не в будущем
        if selected_date > date.today():
            await message.answer("❌ Нельзя записать тренировку в будущем. Попробуй ещё раз:")
            return

        await state.update_data(date=selected_date.isoformat())
        await proceed_to_weight(message, state, message.from_user.id)

    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат даты. Введи в формате ДД.ММ или ДД.ММ.ГГГГ:")


# ==================== ВЕС ====================

def format_weight(weight: float) -> str:
    """Форматирует вес без .0 для целых чисел."""
    return f"{int(weight)}" if weight == int(weight) else f"{weight}"


@router.callback_query(LogWorkout.waiting_for_weight, F.data.startswith("w:"))
async def quick_weight(callback: CallbackQuery, state: FSMContext):
    """Быстрый выбор веса."""
    weight = float(callback.data.split(":")[1])
    await state.update_data(weight=weight)
    await state.set_state(LogWorkout.waiting_for_reps)

    data = await state.get_data()
    await callback.message.edit_text(
        f"💪 {data['exercise_name']} — {format_weight(weight)}кг\n\n"
        f"Выбери повторения:",
        reply_markup=reps_kb()
    )
    await callback.answer()


@router.message(LogWorkout.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса (ручной ввод)."""
    data = await state.get_data()
    weight_type = data.get("weight_type", 10)

    try:
        weight_text = message.text.replace(",", ".")
        weight = float(weight_text)
        if weight < 0 or weight > 1000:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи корректный вес (число от 0 до 1000):",
            reply_markup=weight_kb(weight_type)
        )
        return

    await state.update_data(weight=weight)
    await state.set_state(LogWorkout.waiting_for_reps)

    await message.answer(
        f"💪 {data['exercise_name']} — {format_weight(weight)}кг\n\n"
        f"Выбери повторения:",
        reply_markup=reps_kb()
    )


# ==================== ПОВТОРЕНИЯ ====================

@router.callback_query(LogWorkout.waiting_for_reps, F.data.startswith("r:"))
async def quick_reps(callback: CallbackQuery, state: FSMContext):
    """Быстрый выбор повторений."""
    reps = int(callback.data.split(":")[1])
    await state.update_data(reps=reps)
    await state.set_state(LogWorkout.waiting_for_sets)

    data = await state.get_data()
    await callback.message.edit_text(
        f"💪 {data['exercise_name']} — {format_weight(data['weight'])}кг ×{reps}\n\n"
        f"Сколько подходов?",
        reply_markup=sets_kb()
    )
    await callback.answer()


@router.message(LogWorkout.waiting_for_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений (ручной ввод)."""
    try:
        reps = int(message.text.strip())
        if reps < 1 or reps > 1000:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи число повторений (1-1000):",
            reply_markup=reps_kb()
        )
        return

    await state.update_data(reps=reps)
    await state.set_state(LogWorkout.waiting_for_sets)

    data = await state.get_data()
    await message.answer(
        f"💪 {data['exercise_name']} — {format_weight(data['weight'])}кг ×{reps}\n\n"
        f"Сколько подходов?",
        reply_markup=sets_kb()
    )


# ==================== ПОДХОДЫ ====================

@router.callback_query(LogWorkout.waiting_for_sets, F.data.startswith("s:"))
async def quick_sets(callback: CallbackQuery, state: FSMContext):
    """Быстрый выбор подходов."""
    sets = int(callback.data.split(":")[1])
    await save_workout(callback.message, state, sets, is_callback=True)
    await callback.answer()


@router.message(LogWorkout.waiting_for_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов (ручной ввод)."""
    try:
        sets = int(message.text.strip())
        if sets < 1 or sets > 20:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи число подходов (1-20):",
            reply_markup=sets_kb()
        )
        return

    await save_workout(message, state, sets, is_callback=False)


async def save_workout(message, state: FSMContext, sets: int, is_callback: bool):
    """Сохранить тренировку."""
    data = await state.get_data()
    user_id = message.chat.id

    # Получаем текущее количество подходов
    current_count = await db.get_workout_sets_count(
        user_id, data["exercise_id"], data["date"]
    )

    # Сохраняем каждый подход
    for i in range(sets):
        set_num = current_count + i + 1
        await db.log_workout(
            user_id=user_id,
            exercise_id=data["exercise_id"],
            weight=data["weight"],
            reps=data["reps"],
            set_num=set_num,
            date=data["date"]
        )

    await state.clear()

    sets_text = f"×{sets}" if sets > 1 else ""
    result_text = (
        f"✅ <b>{data['exercise_name']}</b>\n"
        f"{format_weight(data['weight'])}кг {data['reps']}{sets_text}"
    )

    kb = after_log_kb(
        exercise_id=data["exercise_id"],
        next_exercise_id=data.get("next_exercise_id"),
        day_id=data.get("day_id"),
        first_exercise_id=data.get("first_exercise_id")
    )

    if is_callback:
        await message.edit_text(result_text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(result_text, parse_mode="HTML", reply_markup=kb)


# ==================== ДОБАВИТЬ ЗАПИСЬ (из меню) ====================

@router.callback_query(F.data == "add_record")
async def add_record_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление записи — выбор даты."""
    await state.clear()
    await callback.message.edit_text(
        "📝 Добавить запись\n\n"
        "За какую дату?",
        reply_markup=date_select_kb(for_record=True)
    )
    await callback.answer()


async def show_exercises_for_record(message, state: FSMContext, date_label: str):
    """Показать список упражнений для записи."""
    exercises = await db.get_all_exercises()
    if not exercises:
        from keyboards import cancel_kb
        await message.edit_text(
            "В библиотеке пока нет упражнений.\n"
            "Сначала создай упражнение.",
            reply_markup=cancel_kb()
        )
        return

    await message.edit_text(
        f"📅 {date_label}\n\n"
        f"Выбери упражнение:",
        reply_markup=exercise_select_kb(exercises)
    )


@router.callback_query(F.data.startswith("rec_date:"))
async def add_record_date(callback: CallbackQuery, state: FSMContext):
    """Выбор даты для записи."""
    from datetime import timedelta

    date_choice = callback.data.split(":")[1]

    if date_choice == "today":
        selected_date = date.today().isoformat()
        await state.update_data(record_date=selected_date)
        await show_exercises_for_record(callback.message, state, "Сегодня")
        await callback.answer()
    elif date_choice == "yesterday":
        selected_date = (date.today() - timedelta(days=1)).isoformat()
        await state.update_data(record_date=selected_date)
        await show_exercises_for_record(callback.message, state, "Вчера")
        await callback.answer()
    elif date_choice == "custom":
        await state.set_state(AddRecord.waiting_for_date)
        await callback.message.edit_text(
            "Введи дату в формате ДД.ММ или ДД.ММ.ГГГГ:",
            reply_markup=cancel_kb()
        )
        await callback.answer()


@router.message(AddRecord.waiting_for_date)
async def add_record_custom_date(message: Message, state: FSMContext):
    """Ввод произвольной даты для записи."""
    text = message.text.strip()

    try:
        parts = text.split(".")
        if len(parts) == 2:
            day, month = int(parts[0]), int(parts[1])
            year = date.today().year
        elif len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
        else:
            raise ValueError("Invalid format")

        selected_date = date(year, month, day)

        if selected_date > date.today():
            await message.answer("❌ Нельзя записать тренировку в будущем. Попробуй ещё раз:")
            return

        await state.update_data(record_date=selected_date.isoformat())
        await state.set_state(None)

        # Показываем список упражнений
        exercises = await db.get_all_exercises()
        if not exercises:
            await message.answer(
                "В библиотеке пока нет упражнений.\n"
                "Сначала создай упражнение.",
                reply_markup=cancel_kb()
            )
            return

        await message.answer(
            f"📅 {selected_date.strftime('%d.%m.%Y')}\n\n"
            f"Выбери упражнение:",
            reply_markup=exercise_select_kb(exercises)
        )

    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат даты. Введи в формате ДД.ММ или ДД.ММ.ГГГГ:")


@router.callback_query(F.data.startswith("rec_ex:"))
async def add_record_exercise(callback: CallbackQuery, state: FSMContext):
    """Выбор упражнения из библиотеки — переход к записи."""
    exercise_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    record_date = data.get("record_date", date.today().isoformat())

    exercise = await db.get_exercise(exercise_id)
    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    weight_type = exercise["weight_type"] if "weight_type" in exercise.keys() else 10

    await state.update_data(
        exercise_id=exercise_id,
        exercise_name=exercise["name"],
        day_id=0,
        next_exercise_id=None,
        first_exercise_id=None,
        weight_type=weight_type,
        date=record_date
    )

    # Переходим к вводу веса
    user_id = callback.from_user.id

    if weight_type == 0:
        await state.update_data(weight=0)
        await state.set_state(LogWorkout.waiting_for_reps)
        await callback.message.edit_text(
            f"💪 {exercise['name']}\n\n"
            f"Выбери повторения:",
            reply_markup=reps_kb()
        )
    else:
        last_workout = await db.get_last_workout(user_id, exercise_id)
        hint = ""
        if last_workout:
            last = last_workout[0]
            hint = f"\n\n💡 В прошлый раз: {last['weight']} кг × {last['reps']}"

        await state.set_state(LogWorkout.waiting_for_weight)
        await callback.message.edit_text(
            f"💪 {exercise['name']}\n\n"
            f"Выбери вес (кг) или введи свой:{hint}",
            reply_markup=weight_kb(weight_type)
        )

    await callback.answer()