from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from keyboards import (
    main_menu_kb, admin_menu_kb, select_program_kb,
    today_workout_kb, program_finished_kb
)
import database as db

router = Router()


async def get_main_text_and_kb(user_id: int):
    """Получить текст и клавиатуру главного меню."""
    is_admin = user_id == ADMIN_ID
    current_day = await db.get_current_day_info(user_id)

    if current_day:
        day_name = current_day["day_name"] or f"День {current_day['day_number']}"
        text = (
            f"💪 Текущая программа: {current_day['program_name']}\n"
            f"📅 Сегодня: {day_name} ({current_day['day_number']}/{current_day['total_days']})"
        )
        kb = admin_menu_kb(has_active_program=True) if is_admin else main_menu_kb(has_active_program=True)
    else:
        # Проверяем, может программа завершена
        progress = await db.get_user_progress(user_id)
        if progress and progress["is_finished"]:
            text = "🎉 Программа завершена! Выбери новую программу."
        else:
            text = "Привет! Выбери программу и записывай свои результаты."
        kb = admin_menu_kb(has_active_program=False) if is_admin else main_menu_kb(has_active_program=False)

    return text, kb


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start."""
    text, kb = await get_main_text_and_kb(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear()  # Очищаем FSM состояние
    text, kb = await get_main_text_and_kb(callback.from_user.id)

    # Если это фото — удаляем и отправляем текст
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


def format_duration(minutes: int) -> str:
    """Форматировать длительность."""
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        if mins:
            return f"{hours}ч{mins}м"
        return f"{hours}ч"
    return f"{minutes}м"


def format_activity(activity: dict) -> str:
    """Форматировать активность дня."""
    lines = []

    # Группируем по упражнениям
    exercises = {}
    cardio = {}

    # Силовые из программы
    for item in activity["workouts"]:
        name = item["name"]
        if name not in exercises:
            exercises[name] = []
        exercises[name].append(f"{item['weight']}×{item['reps']}")

    # Свои упражнения (силовые и кардио)
    for item in activity["custom"]:
        name = item["name"]
        duration = item.get("duration_minutes")
        if duration:
            # Кардио - суммируем время
            cardio[name] = cardio.get(name, 0) + duration
        else:
            # Силовое
            if name not in exercises:
                exercises[name] = []
            exercises[name].append(f"{item['weight']}×{item['reps']}")

    for name, sets in exercises.items():
        lines.append(f"• {name}: {', '.join(sets)}")

    for name, total_mins in cardio.items():
        lines.append(f"• {name}: {format_duration(total_mins)}")

    return "\n".join(lines) if lines else "—"


@router.callback_query(F.data == "my_stats")
async def show_my_stats(callback: CallbackQuery):
    """Показать статистику пользователя."""
    from datetime import date, timedelta

    user_id = callback.from_user.id
    stats = await db.get_user_stats(user_id)
    current_day = await db.get_current_day_info(user_id)

    today = date.today()
    yesterday = today - timedelta(days=1)

    today_activity = await db.get_daily_activity(user_id, today.isoformat())
    yesterday_activity = await db.get_daily_activity(user_id, yesterday.isoformat())

    text = f"📊 Твоя статистика:\n\n"

    # Прогресс по программе
    if current_day:
        completed = current_day["day_number"] - 1  # текущий день ещё не сделан
        total = current_day["total_days"]
        progress = "✅" * completed + "⬜" * (total - completed)
        text += f"📋 {current_day['program_name']}\n"
        text += f"{progress} ({completed}/{total})\n\n"

    text += f"В этом месяце: {stats['month_workouts']} тренировок\n"
    if stats['days_ago'] is not None:
        if stats['days_ago'] == 0:
            text += f"Последний раз: сегодня\n\n"
        elif stats['days_ago'] == 1:
            text += f"Последний раз: вчера\n\n"
        else:
            text += f"Последний раз: {stats['days_ago']} дн. назад\n\n"
    else:
        text += f"Ещё нет тренировок\n\n"

    text += f"📅 Сегодня ({today.strftime('%d.%m')}):\n"
    text += format_activity(today_activity) + "\n\n"

    text += f"📅 Вчера ({yesterday.strftime('%d.%m')}):\n"
    text += format_activity(yesterday_activity)

    is_admin = user_id == ADMIN_ID
    has_active = current_day is not None
    kb = admin_menu_kb(has_active_program=has_active) if is_admin else main_menu_kb(has_active_program=has_active)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass  # Сообщение не изменилось
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery):
    """Отмена текущего действия."""
    text, kb = await get_main_text_and_kb(callback.from_user.id)
    await callback.message.edit_text(f"Действие отменено.\n\n{text}", reply_markup=kb)
    await callback.answer()


# ==================== ВЫБОР ПРОГРАММЫ ====================

@router.callback_query(F.data == "select_program")
async def select_program(callback: CallbackQuery):
    """Выбор программы для начала."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Пока нет программ", show_alert=True)
        return

    await callback.message.edit_text(
        "📋 Выбери программу для начала тренировок:\n\n"
        "⚠️ Если у тебя уже есть активная программа, она будет сброшена!",
        reply_markup=select_program_kb(programs)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("start_program:"))
async def start_program(callback: CallbackQuery):
    """Начать программу."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)

    if not program:
        await callback.answer("Программа не найдена", show_alert=True)
        return

    # Проверяем что в программе есть дни
    days = await db.get_days_by_program(program_id)
    if not days:
        await callback.answer("В программе нет дней!", show_alert=True)
        return

    # Устанавливаем программу
    await db.set_user_program(callback.from_user.id, program_id)

    # Показываем текущий день
    current_day = await db.get_current_day_info(callback.from_user.id)
    day_name = current_day["day_name"] or f"День {current_day['day_number']}"

    await callback.message.edit_text(
        f"✅ Программа «{program['name']}» выбрана!\n\n"
        f"📅 Сегодня: {day_name}\n"
        f"Прогресс: {current_day['day_number']}/{current_day['total_days']}",
        reply_markup=today_workout_kb(current_day["day_id"])
    )
    await callback.answer()


# ==================== ТЕКУЩАЯ ТРЕНИРОВКА ====================

@router.callback_query(F.data == "today_workout")
async def today_workout(callback: CallbackQuery):
    """Показать текущую тренировку."""
    current_day = await db.get_current_day_info(callback.from_user.id)

    if not current_day:
        await callback.answer("Нет активной программы", show_alert=True)
        return

    day_name = current_day["day_name"] or f"День {current_day['day_number']}"

    await callback.message.edit_text(
        f"💪 {current_day['program_name']}\n\n"
        f"📅 {day_name}\n"
        f"Прогресс: {current_day['day_number']}/{current_day['total_days']}",
        reply_markup=today_workout_kb(current_day["day_id"])
    )
    await callback.answer()


@router.callback_query(F.data == "complete_day")
async def complete_day(callback: CallbackQuery):
    """Закончить текущий день."""
    from datetime import date

    user_id = callback.from_user.id
    current_day = await db.get_current_day_info(user_id)

    if not current_day:
        await callback.answer("Нет активной программы", show_alert=True)
        return

    # Получаем сводку дня до завершения
    today = date.today().isoformat()
    activity = await db.get_daily_activity(user_id, today)

    # Формируем сводку
    day_name = current_day["day_name"] or f"День {current_day['day_number']}"
    header = f"{current_day['program_name']} - {day_name}"

    summary_lines = [header, ""]

    # Упражнения из программы - группируем по названию
    exercises = {}
    for w in activity["workouts"]:
        name = w["name"]
        if name not in exercises:
            exercises[name] = {"weight": w["weight"], "reps": w["reps"], "sets": 0}
        exercises[name]["sets"] += 1

    # Свои упражнения
    for c in activity["custom"]:
        name = c["name"]
        if c.get("duration_minutes"):
            # Кардио
            if name not in exercises:
                exercises[name] = {"duration": 0}
            exercises[name]["duration"] = exercises[name].get("duration", 0) + c["duration_minutes"]
        else:
            # Силовое
            if name not in exercises:
                exercises[name] = {"weight": c["weight"], "reps": c["reps"], "sets": 0}
            exercises[name]["sets"] += 1

    # Форматируем с номерами
    for i, (name, data) in enumerate(exercises.items(), 1):
        if "duration" in data:
            summary_lines.append(f"{i}. {name}: {data['duration']}мин")
        else:
            summary_lines.append(f"{i}. {name}: {data['weight']}кг {data['reps']}×{data['sets']}")

    summary = "\n".join(summary_lines) if len(summary_lines) > 2 else "Нет записей"
    # Форматируем для копирования
    copyable_summary = f"```\n{summary}\n```"

    # Завершаем день
    is_finished = await db.complete_day(user_id)

    if is_finished:
        # Программа завершена
        await callback.message.edit_text(
            f"🎉 Программа «{current_day['program_name']}» завершена!\n\n"
            f"📝 Итог дня:\n{copyable_summary}\n\n"
            f"Ты прошёл все {current_day['total_days']} дней!",
            parse_mode="Markdown",
            reply_markup=program_finished_kb()
        )
    else:
        # Переходим к следующему дню
        new_day = await db.get_current_day_info(user_id)
        day_name = new_day["day_name"] or f"День {new_day['day_number']}"

        await callback.message.edit_text(
            f"✅ День завершён!\n\n"
            f"📝 Итог:\n{copyable_summary}\n\n"
            f"📅 Следующий: {day_name} ({new_day['day_number']}/{new_day['total_days']})",
            parse_mode="Markdown",
            reply_markup=today_workout_kb(new_day["day_id"])
        )

    await callback.answer()