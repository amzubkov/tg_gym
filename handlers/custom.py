import re
from datetime import date

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, ForceReply
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

import database as db

router = Router()


class CustomMode(StatesGroup):
    """Режим ввода своих упражнений."""
    waiting_for_name = State()
    waiting_for_weight = State()
    waiting_for_reps = State()


class UserCreateExercise(StatesGroup):
    """Создание упражнения пользователем."""
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_tag = State()
    waiting_for_weight_type = State()
    waiting_for_image = State()


def custom_mode_kb(has_entries: bool) -> InlineKeyboardMarkup:
    """Клавиатура режима своих упражнений."""
    builder = InlineKeyboardBuilder()
    if has_entries:
        # Если уже вводил - только кнопка завершения
        builder.row(
            InlineKeyboardButton(text="✅ Закончить день", callback_data="finish_custom")
        )
    else:
        # Если ещё не вводил - можно вернуться
        builder.row(
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")
        )
    return builder.as_markup()


def after_custom_kb() -> InlineKeyboardMarkup:
    """Клавиатура после записи (есть записи)."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Закончить день", callback_data="finish_custom")
    )
    return builder.as_markup()


def is_group_chat(chat) -> bool:
    """Проверить, что чат групповый (privacy mode)."""
    return chat.type in ("group", "supergroup")


async def send_force_reply_if_group(message: Message, text: str) -> None:
    """В группах просим отвечать на сообщение, чтобы бот получил ввод."""
    if is_group_chat(message.chat):
        await message.answer(text, reply_markup=ForceReply(selective=True))


def parse_exercise_input(text: str) -> dict | None:
    """
    Парсит упражнения:
    - "жим лежа 90кг 15х4" → силовое (вес, повторы, подходы)
    - "бег 50мин" → кардио (длительность)
    """
    text = text.strip()

    # Паттерн для времени: "бег 50мин", "ходьба 1 час"
    time_pattern = r'^(.+?)\s+(\d+(?:[.,]\d+)?)\s*(час|ч|минут|мин|м).*$'
    time_match = re.match(time_pattern, text, re.IGNORECASE)

    if time_match:
        name = time_match.group(1).strip()
        value = float(time_match.group(2).replace(',', '.'))
        unit = time_match.group(3).lower()

        if unit in ('час', 'ч'):
            duration = int(value * 60)
        else:
            duration = int(value)

        return {"type": "cardio", "name": name, "duration": duration}

    # Паттерн для силовых: "жим лежа 90кг 15х4" или "жим 90 15x4"
    strength_pattern = r'^(.+?)\s+(\d+(?:[.,]\d+)?)\s*(?:кг)?\s+(\d+)\s*(?:[xхXХ×*]\s*(\d+))?$'
    strength_match = re.match(strength_pattern, text, re.IGNORECASE)

    if strength_match:
        name = strength_match.group(1).strip()
        weight = float(strength_match.group(2).replace(',', '.'))
        reps = int(strength_match.group(3))
        sets = int(strength_match.group(4)) if strength_match.group(4) else 1
        return {"type": "strength", "name": name, "weight": weight, "reps": reps, "sets": sets}

    return None


def format_duration(minutes: int) -> str:
    """Форматировать длительность."""
    if minutes >= 60:
        hours = minutes // 60
        mins = minutes % 60
        if mins:
            return f"{hours} ч {mins} мин"
        return f"{hours} ч"
    return f"{minutes} мин"


def add_more_kb() -> InlineKeyboardMarkup:
    """Клавиатура после записи упражнения."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Ещё упражнение", callback_data="custom_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Закончить день", callback_data="finish_custom")
    )
    return builder.as_markup()


@router.callback_query(F.data == "custom_exercise")
async def start_custom_mode(callback: CallbackQuery, state: FSMContext):
    """Начать режим своих упражнений."""
    user_id = callback.from_user.id
    today = date.today().isoformat()

    # Проверяем есть ли записи за сегодня
    today_logs = await db.get_today_custom_logs(user_id, today)
    has_entries = len(today_logs) > 0

    await state.set_state(CustomMode.waiting_for_name)

    await callback.message.edit_text(
        "Напиши что сделал сегодня, например:\n"
        "<code>жим лежа 90 15х4</code> или <code>бег 1 час</code>",
        parse_mode="HTML",
        reply_markup=custom_mode_kb(has_entries)
    )
    if callback.message:
        await send_force_reply_if_group(
            callback.message,
            "Ответь на это сообщение своим упражнением."
        )
    await callback.answer()


@router.callback_query(F.data == "finish_custom")
async def finish_custom(callback: CallbackQuery, state: FSMContext):
    """Закончить ввод своих упражнений."""
    await state.clear()

    from handlers.start import get_main_text_and_kb
    text, kb = await get_main_text_and_kb(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.message(CustomMode.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка названия упражнения."""
    text = message.text.strip()
    user_id = message.from_user.id
    today = date.today().isoformat()

    # Проверяем полный формат
    result = parse_exercise_input(text)

    if result and result["type"] == "cardio":
        # Кардио - сразу сохраняем
        await db.log_custom_exercise(
            user_id=user_id,
            name=result["name"],
            date=today,
            duration_minutes=result["duration"]
        )
        await state.clear()
        await message.answer(
            f"✅ <b>{result['name']}</b> — {format_duration(result['duration'])}",
            parse_mode="HTML",
            reply_markup=add_more_kb()
        )
        return

    if result and result["type"] == "strength":
        # Силовое в одну строку - сразу сохраняем
        sets = result["sets"]
        for _ in range(sets):
            await db.log_custom_exercise(
                user_id=user_id,
                name=result["name"],
                date=today,
                weight=result["weight"],
                reps=result["reps"]
            )
        await state.clear()
        sets_text = f" × {sets} подходов" if sets > 1 else ""
        await message.answer(
            f"✅ <b>{result['name']}</b> — {result['weight']} кг × {result['reps']}{sets_text}",
            parse_mode="HTML",
            reply_markup=add_more_kb()
        )
        return

    # Только название - переходим к вводу веса
    await state.update_data(name=text)
    await state.set_state(CustomMode.waiting_for_weight)

    await message.answer(
        f"💪 <b>{text}</b>\n\n"
        f"Введи вес (кг):\n"
        f"(или 0 для упражнений без веса)",
        parse_mode="HTML",
        reply_markup=after_custom_kb()
    )
    await send_force_reply_if_group(message, "Ответь на это сообщение числом (вес).")


@router.message(CustomMode.waiting_for_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса."""
    try:
        weight = float(message.text.replace(',', '.').replace('кг', '').strip())
    except ValueError:
        await message.answer(
            "❌ Введи число (вес в кг):",
            reply_markup=after_custom_kb()
        )
        await send_force_reply_if_group(message, "Ответь на это сообщение числом (вес).")
        return

    data = await state.get_data()
    await state.update_data(weight=weight)
    await state.set_state(CustomMode.waiting_for_reps)

    await message.answer(
        f"💪 <b>{data['name']}</b> — {weight} кг\n\n"
        f"Введи повторы×подходы:\n"
        f"Например: <code>15x3</code> или <code>12</code>",
        parse_mode="HTML",
        reply_markup=after_custom_kb()
    )
    await send_force_reply_if_group(message, "Ответь на это сообщение повторами.")


@router.message(CustomMode.waiting_for_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторов и подходов."""
    text = message.text.strip().lower()

    # Парсим формат: "15x3", "15х3", "15*3", "15-3", или просто "15"
    match = re.match(r'^(\d+)\s*[xх×*\-]\s*(\d+)$', text)
    if match:
        reps = int(match.group(1))
        sets = int(match.group(2))
    else:
        try:
            reps = int(text)
            sets = 1
        except ValueError:
            await message.answer(
                "❌ Формат: <code>15x3</code> или <code>12</code>",
                parse_mode="HTML",
                reply_markup=after_custom_kb()
            )
            await send_force_reply_if_group(message, "Ответь на это сообщение повторами.")
            return

    data = await state.get_data()
    user_id = message.from_user.id
    today = date.today().isoformat()

    # Сохраняем каждый подход
    for _ in range(sets):
        await db.log_custom_exercise(
            user_id=user_id,
            name=data["name"],
            date=today,
            weight=data["weight"],
            reps=reps
        )

    await state.clear()

    sets_text = f"× {sets} подходов" if sets > 1 else ""
    await message.answer(
        f"✅ <b>{data['name']}</b> — {data['weight']} кг × {reps} {sets_text}",
        parse_mode="HTML",
        reply_markup=add_more_kb()
    )


# ==================== USER CREATE EXERCISE ====================

def user_cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены для пользователя."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_user_create")
    )
    return builder.as_markup()


def user_skip_kb(skip_callback: str) -> InlineKeyboardMarkup:
    """Кнопка пропустить для пользователя."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=skip_callback)
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_user_create")
    )
    return builder.as_markup()


def user_weight_type_kb() -> InlineKeyboardMarkup:
    """Выбор типа веса для пользователя."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ Штанга", callback_data="user_wt:100"),
        InlineKeyboardButton(text="💪 Гантели", callback_data="user_wt:10")
    )
    builder.row(
        InlineKeyboardButton(text="🤸 Без веса", callback_data="user_wt:0")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_user_create")
    )
    return builder.as_markup()


@router.callback_query(F.data == "user_create_exercise")
async def start_user_create_exercise(callback: CallbackQuery, state: FSMContext):
    """Начать создание упражнения пользователем."""
    await state.set_state(UserCreateExercise.waiting_for_name)

    await callback.message.edit_text(
        "➕ Создание упражнения\n\n"
        "Введи название упражнения:",
        reply_markup=user_cancel_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_user_create")
async def cancel_user_create(callback: CallbackQuery, state: FSMContext):
    """Отмена создания упражнения."""
    await state.clear()

    from handlers.start import get_main_text_and_kb
    text, kb = await get_main_text_and_kb(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.message(UserCreateExercise.waiting_for_name)
async def process_user_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "Название слишком короткое. Минимум 2 символа:",
            reply_markup=user_cancel_kb()
        )
        return

    await state.update_data(exercise_name=name)
    await state.set_state(UserCreateExercise.waiting_for_description)

    await message.answer(
        f"Упражнение: {name}\n\n"
        "Введи описание (или нажми Пропустить):\n"
        "Например: 3×12, техника, подсказки",
        reply_markup=user_skip_kb("user_skip_desc")
    )


@router.callback_query(UserCreateExercise.waiting_for_description, F.data == "user_skip_desc")
async def skip_user_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание."""
    await state.update_data(description=None)
    await state.set_state(UserCreateExercise.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nПопулярные теги: " + ", ".join(t["name"] for t in tags[:10])

    await callback.message.edit_text(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=user_skip_kb("user_skip_tag")
    )
    await callback.answer()


@router.message(UserCreateExercise.waiting_for_description)
async def process_user_description(message: Message, state: FSMContext):
    """Обработка описания."""
    description = message.text.strip()
    await state.update_data(description=description)
    await state.set_state(UserCreateExercise.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nПопулярные теги: " + ", ".join(t["name"] for t in tags[:10])

    await message.answer(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=user_skip_kb("user_skip_tag")
    )


@router.callback_query(UserCreateExercise.waiting_for_tag, F.data == "user_skip_tag")
async def skip_user_tag(callback: CallbackQuery, state: FSMContext):
    """Пропустить тег."""
    await state.update_data(tag=None)
    await state.set_state(UserCreateExercise.waiting_for_weight_type)

    await callback.message.edit_text(
        "Выбери тип веса для упражнения:",
        reply_markup=user_weight_type_kb()
    )
    await callback.answer()


@router.message(UserCreateExercise.waiting_for_tag)
async def process_user_tag(message: Message, state: FSMContext):
    """Обработка тега."""
    tag = message.text.strip().lower()
    await state.update_data(tag=tag)
    await state.set_state(UserCreateExercise.waiting_for_weight_type)

    await message.answer(
        f"Тег: #{tag}\n\n"
        "Выбери тип веса для упражнения:",
        reply_markup=user_weight_type_kb()
    )


@router.callback_query(UserCreateExercise.waiting_for_weight_type, F.data.startswith("user_wt:"))
async def process_user_weight_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа веса."""
    weight_type = int(callback.data.split(":")[1])
    await state.update_data(weight_type=weight_type)
    await state.set_state(UserCreateExercise.waiting_for_image)

    type_names = {0: "без веса", 10: "гантели", 100: "штанга"}
    await callback.message.edit_text(
        f"Тип веса: {type_names.get(weight_type, 'гантели')}\n\n"
        "Теперь отправь картинку упражнения (или нажми Пропустить):",
        reply_markup=user_skip_kb("user_skip_image")
    )
    await callback.answer()


@router.callback_query(UserCreateExercise.waiting_for_image, F.data == "user_skip_image")
async def skip_user_image(callback: CallbackQuery, state: FSMContext):
    """Пропустить картинку и сохранить упражнение."""
    data = await state.get_data()

    await db.create_exercise(
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=None,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10)
    )

    await state.clear()

    tag_text = f" (#{data['tag']})" if data.get("tag") else ""

    from handlers.start import get_main_text_and_kb
    text, kb = await get_main_text_and_kb(callback.from_user.id)

    await callback.message.edit_text(
        f"✅ Упражнение «{data['exercise_name']}»{tag_text} создано!\n\n" + text,
        reply_markup=kb
    )
    await callback.answer()


@router.message(UserCreateExercise.waiting_for_image, F.photo)
async def process_user_image(message: Message, state: FSMContext):
    """Обработка картинки."""
    data = await state.get_data()

    photo = message.photo[-1]
    file_id = photo.file_id

    await db.create_exercise(
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=file_id,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10)
    )

    await state.clear()

    tag_text = f" (#{data['tag']})" if data.get("tag") else ""

    from handlers.start import get_main_text_and_kb
    text, kb = await get_main_text_and_kb(message.from_user.id)

    await message.answer(
        f"✅ Упражнение «{data['exercise_name']}»{tag_text} создано!\n\n" + text,
        reply_markup=kb
    )


@router.message(UserCreateExercise.waiting_for_image)
async def wrong_user_image_format(message: Message, state: FSMContext):
    """Неправильный формат — ожидаем фото."""
    await message.answer(
        "Отправь картинку как фото, или нажми Пропустить:",
        reply_markup=user_skip_kb("user_skip_image")
    )
