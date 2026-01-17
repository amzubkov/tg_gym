from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto

from keyboards import (
    programs_kb, days_kb, exercises_kb, exercise_detail_kb,
    all_workouts_kb, tags_kb, tag_exercises_kb, exercise_from_tag_kb
)
import database as db

router = Router()


@router.callback_query(F.data == "all_workouts")
async def show_all_workouts(callback: CallbackQuery):
    """Подменю 'Все тренировки'."""
    await callback.message.edit_text(
        "📚 Все тренировки\n\nВыбери способ просмотра:",
        reply_markup=all_workouts_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "tags_menu")
async def show_tags_menu(callback: CallbackQuery):
    """Показать список тегов."""
    tags = await db.get_all_tags()

    if not tags:
        await callback.answer("Пока нет тегов", show_alert=True)
        return

    await callback.message.edit_text(
        "🏷 Выбери тег:",
        reply_markup=tags_kb(tags)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tag:"))
async def show_tag_exercises(callback: CallbackQuery):
    """Показать упражнения по тегу."""
    tag_name = callback.data.split(":", 1)[1]

    exercises = await db.get_exercises_by_tag(tag_name)

    if not exercises:
        await callback.answer("Нет упражнений с этим тегом", show_alert=True)
        return

    await callback.message.edit_text(
        f"🏷 #{tag_name}\n\nУпражнения:",
        reply_markup=tag_exercises_kb(exercises, tag_name)
    )
    await callback.answer()


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
    text = f"📋 {program['name']} — {day_name}\n\nВыбери упражнение:"
    kb = exercises_kb(exercises, day_id)

    # Если текущее сообщение — фото, удаляем и отправляем текст
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)
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
    """Показать упражнение с картинкой.

    Форматы callback_data:
    - exercise:{id}:{day_id} - обычный просмотр из дня
    - exercise:{id}:0:tag:{tag_name} - просмотр из списка по тегу
    """
    from config import ADMIN_ID

    parts = callback.data.split(":")
    exercise_id = int(parts[1])
    day_id = int(parts[2]) if len(parts) > 2 else 0

    # Если это из тегов — запоминаем для кнопки "назад"
    from_tag = None
    if len(parts) > 4 and parts[3] == "tag":
        from_tag = parts[4]

    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    # Если day_id=0, пытаемся найти первый день с этим упражнением
    if day_id == 0:
        exercise_days = await db.get_exercise_days(exercise_id)
        if exercise_days:
            day_id = exercise_days[0]["id"]

    # Находим следующее упражнение (только если есть контекст дня)
    next_exercise_id = None
    if day_id:
        exercises = await db.get_exercises_by_day(day_id)
        for i, ex in enumerate(exercises):
            if ex["id"] == exercise_id and i + 1 < len(exercises):
                next_exercise_id = exercises[i + 1]["id"]
                break

    # Получаем последние 2 тренировки
    user_id = callback.from_user.id
    last_workouts = await db.get_last_workouts(user_id, exercise_id, limit=2)

    text = f"💪 {exercise['name']}\n"

    # Показываем теги
    if "tag" in exercise.keys() and exercise["tag"]:
        tags = [t.strip() for t in exercise["tag"].split(",") if t.strip()]
        if tags:
            text += "🏷 " + " ".join(f"#{t}" for t in tags) + "\n"

    if exercise["description"]:
        text += f"\n{exercise['description']}\n"

    if last_workouts:
        from datetime import date as dt_date
        text += "\n📊 История:\n"

        for workout in last_workouts:
            # Форматируем дату
            try:
                d = dt_date.fromisoformat(workout["date"])
                date_str = d.strftime("%d.%m")
            except:
                date_str = workout["date"]

            # Группируем одинаковые подходы (вес × повторения)
            groups = {}
            for log in workout["logs"]:
                key = (log["weight"], log["reps"])
                groups[key] = groups.get(key, 0) + 1

            # Форматируем подходы в одну строку
            sets_parts = []
            for (weight, reps), count in groups.items():
                weight_str = f"{int(weight)}" if weight == int(weight) else f"{weight}"
                sets_str = f"×{count}" if count > 1 else ""
                sets_parts.append(f"{weight_str}кг ×{reps}{sets_str}")

            text += f"  {date_str}: {', '.join(sets_parts)}\n"

    is_admin = user_id == ADMIN_ID

    # Если из тегов — используем специальную клавиатуру
    if from_tag:
        kb = exercise_from_tag_kb(exercise_id, day_id, from_tag, is_admin=is_admin)
    else:
        kb = exercise_detail_kb(exercise_id, day_id, is_admin=is_admin, next_exercise_id=next_exercise_id)

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