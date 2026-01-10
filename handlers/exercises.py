from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto

from keyboards import programs_kb, days_kb, exercises_kb, exercise_detail_kb
import database as db

router = Router()


@router.callback_query(F.data == "programs")
async def show_programs(callback: CallbackQuery):
    """Показать список программ."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Пока нет программ", show_alert=True)
        return

    await callback.message.edit_text(
        "Выбери программу:",
        reply_markup=programs_kb(programs)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("program:"))
async def show_program_days(callback: CallbackQuery):
    """Показать дни программы."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)

    if not program:
        await callback.answer("Программа не найдена", show_alert=True)
        return

    days = await db.get_days_by_program(program_id)

    if not days:
        await callback.answer("В программе пока нет дней", show_alert=True)
        return

    await callback.message.edit_text(
        f"📋 {program['name']}\n\nВыбери день:",
        reply_markup=days_kb(days, program_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("day:"))
async def show_day_exercises(callback: CallbackQuery):
    """Показать упражнения дня."""
    day_id = int(callback.data.split(":")[1])
    day = await db.get_day(day_id)

    if not day:
        await callback.answer("День не найден", show_alert=True)
        return

    program = await db.get_program(day["program_id"])
    exercises = await db.get_exercises_by_day(day_id)

    if not exercises:
        await callback.answer("В этом дне пока нет упражнений", show_alert=True)
        return

    day_name = day["name"] if day["name"] else f"День {day['day_number']}"

    await callback.message.edit_text(
        f"📋 {program['name']} — {day_name}\n\nВыбери упражнение:",
        reply_markup=exercises_kb(exercises, day_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_days:"))
async def back_to_days(callback: CallbackQuery):
    """Вернуться к списку дней."""
    day_id = int(callback.data.split(":")[1])
    day = await db.get_day(day_id)

    if day:
        program_id = day["program_id"]
        program = await db.get_program(program_id)
        days = await db.get_days_by_program(program_id)

        await callback.message.edit_text(
            f"📋 {program['name']}\n\nВыбери день:",
            reply_markup=days_kb(days, program_id)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("exercise:"))
async def show_exercise(callback: CallbackQuery):
    """Показать упражнение с картинкой."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    day = await db.get_day(exercise["day_id"])

    # Получаем последнюю тренировку
    user_id = callback.from_user.id
    last_workout = await db.get_last_workout(user_id, exercise_id)

    text = f"💪 {exercise['name']}\n"
    if exercise["description"]:
        text += f"\n{exercise['description']}\n"

    if last_workout:
        text += "\n📊 Последняя тренировка:\n"
        for log in last_workout:
            text += f"  Подход {log['set_num']}: {log['weight']} кг × {log['reps']} раз\n"

    kb = exercise_detail_kb(exercise_id, exercise["day_id"])

    # Если есть картинка — отправляем фото
    if exercise["image_file_id"]:
        try:
            # Удаляем старое сообщение и отправляем фото
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=exercise["image_file_id"],
                caption=text,
                reply_markup=kb
            )
        except Exception:
            # Если не получилось — просто текст
            await callback.message.edit_text(text, reply_markup=kb)
    else:
        # Если это было фото — удаляем и отправляем текст
        try:
            if callback.message.photo:
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=kb)
            else:
                await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.edit_text(text, reply_markup=kb)

    await callback.answer()