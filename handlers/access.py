from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID, ACCESS_CODE
import database as db

router = Router()


class AccessState(StatesGroup):
    """Состояние ввода кода доступа."""
    waiting_for_code = State()


class NotAuthorized(BaseFilter):
    """Фильтр для неавторизованных пользователей."""
    async def __call__(self, message: Message) -> bool:
        user_id = message.from_user.id
        if user_id == ADMIN_ID:
            return False
        return not await db.is_user_allowed(user_id)


@router.message(CommandStart(), NotAuthorized())
async def cmd_start_access(message: Message, state: FSMContext):
    """Обработка /start для неавторизованных."""
    await state.set_state(AccessState.waiting_for_code)
    await message.answer(
        "Привет! Для доступа к боту введи код доступа:"
    )


@router.message(AccessState.waiting_for_code)
async def process_access_code(message: Message, state: FSMContext):
    """Обработка ввода кода доступа."""
    user_id = message.from_user.id
    code = message.text.strip()

    if code == ACCESS_CODE:
        # Код верный - добавляем пользователя
        await db.add_allowed_user(
            user_id=user_id,
            username=message.from_user.username,
            full_name=message.from_user.full_name
        )
        await state.clear()

        # Сразу показываем главное меню
        from handlers.start import get_main_text_and_kb
        text, kb = await get_main_text_and_kb(user_id)
        await message.answer(f"Доступ разрешён!\n\n{text}", reply_markup=kb)
    else:
        await message.answer(
            "Неверный код. Попробуй ещё раз:"
        )