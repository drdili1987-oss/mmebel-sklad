from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject

from .keyboards import MAIN_MENU_BUTTONS

log = logging.getLogger(__name__)


class ContextMiddleware(BaseMiddleware):
    """Har bir hodisaga `role` qo'shadi va asosiy menyu tugmasi bosilganda FSM holatini tozalaydi."""

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]],
                       event: TelegramObject, data: dict) -> Any:
        services = data["services"]
        user = data.get("event_from_user")
        if user:
            data["role"] = await services.users.role(user.id)
            try:
                await services.users.touch(user.id, user.full_name, user.username)
            except Exception as e:  # noqa: BLE001
                log.debug("touch xato: %s", e)
        else:
            data["role"] = "mijoz"
        if isinstance(event, Message) and event.text in MAIN_MENU_BUTTONS:
            state = data.get("state")
            if state is not None:
                await state.clear()
                # MUHIM: filtrlar `raw_state` ni ishlatadi — uni ham tozalamasak, eski holat
                # handler'i menyu tugmasini "kiritilgan qiymat" sifatida qabul qilib olardi.
                data["raw_state"] = None
        return await handler(event, data)


class Role(Filter):
    def __init__(self, *roles: str):
        self.roles = set(roles)

    async def __call__(self, event: Message | CallbackQuery, role: str = "mijoz") -> bool:
        return role in self.roles
