from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards import cancel_kb, back_to_exercise_kb
import database as db

router = Router()


class LogWorkout(StatesGroup):
    """Состояния для записи тренировки."""
    waiting_for_weight = State()
    waiting_for_reps = State()
    waiting_for_set = State()


@router.callback_query(F.data.startswith("log:"))
async def start_logging(callback: CallbackQuery, state: FSMContext):
    """Начать запись подхода."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    # Получаем последний подход сегодня для определения номера
    user_id = callback.from_user.id
    today = date.today().isoformat()

    # Сохраняем данные в состояние
    await state.update_data(
        exercise_id=exercise_id,
        exercise_name=exercise["name"],
        date=today
    )

    # Получаем последнюю тренировку для подсказки
    last_workout = await db.get_last_workout(user_id, exercise_id)
    hint = ""
    if last_workout:
        last = last_workout[0]
        hint = f"\n\n💡 В прошлый раз: {last['weight']} кг"

    await state.set_state(LogWorkout.waiting_for_weight)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"💪 {exercise['name']}\n\n"
        f"Введи вес (кг):{hint}",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(LogWorkout.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса."""
    try:
        # Поддержка запятой и точки
        weight_text = message.text.replace(",", ".")
        weight = float(weight_text)
        if weight < 0 or weight > 1000:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи корректный вес (число от 0 до 1000):",
            reply_markup=cancel_kb()
        )
        return

    await state.update_data(weight=weight)
    await state.set_state(LogWorkout.waiting_for_reps)

    data = await state.get_data()
    await message.answer(
        f"💪 {data['exercise_name']}\n"
        f"Вес: {weight} кг\n\n"
        f"Введи количество повторений:",
        reply_markup=cancel_kb()
    )


@router.message(LogWorkout.waiting_for_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений."""
    try:
        reps = int(message.text)
        if reps < 1 or reps > 1000:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи корректное количество повторений (число от 1 до 1000):",
            reply_markup=cancel_kb()
        )
        return

    await state.update_data(reps=reps)
    await state.set_state(LogWorkout.waiting_for_set)

    data = await state.get_data()
    await message.answer(
        f"💪 {data['exercise_name']}\n"
        f"Вес: {data['weight']} кг\n"
        f"Повторений: {reps}\n\n"
        f"Введи номер подхода (или отправь 0 для авто):",
        reply_markup=cancel_kb()
    )


@router.message(LogWorkout.waiting_for_set)
async def process_set(message: Message, state: FSMContext):
    """Обработка номера подхода и сохранение."""
    try:
        set_num = int(message.text)
        if set_num < 0 or set_num > 100:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи корректный номер подхода (0-100):",
            reply_markup=cancel_kb()
        )
        return

    data = await state.get_data()
    user_id = message.from_user.id

    # Если 0 — автоматический номер подхода
    if set_num == 0:
        # Считаем подходы за сегодня
        from aiosqlite import connect
        from config import DATABASE_PATH
        async with connect(DATABASE_PATH) as conn:
            cursor = await conn.execute(
                """SELECT COUNT(*) FROM workout_logs
                   WHERE user_id = ? AND exercise_id = ? AND date = ?""",
                (user_id, data["exercise_id"], data["date"])
            )
            count = (await cursor.fetchone())[0]
            set_num = count + 1

    # Сохраняем
    await db.log_workout(
        user_id=user_id,
        exercise_id=data["exercise_id"],
        weight=data["weight"],
        reps=data["reps"],
        set_num=set_num,
        date=data["date"]
    )

    await state.clear()

    await message.answer(
        f"✅ Записано!\n\n"
        f"💪 {data['exercise_name']}\n"
        f"Подход {set_num}: {data['weight']} кг × {data['reps']} раз",
        reply_markup=back_to_exercise_kb(data["exercise_id"])
    )