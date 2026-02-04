from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import BaseFilter

from config import ADMIN_ID
from keyboards import (
    admin_panel_kb, cancel_kb, skip_kb,
    programs_kb, days_kb, admin_menu_kb,
    exercise_library_kb, lib_exercise_detail_kb,
    select_day_for_exercise_kb, add_exercise_to_day_kb,
    library_exercises_for_day_kb, exercises_kb
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
    waiting_for_description = State()


class AddExercise(StatesGroup):
    """Добавление упражнения из библиотеки в день."""
    waiting_for_program = State()
    waiting_for_day = State()
    waiting_for_source = State()  # из библиотеки или новое


class CreateExercise(StatesGroup):
    """Создание нового упражнения в библиотеке."""
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


# ==================== EXERCISE LIBRARY ====================

@router.callback_query(F.data == "exercise_library")
async def show_exercise_library(callback: CallbackQuery):
    """Показать библиотеку упражнений."""
    exercises = await db.get_all_exercises()

    text = "📚 Библиотека упражнений\n\n"
    if exercises:
        text += f"Всего упражнений: {len(exercises)}"
    else:
        text += "Пока нет упражнений. Создай первое!"

    await callback.message.edit_text(
        text,
        reply_markup=exercise_library_kb(exercises)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lib_exercise:"))
async def show_library_exercise(callback: CallbackQuery):
    """Показать детали упражнения в библиотеке."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    # Получаем дни, в которых используется
    exercise_days = await db.get_exercise_days(exercise_id)

    text = f"📚 {exercise['name']}\n\n"

    if "tag" in exercise.keys() and exercise["tag"]:
        tags = [t.strip() for t in exercise["tag"].split(",") if t.strip()]
        text += "🏷 " + " ".join(f"#{t}" for t in tags) + "\n"

    if "description" in exercise.keys() and exercise["description"]:
        text += f"\n{exercise['description']}\n"

    weight_types = {0: "без веса", 10: "гантели", 100: "штанга"}
    weight_type = exercise["weight_type"] if "weight_type" in exercise.keys() else 10
    text += f"\n⚖️ Тип веса: {weight_types.get(weight_type, 'гантели')}\n"

    if exercise_days:
        text += "\n📋 Используется в днях:\n"
        for d in exercise_days:
            day_name = d["name"] or f"День {d['day_number']}"
            text += f"  • {d['program_name']} / {day_name}\n"
    else:
        text += "\n⚠️ Не добавлено ни в один день"

    await callback.message.edit_text(
        text,
        reply_markup=lib_exercise_detail_kb(exercise_id)
    )
    await callback.answer()


@router.callback_query(F.data == "create_exercise")
async def start_create_exercise(callback: CallbackQuery, state: FSMContext):
    """Начать создание упражнения в библиотеке."""
    await state.set_state(CreateExercise.waiting_for_name)

    await callback.message.edit_text(
        "➕ Создание упражнения\n\n"
        "Введи название упражнения:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


@router.message(CreateExercise.waiting_for_name)
async def process_lib_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения."""
    name = message.text.strip()

    if len(name) < 2:
        await message.answer(
            "Название слишком короткое. Минимум 2 символа:",
            reply_markup=cancel_kb()
        )
        return

    await state.update_data(exercise_name=name)
    await state.set_state(CreateExercise.waiting_for_description)

    await message.answer(
        f"Упражнение: {name}\n\n"
        "Введи описание (или нажми Пропустить):\n"
        "Например: 3×12, техника, подсказки",
        reply_markup=skip_kb("skip_lib_desc")
    )


@router.callback_query(CreateExercise.waiting_for_description, F.data == "skip_lib_desc")
async def skip_lib_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание."""
    await state.update_data(description=None)
    await state.set_state(CreateExercise.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    await callback.message.edit_text(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=skip_kb("skip_lib_tag")
    )
    await callback.answer()


@router.message(CreateExercise.waiting_for_description)
async def process_lib_description(message: Message, state: FSMContext):
    """Обработка описания."""
    description = message.text.strip()
    await state.update_data(description=description)
    await state.set_state(CreateExercise.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    await message.answer(
        f"Введи тег (группа мышц){tags_hint}\n\n"
        "Например: бицепс, грудь, ноги\n"
        "(или нажми Пропустить)",
        reply_markup=skip_kb("skip_lib_tag")
    )


@router.callback_query(CreateExercise.waiting_for_tag, F.data == "skip_lib_tag")
async def skip_lib_tag(callback: CallbackQuery, state: FSMContext):
    """Пропустить тег."""
    await state.update_data(tag=None)
    await state.set_state(CreateExercise.waiting_for_weight_type)

    from keyboards import weight_type_kb
    await callback.message.edit_text(
        "Выбери тип веса для упражнения:",
        reply_markup=weight_type_kb()
    )
    await callback.answer()


@router.message(CreateExercise.waiting_for_tag)
async def process_lib_tag(message: Message, state: FSMContext):
    """Обработка тега."""
    tag = message.text.strip().lower()
    await state.update_data(tag=tag)
    await state.set_state(CreateExercise.waiting_for_weight_type)

    from keyboards import weight_type_kb
    await message.answer(
        f"Тег: #{tag}\n\n"
        "Выбери тип веса для упражнения:",
        reply_markup=weight_type_kb()
    )


@router.callback_query(CreateExercise.waiting_for_weight_type, F.data.startswith("wt:"))
async def process_lib_weight_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа веса."""
    weight_type = int(callback.data.split(":")[1])
    await state.update_data(weight_type=weight_type)
    await state.set_state(CreateExercise.waiting_for_image)

    type_names = {0: "без веса", 10: "гантели", 100: "штанга"}
    await callback.message.edit_text(
        f"Тип веса: {type_names.get(weight_type, 'гантели')}\n\n"
        "Теперь отправь фото или GIF упражнения (или нажми Пропустить):",
        reply_markup=skip_kb("skip_lib_image")
    )
    await callback.answer()


@router.callback_query(CreateExercise.waiting_for_image, F.data == "skip_lib_image")
async def skip_lib_image(callback: CallbackQuery, state: FSMContext):
    """Пропустить картинку и сохранить упражнение."""
    data = await state.get_data()

    exercise_id = await db.create_exercise(
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=None,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10)
    )

    # Если пришли из добавления в день - добавляем связь
    day_id = data.get("target_day_id")
    if day_id:
        await db.add_exercise_to_day(exercise_id, day_id)
        day = await db.get_day(day_id)
        day_name = day["name"] or f"День {day['day_number']}"
        await state.clear()
        await callback.message.edit_text(
            f"✅ Упражнение «{data['exercise_name']}» создано и добавлено в {day_name}!",
            reply_markup=admin_panel_kb()
        )
    else:
        await state.clear()
        tag_text = f" (#{data['tag']})" if data.get("tag") else ""
        await callback.message.edit_text(
            f"✅ Упражнение «{data['exercise_name']}»{tag_text} создано в библиотеке!",
            reply_markup=exercise_library_kb(await db.get_all_exercises())
        )
    await callback.answer()


@router.message(CreateExercise.waiting_for_image, F.photo)
async def process_lib_image(message: Message, state: FSMContext):
    """Обработка фото."""
    data = await state.get_data()

    photo = message.photo[-1]
    file_id = photo.file_id

    exercise_id = await db.create_exercise(
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=file_id,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10),
        media_type="photo"
    )

    # Если пришли из добавления в день - добавляем связь
    day_id = data.get("target_day_id")
    if day_id:
        await db.add_exercise_to_day(exercise_id, day_id)
        day = await db.get_day(day_id)
        day_name = day["name"] or f"День {day['day_number']}"
        await state.clear()
        await message.answer(
            f"✅ Упражнение «{data['exercise_name']}» создано и добавлено в {day_name}!",
            reply_markup=admin_panel_kb()
        )
    else:
        await state.clear()
        tag_text = f" (#{data['tag']})" if data.get("tag") else ""
        await message.answer(
            f"✅ Упражнение «{data['exercise_name']}»{tag_text} создано в библиотеке!",
            reply_markup=exercise_library_kb(await db.get_all_exercises())
        )


@router.message(CreateExercise.waiting_for_image, F.animation)
async def process_lib_animation(message: Message, state: FSMContext):
    """Обработка GIF."""
    data = await state.get_data()

    animation = message.animation
    file_id = animation.file_id

    exercise_id = await db.create_exercise(
        name=data["exercise_name"],
        description=data.get("description"),
        image_file_id=file_id,
        tag=data.get("tag"),
        weight_type=data.get("weight_type", 10),
        media_type="animation"
    )

    # Если пришли из добавления в день - добавляем связь
    day_id = data.get("target_day_id")
    if day_id:
        await db.add_exercise_to_day(exercise_id, day_id)
        day = await db.get_day(day_id)
        day_name = day["name"] or f"День {day['day_number']}"
        await state.clear()
        await message.answer(
            f"✅ Упражнение «{data['exercise_name']}» (GIF) создано и добавлено в {day_name}!",
            reply_markup=admin_panel_kb()
        )
    else:
        await state.clear()
        tag_text = f" (#{data['tag']})" if data.get("tag") else ""
        await message.answer(
            f"✅ Упражнение «{data['exercise_name']}»{tag_text} (GIF) создано в библиотеке!",
            reply_markup=exercise_library_kb(await db.get_all_exercises())
        )


@router.message(CreateExercise.waiting_for_image)
async def wrong_lib_image_format(message: Message, state: FSMContext):
    """Неправильный формат — ожидаем фото или GIF."""
    await message.answer(
        "Отправь фото или GIF, или нажми Пропустить:",
        reply_markup=skip_kb("skip_lib_image")
    )


@router.callback_query(F.data.startswith("add_to_day:"))
async def add_exercise_to_day_menu(callback: CallbackQuery):
    """Выбрать день для добавления упражнения."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    programs = await db.get_all_programs()
    if not programs:
        await callback.answer("Сначала создай программу!", show_alert=True)
        return

    # Собираем дни по программам
    days_by_program = {}
    for p in programs:
        days = await db.get_days_by_program(p['id'])
        if days:
            days_by_program[p['id']] = days

    if not days_by_program:
        await callback.answer("Нет дней в программах!", show_alert=True)
        return

    await callback.message.edit_text(
        f"📋 Добавить «{exercise['name']}» в день:\n\nВыбери программу и день:",
        reply_markup=select_day_for_exercise_kb(programs, days_by_program, exercise_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("link_exercise:"))
async def link_exercise_to_day(callback: CallbackQuery):
    """Связать упражнение с днём."""
    parts = callback.data.split(":")
    exercise_id = int(parts[1])
    day_id = int(parts[2])

    exercise = await db.get_exercise(exercise_id)
    day = await db.get_day(day_id)

    if not exercise or not day:
        await callback.answer("Упражнение или день не найдены", show_alert=True)
        return

    # Добавляем связь
    await db.add_exercise_to_day(exercise_id, day_id)

    day_name = day["name"] or f"День {day['day_number']}"
    await callback.message.edit_text(
        f"✅ «{exercise['name']}» добавлено в {day_name}!",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_lib_exercise:"))
async def confirm_delete_lib_exercise(callback: CallbackQuery):
    """Подтверждение удаления упражнения из библиотеки."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if not exercise:
        await callback.answer("Упражнение не найдено", show_alert=True)
        return

    exercise_days = await db.get_exercise_days(exercise_id)

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"do_del_lib_ex:{exercise_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"lib_exercise:{exercise_id}")
    )

    warning = ""
    if exercise_days:
        warning = f"\n\n⚠️ Упражнение используется в {len(exercise_days)} днях!"

    await callback.message.edit_text(
        f"🗑 Удалить «{exercise['name']}» из библиотеки?{warning}\n\n"
        "Это также удалит всю историю тренировок по этому упражнению!",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("do_del_lib_ex:"))
async def do_delete_lib_exercise(callback: CallbackQuery):
    """Удалить упражнение из библиотеки."""
    exercise_id = int(callback.data.split(":")[1])
    exercise = await db.get_exercise(exercise_id)

    if exercise:
        await db.delete_exercise(exercise_id)
        await callback.message.edit_text(
            f"✅ Упражнение «{exercise['name']}» удалено из библиотеки!",
            reply_markup=exercise_library_kb(await db.get_all_exercises())
        )
    else:
        await callback.answer("Упражнение не найдено", show_alert=True)

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
    await state.update_data(day_name=None)
    await state.set_state(AddDay.waiting_for_description)

    data = await state.get_data()
    await callback.message.edit_text(
        f"День {data['day_number']}\n\n"
        "Введи описание дня (или нажми Пропустить):\n"
        "Например: Фокус на грудь, лёгкая кардио разминка",
        reply_markup=skip_kb("skip_day_desc")
    )
    await callback.answer()


@router.message(AddDay.waiting_for_name)
async def process_day_name(message: Message, state: FSMContext):
    """Сохранить название дня и перейти к описанию."""
    name = message.text.strip()
    await state.update_data(day_name=name)
    await state.set_state(AddDay.waiting_for_description)

    data = await state.get_data()
    await message.answer(
        f"День {data['day_number']} — {name}\n\n"
        "Введи описание дня (или нажми Пропустить):\n"
        "Например: Фокус на грудь, лёгкая кардио разминка",
        reply_markup=skip_kb("skip_day_desc")
    )


@router.callback_query(AddDay.waiting_for_description, F.data == "skip_day_desc")
async def skip_day_description(callback: CallbackQuery, state: FSMContext):
    """Пропустить описание и сохранить день."""
    data = await state.get_data()

    try:
        await db.create_day(
            program_id=data["program_id"],
            day_number=data["day_number"],
            name=data.get("day_name"),
            description=None
        )
        await state.clear()

        name_text = f" ({data['day_name']})" if data.get("day_name") else ""
        await callback.message.edit_text(
            f"✅ День {data['day_number']}{name_text} добавлен в «{data['program_name']}»!",
            reply_markup=admin_panel_kb()
        )
    except Exception:
        await callback.message.edit_text(
            "Ошибка: такой день уже существует.",
            reply_markup=cancel_kb()
        )
    await callback.answer()


@router.message(AddDay.waiting_for_description)
async def process_day_description(message: Message, state: FSMContext):
    """Сохранить день с описанием."""
    data = await state.get_data()
    description = message.text.strip()

    try:
        await db.create_day(
            program_id=data["program_id"],
            day_number=data["day_number"],
            name=data.get("day_name"),
            description=description
        )
        await state.clear()

        name_text = f" ({data['day_name']})" if data.get("day_name") else ""
        await message.answer(
            f"✅ День {data['day_number']}{name_text} добавлен в «{data['program_name']}»!",
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
    """Выбор дня для упражнения - показать выбор источника."""
    day_id = int(callback.data.split(":")[1])
    day = await db.get_day(day_id)
    day_name = day["name"] if day["name"] else f"День {day['day_number']}"

    await state.update_data(day_id=day_id, day_name=day_name, target_day_id=day_id)
    await state.set_state(AddExercise.waiting_for_source)

    # Показываем существующие упражнения
    day_exercises = await db.get_exercises_by_day(day_id)
    existing = ""
    if day_exercises:
        existing = "\n\nУже есть:\n" + "\n".join(f"• {ex['name']}" for ex in day_exercises)

    await callback.message.edit_text(
        f"➕ Добавить упражнение в {day_name}{existing}\n\n"
        "Выбери способ:",
        reply_markup=add_exercise_to_day_kb()
    )
    await callback.answer()


@router.callback_query(AddExercise.waiting_for_source, F.data == "from_library")
async def add_from_library(callback: CallbackQuery, state: FSMContext):
    """Показать список упражнений из библиотеки."""
    data = await state.get_data()
    day_id = data["day_id"]

    # Все упражнения библиотеки
    all_exercises = await db.get_all_exercises()

    # Уже добавленные в день
    day_exercises = await db.get_exercises_by_day(day_id)
    day_exercise_ids = {ex["id"] for ex in day_exercises}

    # Фильтруем — только те, что ещё не добавлены
    available = [ex for ex in all_exercises if ex["id"] not in day_exercise_ids]

    if not available:
        await callback.answer("Все упражнения уже добавлены в этот день!", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        f"📚 Выбери упражнение для добавления в {data['day_name']}:",
        reply_markup=library_exercises_for_day_kb(available, day_id)
    )
    await callback.answer()


@router.callback_query(AddExercise.waiting_for_source, F.data == "create_new_exercise")
async def create_new_for_day(callback: CallbackQuery, state: FSMContext):
    """Создать новое упражнение для дня."""
    data = await state.get_data()
    # Сохраняем target_day_id и переходим к созданию
    await state.update_data(target_day_id=data["day_id"])
    await state.set_state(CreateExercise.waiting_for_name)

    await callback.message.edit_text(
        f"➕ Создание упражнения для {data['day_name']}\n\n"
        "Введи название упражнения:",
        reply_markup=cancel_kb()
    )
    await callback.answer()


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

    # Находим первый день для кнопки "назад"
    exercise_days = await db.get_exercise_days(exercise_id)
    day_id = exercise_days[0]["id"] if exercise_days else 0

    await state.update_data(exercise_id=exercise_id)
    await state.set_state(EditExerciseTag.waiting_for_tag)

    tags = await db.get_all_tags()
    tags_hint = ""
    if tags:
        tags_hint = "\n\nИспользуемые теги: " + ", ".join(t["name"] for t in tags)

    has_tag = "tag" in exercise.keys() and exercise["tag"]
    if has_tag:
        tag_list = [t.strip() for t in exercise["tag"].split(",") if t.strip()]
        current_tag = "Текущий тег: " + " ".join(f"#{t}" for t in tag_list)
    else:
        current_tag = "Тег не установлен"

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    if has_tag:
        builder.row(
            InlineKeyboardButton(text="🗑 Убрать тег", callback_data=f"remove_tag:{exercise_id}")
        )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"exercise:{exercise_id}:{day_id}")
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

    # Находим первый день, если есть
    exercise_days = await db.get_exercise_days(exercise_id)
    day_id = exercise_days[0]["id"] if exercise_days else 0

    from keyboards import exercise_detail_kb
    await message.answer(
        f"✅ Тег для «{exercise['name']}» изменён на #{new_tag}",
        reply_markup=exercise_detail_kb(exercise_id, day_id, is_admin=True)
    )


@router.callback_query(F.data.startswith("remove_tag:"))
async def remove_exercise_tag(callback: CallbackQuery, state: FSMContext):
    """Убрать тег у упражнения."""
    exercise_id = int(callback.data.split(":")[1])

    await db.update_exercise_tag(exercise_id, None)
    await state.clear()

    exercise = await db.get_exercise(exercise_id)

    # Находим первый день, если есть
    exercise_days = await db.get_exercise_days(exercise_id)
    day_id = exercise_days[0]["id"] if exercise_days else 0

    from keyboards import exercise_detail_kb
    await callback.message.edit_text(
        f"✅ Тег для «{exercise['name']}» удалён",
        reply_markup=exercise_detail_kb(exercise_id, day_id, is_admin=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("move_ex:"))
async def move_exercise_order(callback: CallbackQuery):
    """Переместить упражнение вверх/вниз в дне."""
    parts = callback.data.split(":")
    exercise_id = int(parts[1])
    day_id = int(parts[2])
    direction = int(parts[3])  # -1 вверх, 1 вниз

    await db.move_exercise_in_day(exercise_id, day_id, direction)

    # Обновляем клавиатуру
    day = await db.get_day(day_id)
    program = await db.get_program(day["program_id"])
    exercises = await db.get_exercises_by_day(day_id)

    day_name = day["name"] if day["name"] else f"День {day['day_number']}"
    text = f"📋 {program['name']} — {day_name}\n\nВыбери упражнение:"

    await callback.message.edit_text(
        text,
        reply_markup=exercises_kb(exercises, day_id, is_admin=True)
    )
    await callback.answer()