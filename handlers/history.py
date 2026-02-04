from aiogram import Router, F
from aiogram.types import CallbackQuery
from collections import defaultdict

from keyboards import back_to_exercise_kb
import database as db

router = Router()


@router.callback_query(F.data.startswith("history:"))
async def show_exercise_history(callback: CallbackQuery):
    """Показать историю упражнения."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    user_id = callback.from_user.id
    history = await db.get_exercise_history(user_id, exercise_id, limit=50)

    if not history:
        await callback.answer("История пуста", show_alert=True)
        return

    # Группируем по датам
    by_date = defaultdict(list)
    for log in history:
        by_date[log["date"]].append(log)

    text = f"📈 История: {exercise['name']}\n\n"

    # Показываем последние 5 тренировок
    dates = sorted(by_date.keys(), reverse=True)[:5]

    for d in dates:
        logs = sorted(by_date[d], key=lambda x: x["set_num"])
        text += f"📅 {d}\n"
        for log in logs:
            text += f"  {log['set_num']}) {log['weight']} кг × {log['reps']}\n"
        text += "\n"

    # Статистика прогресса
    if len(dates) >= 2:
        # Максимальный вес первой и последней тренировки
        first_date = dates[-1]
        last_date = dates[0]

        first_max = max(log["weight"] for log in by_date[first_date])
        last_max = max(log["weight"] for log in by_date[last_date])

        if last_max > first_max:
            diff = last_max - first_max
            text += f"📊 Прогресс: +{diff:.1f} кг с первой тренировки!"
        elif last_max == first_max:
            text += f"📊 Стабильный вес: {last_max} кг"

    try:
        if callback.message.photo or callback.message.animation:
            await callback.message.delete()
            await callback.message.answer(
                text,
                reply_markup=back_to_exercise_kb(exercise_id)
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=back_to_exercise_kb(exercise_id)
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=back_to_exercise_kb(exercise_id)
        )

    await callback.answer()