from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import BaseFilter

from config import ADMIN_ID
from keyboards import (
    admin_panel_kb, cancel_kb, skip_kb,
    programs_kb, days_kb, admin_menu_kb
)
import database as db

router = Router()


class IsAdmin(BaseFilter):
    """Фильтр для проверки админа."""
    async def __call__(self, event) -> bool:
        user_id = event.from_user.id if hasattr(event, 'from_user') else None
        return user_id == ADMIN_ID


# Применяем фильтр ко всему роутеру
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ==================== STATES ====================

class AddProgram(StatesGroup):
    waiting_for_name = State()


class AddDay(StatesGroup):
    waiting_for_program = State()
    waiting_for_number = State()
    waiting_for_name = State()


class AddExercise(StatesGroup):
    waiting_for_program = State()
    waiting_for_day = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_tag = State()
    waiting_for_weight_type = State()
    waiting_for_image = State()


# ==================== ADMIN MENU ====================

@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery):
    """Показать панель админа."""
    await callback.message.edit_text(
        "⚙️ Панель управления\n\n"
        "Здесь можно добавлять программы, дни и упражнения.",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


# ==================== ADD PROGRAM ====================

@router.callback_query(F.data == "add_program")
async def start_add_program(callback: CallbackQuery, state: FSMContext):
    """Начать добавление программы."""
    await state.set_state(AddProgram.waiting_for_name)

    await callback.message.edit_text(
        "➕ Добавление программы\n\n"
        "Введи название программы (например: Зубкова, PPL, Full Body):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AddProgram.waiting_for_name)
async def process_program_name(message: Message, state: FSMContext):
    """Сохранить программу."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "Название слишком короткое. Минимум 2 символа:",
            reply_markup=cancel_kb()
        )
        return

    try:
        await db.create_program(name)
        await state.clear()
        await message.answer(
            f"✅ Программа «{name}» создана!",
            reply_markup=admin_panel_kb()
        )
    except Exception as e:
        await message.answer(
            f"Ошибка: программа с таким именем уже существует.",
            reply_markup=cancel_kb()
        )


# ==================== ADD DAY ====================

@router.callback_query(F.data == "add_day")
async def start_add_day(callback: CallbackQuery, state: FSMContext):
    """Начать добавление дня."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Сначала создай программу!", show_alert=True)
        return

    await state.set_state(AddDay.waiting_for_program)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"select_program_day:{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))

    await callback.message.edit_text(
        "➕ Добавление дня\n\n"
        "Выбери программу:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(AddDay.waiting_for_program, F.data.startswith("select_program_day:"))
async def select_program_for_day(callback: CallbackQuery, state: FSMContext):
    """Выбор программы для дня."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)

    await state.update_data(program_id=program_id, program_name=program["name"])
    await state.set_state(AddDay.waiting_for_number)

    # Показываем существующие дни
    days = await db.get_days_by_program(program_id)
    existing = ""
    if days:
        existing = "\n\nУже есть дни: " + ", ".join(str(d["day_number"]) for d in days)

    await callback.message.edit_text(
        f"➕ Добавление дня в «{program['name']}»{existing}\n\n"
        "Введи номер дня (число):",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AddDay.waiting_for_number)
async def process_day_number(message: Message, state: FSMContext):
    """Обработка номера дня."""
    try:
        day_number = int(message.text)
        if day_number < 1 or day_number > 100:
            raise ValueError()
    except (ValueError, TypeError):
        await message.answer(
            "Введи корректный номер дня (1-100):",
            reply_markup=cancel_kb()
        )
        return

    await state.update_data(day_number=day_number)
    await state.set_state(AddDay.waiting_for_name)

    await message.answer(
        f"День {day_number}\n\n"
        "Введи название дня (или нажми Пропустить):\n"
        "Например: Грудь+Трицепс, Ноги, Pull",
        reply_markup=skip_kb("skip_day_name")
    )


@router.callback_query(AddDay.waiting_for_name, F.data == "skip_day_name")
async def skip_day_name(callback: CallbackQuery, state: FSMContext):
    """Пропустить название дня."""
    data = await state.get_data()

    await db.create_day(
        program_id=data["program_id"],
        day_number=data["day_number"],
        name=None
    )

    await state.clear()
    await callback.message.edit_text(
        f"✅ День {data['day_number']} добавлен в «{data['program_name']}»!",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


@router.message(AddDay.waiting_for_name)
async def process_day_name(message: Message, state: FSMContext):
    """Сохранить день с названием."""
    data = await state.get_data()
    name = message.text.strip()

    try:
        await db.create_day(
            program_id=data["program_id"],
            day_number=data["day_number"],
            name=name
        )
        await state.clear()
        await message.answer(
            f"✅ День {data['day_number']} ({name}) добавлен в «{data['program_name']}»!",
            reply_markup=admin_panel_kb()
        )
    except Exception:
        await message.answer(
            "Ошибка: такой день уже существует.",
            reply_markup=cancel_kb()
        )


# ==================== ADD EXERCISE ====================

@router.callback_query(F.data == "add_exercise")
async def start_add_exercise(callback: CallbackQuery, state: FSMContext):
    """Начать добавление упражнения."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Сначала создай программу!", show_alert=True)
        return

    await state.set_state(AddExercise.waiting_for_program)

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"select_program_ex:{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))

    await callback.message.edit_text(
        "➕ Добавление упражнения\n\n"
        "Выбери программу:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(AddExercise.waiting_for_program, F.data.startswith("select_program_ex:"))
async def select_program_for_exercise(callback: CallbackQuery, state: FSMContext):
    """Выбор программы для упражнения."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)
    days = await db.get_days_by_program(program_id)

    if not days:
        await callback.answer("В программе нет дней! Сначала добавь день.", show_alert=True)
        return

    await state.update_data(program_id=program_id, program_name=program["name"])
    await state.set_state(AddExercise.waiting_for_day)

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for d in days:
        day_name = d["name"] if d["name"] else f"День {d['day_number']}"
        builder.row(
            InlineKeyboardButton(
                text=day_name,
                callback_data=f"select_day_ex:{d['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action"))

    await callback.message.edit_text(
        f"➕ Добавление упражнения в «{program['name']}»\n\n"
        "Выбери день:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(AddExercise.waiting_for_day, F.data.startswith("select_day_ex:"))
async def select_day_for_exercise(callback: CallbackQuery, state: FSMContext):
    """Выбор дня для упражнения."""
    day_id = int(callback.data.split(":")[1])
    day = await db.get_day(day_id)
    day_name = day["name"] if day["name"] else f"День {day['day_number']}"

    await state.update_data(day_id=day_id, day_name=day_name)
    await state.set_state(AddExercise.waiting_for_name)

    # Показываем существующие упражнения
    exercises = await db.get_exercises_by_day(day_id)
    existing = ""
    if exercises:
        existing = "\n\nУже есть:\n" + "\n".join(f"• {ex['name']}" for ex in exercises)

    await callback.message.edit_text(
        f"➕ Упражнение в {day_name}{existing}\n\n"
        "Введи название упражнения:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(AddExercise.waiting_for_name)
async def process_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "Название слишком короткое:",
            reply_markup=cancel_kb()
        )
        return

    await state.update_data(exercise_name=name)
    await state.set_state(AddExercise.waiting_for_description)

    await message.answer(
        f"Упражнение: {name}\n\n"
        "Введи описание (или нажми Пропустить):\n"
        "Например: 3×12, техника, подсказки",
        reply_markup=skip_kb("skip_ex_desc")
    )


@router.callback_query(AddExercise.waiting_for_description, F.data == "skip_ex_desc")
async def skip_exercise_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание."""
    await state.update_data(description=None)
    await state.set_state(AddExercise.waiting_for_tag)

    # Показываем существующие теги
    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    await callback.message.edit_text(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=skip_kb("skip_ex_tag")
    )
    await callback.answer()


@router.message(AddExercise.waiting_for_description)
async def process_exercise_description(message: Message, state: FSMContext):
    """Обработка описания."""
    description = message.text.strip()
    await state.update_data(description=description)
    await state.set_state(AddExercise.waiting_for_tag)

    # Показываем существующие теги
    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    await message.answer(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=skip_kb("skip_ex_tag")
    )


@router.callback_query(AddExercise.waiting_for_tag, F.data == "skip_ex_tag")
async def skip_exercise_tag(callback: CallbackQuery, state: FSMContext):
    """Пропустить тег."""
    await state.update_data(tag=None)
    await state.set_state(AddExercise.waiting_for_weight_type)

    from keyboards import weight_type_kb
    await callback.message.edit_text(
        "Выбери тип веса для упражнения:",
        reply_markup=weight_type_kb()
    )
    await callback.answer()


@router.message(AddExercise.waiting_for_tag)
async def process_exercise_tag(message: Message, state: FSMContext):
    """Обработка тега."""
    tag = message.text.strip().lower()
    await state.update_data(tag=tag)
    await state.set_state(AddExercise.waiting_for_weight_type)

    from keyboards import weight_type_kb
    await message.answer(
        f"Тег: #{tag}\n\n"
        "Выбери тип веса для упражнения:",
        reply_markup=weight_type_kb()
    )


@router.callback_query(AddExercise.waiting_for_weight_type, F.data.startswith("wt:"))
async def process_weight_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа веса."""
    weight_type = int(callback.data.split(":")[1])
    await state.update_data(weight_type=weight_type)
    await state.set_state(AddExercise.waiting_for_image)

    type_names = {0: "без веса", 10: "гантели", 100: "штанга"}
    await callback.message.edit_text(
        f"Тип веса: {type_names.get(weight_type, 'гантели')}\n\n"
        "Теперь отправь картинку упражнения (или нажми Пропустить):",
        reply_markup=skip_kb("skip_ex_image")
    )
    await callback.answer()


@router.callback_query(AddExercise.waiting_for_image, F.data == "skip_ex_image")
async def skip_exercise_image(callback: CallbackQuery, state: FSMContext):
    """Пропустить картинку и сохранить упражнение."""
    data = await state.get_data()

    await db.create_exercise(
        day_id=data["day_id"],
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=None,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10)
    )

    await state.clear()
    tag_text = f" (#{data['tag']})" if data.get("tag") else ""
    await callback.message.edit_text(
        f"✅ Упражнение «{data['exercise_name']}»{tag_text} добавлено в {data['day_name']}!",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


@router.message(AddExercise.waiting_for_image, F.photo)
async def process_exercise_image(message: Message, state: FSMContext):
    """Обработка картинки."""
    data = await state.get_data()

    # Берём самое большое фото
    photo = message.photo[-1]
    file_id = photo.file_id

    await db.create_exercise(
        day_id=data["day_id"],
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=file_id,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10)
    )

    await state.clear()
    tag_text = f" (#{data['tag']})" if data.get("tag") else ""
    await message.answer(
        f"✅ Упражнение «{data['exercise_name']}»{tag_text} добавлено в {data['day_name']}!",
        reply_markup=admin_panel_kb()
    )


@router.message(AddExercise.waiting_for_image)
async def wrong_image_format(message: Message, state: FSMContext):
    """Неправильный формат — ожидаем фото."""
    await message.answer(
        "Отправь картинку как фото, или нажми Пропустить:",
        reply_markup=skip_kb("skip_ex_image")
    )


# ==================== DELETE MENU ====================

@router.callback_query(F.data == "delete_menu")
async def delete_menu(callback: CallbackQuery):
    """Меню удаления."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить программу", callback_data="delete_program")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить день", callback_data="delete_day")
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить упражнение", callback_data="delete_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin_menu")
    )

    await callback.message.edit_text(
        "🗑 Удаление\n\n"
        "Что удалить?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "delete_program")
async def start_delete_program(callback: CallbackQuery):
    """Выбор программы для удаления."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Нет программ для удаления", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {p['name']}",
                callback_data=f"confirm_del_program:{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_menu"))

    await callback.message.edit_text(
        "🗑 Удаление программы\n\n"
        "Выбери программу для удаления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_del_program:"))
async def confirm_delete_program(callback: CallbackQuery):
    """Подтверждение удаления программы."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)

    if not program:
        await callback.answer("Программа не найдена", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"do_del_program:{program_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="delete_program")
    )

    await callback.message.edit_text(
        f"⚠️ Удалить программу «{program['name']}»?\n\n"
        "Это удалит все дни и упражнения в ней!",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("do_del_program:"))
async def do_delete_program(callback: CallbackQuery):
    """Удаление программы."""
    program_id = int(callback.data.split(":")[1])
    program = await db.get_program(program_id)

    if program:
        await db.delete_program(program_id)
        await callback.message.edit_text(
            f"✅ Программа «{program['name']}» удалена!",
            reply_markup=admin_panel_kb()
        )
    else:
        await callback.answer("Программа не найдена", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "delete_day")
async def start_delete_day(callback: CallbackQuery, state: FSMContext):
    """Выбор программы для удаления дня."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Нет программ", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"del_day_program:{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_menu"))

    await callback.message.edit_text(
        "🗑 Удаление дня\n\nВыбери программу:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_day_program:"))
async def select_day_to_delete(callback: CallbackQuery):
    """Выбор дня для удаления."""
    program_id = int(callback.data.split(":")[1])
    days = await db.get_days_by_program(program_id)

    if not days:
        await callback.answer("В программе нет дней", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for d in days:
        day_name = d["name"] if d["name"] else f"День {d['day_number']}"
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {day_name}",
                callback_data=f"do_del_day:{d['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_day"))

    await callback.message.edit_text(
        "🗑 Выбери день для удаления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("do_del_day:"))
async def do_delete_day(callback: CallbackQuery):
    """Удаление дня."""
    day_id = int(callback.data.split(":")[1])
    day = await db.get_day(day_id)

    if day:
        day_name = day["name"] if day["name"] else f"День {day['day_number']}"
        await db.delete_day(day_id)
        await callback.message.edit_text(
            f"✅ {day_name} удалён!",
            reply_markup=admin_panel_kb()
        )
    else:
        await callback.answer("День не найден", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "delete_exercise")
async def start_delete_exercise(callback: CallbackQuery):
    """Выбор программы для удаления упражнения."""
    programs = await db.get_all_programs()

    if not programs:
        await callback.answer("Нет программ", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for p in programs:
        builder.row(
            InlineKeyboardButton(
                text=p["name"],
                callback_data=f"del_ex_program:{p['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_menu"))

    await callback.message.edit_text(
        "🗑 Удаление упражнения\n\nВыбери программу:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_ex_program:"))
async def select_day_for_del_exercise(callback: CallbackQuery):
    """Выбор дня для удаления упражнения."""
    program_id = int(callback.data.split(":")[1])
    days = await db.get_days_by_program(program_id)

    if not days:
        await callback.answer("В программе нет дней", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for d in days:
        day_name = d["name"] if d["name"] else f"День {d['day_number']}"
        builder.row(
            InlineKeyboardButton(
                text=day_name,
                callback_data=f"del_ex_day:{d['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_exercise"))

    await callback.message.edit_text(
        "🗑 Выбери день:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("del_ex_day:"))
async def select_exercise_to_delete(callback: CallbackQuery):
    """Выбор упражнения для удаления."""
    day_id = int(callback.data.split(":")[1])
    exercises = await db.get_exercises_by_day(day_id)

    if not exercises:
        await callback.answer("В дне нет упражнений", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for ex in exercises:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {ex['name']}",
                callback_data=f"do_del_ex:{ex['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="delete_exercise"))

    await callback.message.edit_text(
        "🗑 Выбери упражнение для удаления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("do_del_ex:"))
async def do_delete_exercise(callback: CallbackQuery):
    """Удаление упражнения."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if exercise:
        await db.delete_exercise(exercise_id)
        await callback.message.edit_text(
            f"✅ Упражнение «{exercise['name']}» удалено!",
            reply_markup=admin_panel_kb()
        )
    else:
        await callback.answer("Упражнение не найдено", show_alert=True)

    await callback.answer()


# ==================== MANAGE USERS ====================

@router.callback_query(F.data == "manage_users")
async def manage_users(callback: CallbackQuery):
    """Показать список пользователей."""
    users = await db.get_all_allowed_users()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    if not users:
        text = "👥 Пользователи\n\nПока нет одобренных пользователей."
    else:
        text = f"👥 Пользователи ({len(users)}):\n\n"
        for u in users:
            name = u["full_name"] or u["username"] or str(u["user_id"])
            text += f"• {name}\n"

    builder = InlineKeyboardBuilder()
    if users:
        builder.row(
            InlineKeyboardButton(text="🗑 Удалить пользователя", callback_data="remove_user_menu")
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin_menu")
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "remove_user_menu")
async def remove_user_menu(callback: CallbackQuery):
    """Выбор пользователя для удаления."""
    users = await db.get_all_allowed_users()

    if not users:
        await callback.answer("Нет пользователей", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for u in users:
        name = u["full_name"] or u["username"] or str(u["user_id"])
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {name}",
                callback_data=f"remove_user:{u['user_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="manage_users")
    )

    await callback.message.edit_text(
        "🗑 Выбери пользователя для удаления доступа:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_user:"))
async def remove_user(callback: CallbackQuery):
    """Удалить пользователя."""
    user_id = int(callback.data.split(":")[1])

    await db.remove_allowed_user(user_id)

    await callback.message.edit_text(
        f"✅ Пользователь удалён из списка доступа!",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


# ==================== MANAGE TAGS ====================

@router.callback_query(F.data == "manage_tags")
async def manage_tags(callback: CallbackQuery):
    """Показать список тегов."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    tags = await db.get_all_tags()

    if not tags:
        text = "🏷 Теги\n\nПока нет тегов. Теги создаются автоматически при добавлении упражнений."
    else:
        text = "🏷 Теги\n\nИспользуемые теги:\n\n"
        for tag in tags:
            text += f"• #{tag['name']} ({tag['exercise_count']} упр.)\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="« Назад", callback_data="admin_menu")
    )

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


class EditExerciseTag(StatesGroup):
    waiting_for_tag = State()


@router.callback_query(F.data.startswith("edit_tags:"))
async def edit_exercise_tag(callback: CallbackQuery, state: FSMContext):
    """Изменить тег упражнения."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    await state.update_data(exercise_id=exercise_id)
    await state.set_state(EditExerciseTag.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    if exercise.get("tag"):
        tags = [t.strip() for t in exercise["tag"].split(",") if t.strip()]
        current_tag = "Текущий тег: " + " ".join(f"#{t}" for t in tags)
    else:
        current_tag = "Тег не установлен"

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    if exercise.get("tag"):
        builder.row(
            InlineKeyboardButton(text="🗑 Убрать тег", callback_data=f"remove_tag:{exercise_id}")
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"exercise:{exercise_id}")
    )

    await callback.message.edit_text(
        f"🏷 Тег для «{exercise['name']}»\n\n"
        f"{current_tag}{tags_hint}\n\n"
        "Введи новый тег:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.message(EditExerciseTag.waiting_for_tag)
async def process_edit_tag(message: Message, state: FSMContext):
    """Сохранить новый тег упражнения."""
    data = await state.get_data()
    exercise_id = data["exercise_id"]
    new_tag = message.text.strip().lower()

    await db.update_exercise_tag(exercise_id, new_tag)
    await state.clear()

    exercise = await db.get_exercise(exercise_id)

    from keyboards import exercise_detail_kb
    await message.answer(
        f"✅ Тег для «{exercise['name']}» изменён на #{new_tag}",
        reply_markup=exercise_detail_kb(exercise_id, exercise["day_id"], is_admin=True)
    )


@router.callback_query(F.data.startswith("remove_tag:"))
async def remove_exercise_tag(callback: CallbackQuery, state: FSMContext):
    """Убрать тег у упражнения."""
    exercise_id = int(callback.data.split(":")[1])

    await db.update_exercise_tag(exercise_id, None)
    await state.clear()

    exercise = await db.get_exercise(exercise_id)

    from keyboards import exercise_detail_kb
    await callback.message.edit_text(
        f"✅ Тег для «{exercise['name']}» удалён",
        reply_markup=exercise_detail_kb(exercise_id, exercise["day_id"], is_admin=True)
    )
    await callback.answer()