from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import ADMIN_ID
from keyboards import main_menu_kb, admin_menu_kb
import database as db

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start."""
    is_admin = message.from_user.id == ADMIN_ID
    kb = admin_menu_kb() if is_admin else main_menu_kb()

    await message.answer(
        "Привет! Я бот для тренировок.\n\n"
        "Выбери программу и записывай свои результаты.",
        reply_markup=kb
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню."""
    is_admin = callback.from_user.id == ADMIN_ID
    kb = admin_menu_kb() if is_admin else main_menu_kb()

    await callback.message.edit_text(
        "Выбери программу и записывай свои результаты.",
        reply_markup=kb
    )
    await callback.answer()


@router.callback_query(F.data == "my_stats")
async def show_my_stats(callback: CallbackQuery):
    """Показать статистику пользователя."""
    user_id = callback.from_user.id
    stats = await db.get_user_stats(user_id)

    text = (
        f"📊 Твоя статистика:\n\n"
        f"Тренировок: {stats['total_workouts']}\n"
        f"Всего подходов: {stats['total_sets']}"
    )

    is_admin = user_id == ADMIN_ID
    kb = admin_menu_kb() if is_admin else main_menu_kb()

    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery):
    """Отмена текущего действия."""
    is_admin = callback.from_user.id == ADMIN_ID
    kb = admin_menu_kb() if is_admin else main_menu_kb()

    await callback.message.edit_text(
        "Действие отменено.\n\nВыбери программу и записывай свои результаты.",
        reply_markup=kb
    )
    await callback.answer()