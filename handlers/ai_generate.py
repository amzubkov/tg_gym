"""Генерация упражнений через AI."""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ai_service import generate_exercises, MUSCLE_GROUPS

router = Router()


class GenerateExercises(StatesGroup):
    selecting_muscles = State()
    viewing_result = State()


def muscles_kb(selected: set = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора мышц."""
    selected = selected or set()
    builder = InlineKeyboardBuilder()

    for key, name in MUSCLE_GROUPS.items():
        check = "✓ " if key in selected else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{check}{name}",
                callback_data=f"muscle:{key}"
            )
        )

    if selected:
        builder.row(
            InlineKeyboardButton(
                text="🤖 Сгенерировать",
                callback_data="do_generate"
            )
        )

    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def result_kb() -> InlineKeyboardMarkup:
    """Клавиатура после генерации."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Ещё раз", callback_data="ai_exercises")
    )
    builder.row(
        InlineKeyboardButton(text="« В меню", callback_data="back_to_main")
    )
    return builder.as_markup()


@router.callback_query(F.data == "ai_exercises")
async def start_ai_generate(callback: CallbackQuery, state: FSMContext):
    """Начать генерацию упражнений."""
    await state.set_state(GenerateExercises.selecting_muscles)
    await state.update_data(selected_muscles=set())

    await callback.message.edit_text(
        "🤖 Выбери группы мышц для тренировки:\n\n"
        "(можно выбрать несколько)",
        reply_markup=muscles_kb()
    )
    await callback.answer()


@router.callback_query(GenerateExercises.selecting_muscles, F.data.startswith("muscle:"))
async def toggle_muscle(callback: CallbackQuery, state: FSMContext):
    """Переключить выбор мышцы."""
    muscle = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_muscles", set())

    if muscle in selected:
        selected.discard(muscle)
    else:
        selected.add(muscle)

    await state.update_data(selected_muscles=selected)

    await callback.message.edit_text(
        "🤖 Выбери группы мышц для тренировки:\n\n"
        "(можно выбрать несколько)",
        reply_markup=muscles_kb(selected)
    )
    await callback.answer()


@router.callback_query(GenerateExercises.selecting_muscles, F.data == "do_generate")
async def do_generate(callback: CallbackQuery, state: FSMContext):
    """Сгенерировать упражнения."""
    data = await state.get_data()
    selected = data.get("selected_muscles", set())

    if not selected:
        await callback.answer("Выбери хотя бы одну группу мышц", show_alert=True)
        return

    # Показываем загрузку
    await callback.message.edit_text("🤖 Генерирую упражнения...")

    # Преобразуем в русские названия
    muscles_ru = [MUSCLE_GROUPS[m] for m in selected]

    # Генерируем
    result = await generate_exercises(muscles_ru)

    if result:
        await state.set_state(GenerateExercises.viewing_result)
        muscles_str = ", ".join(muscles_ru)
        await callback.message.edit_text(
            f"🤖 Упражнения на {muscles_str}:\n\n{result}",
            reply_markup=result_kb()
        )
    else:
        await callback.message.edit_text(
            "❌ Не удалось сгенерировать упражнения.\n"
            "Проверь DEEPSEEK_API_KEY в .env",
            reply_markup=result_kb()
        )

    await callback.answer()