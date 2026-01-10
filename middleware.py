from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
import database as db


class AccessMiddleware(BaseMiddleware):
    """Middleware для проверки доступа пользователя."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем user_id
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
            # Пропускаем /start - его обработает access router
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)

            # Проверяем FSM состояние - если в процессе ввода, пропускаем
            state: FSMContext = data.get("state")
            if state:
                current_state = await state.get_state()
                if current_state and ("AccessState" in current_state or "CustomMode" in current_state or "LogWorkout" in current_state or "EditExerciseTag" in current_state):
                    return await handler(event, data)

        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is None:
            return await handler(event, data)

        # Админ всегда имеет доступ
        if user_id == ADMIN_ID:
            return await handler(event, data)

        # Проверяем в базе
        if await db.is_user_allowed(user_id):
            return await handler(event, data)

        # Нет доступа - показываем сообщение
        if isinstance(event, Message):
            await event.answer(
                "У тебя нет доступа. Нажми /start и введи код доступа."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer("Нет доступа. Нажми /start", show_alert=True)

        return None