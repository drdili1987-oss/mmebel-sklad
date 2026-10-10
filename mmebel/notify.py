"""Telegram xabarnomalari: HTML, xatoga chidamli, loglangan.

Eski kodda xatolar `except: pass` bilan yutilib ketardi va Markdown buzilganda
(masalan, ismda '_' bo'lsa) adminlar xabar olmasdi. Endi: HTML + oddiy matnga qaytish + log.
"""
from __future__ import annotations

import asyncio
import logging
import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from .constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM
from .utils import chunk_text

log = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return (_TAG_RE.sub("", text).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))


class Notifier:
    def __init__(self, bot: Bot, users_service, push=None):
        self.bot = bot
        self.users = users_service
        self.push = push

    async def send(self, chat_id: int, text: str, reply_markup=None, push: bool = True,
                   sound: str | None = None) -> bool:
        chunks = chunk_text(text)
        ok = True
        for i, chunk in enumerate(chunks):
            markup = reply_markup if i == len(chunks) - 1 else None
            ok &= await self._send_one(chat_id, chunk, markup)
        if push and self.push is not None:
            from .push import split_message
            title, body = split_message(strip_html(text))
            self.push.notify_later(chat_id, title, body, sound)
        return ok

    async def _send_one(self, chat_id: int, text: str, markup) -> bool:
        for attempt in range(3):
            try:
                await self.bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML",
                                            disable_web_page_preview=True)
                return True
            except TelegramRetryAfter as e:
                await asyncio.sleep(min(e.retry_after, 30))
            except TelegramForbiddenError:
                log.info("Foydalanuvchi %s botni bloklagan", chat_id)
                return False
            except TelegramBadRequest as e:
                if "parse" in str(e).lower() or "entities" in str(e).lower():
                    try:
                        await self.bot.send_message(chat_id, strip_html(text), reply_markup=markup,
                                                    parse_mode=None, disable_web_page_preview=True)
                        return True
                    except Exception as e2:  # noqa: BLE001
                        log.warning("Xabar yuborilmadi %s: %s", chat_id, e2)
                        return False
                log.warning("Xabar yuborilmadi %s: %s", chat_id, e)
                return False
            except Exception as e:  # noqa: BLE001 — tarmoq xatolari
                log.warning("Xabar yuborishda xato %s (urinish %d): %s", chat_id, attempt + 1, e)
                await asyncio.sleep(1 + attempt)
        return False

    async def to_ids(self, ids, text: str, reply_markup=None, exclude=None, sound: str | None = None) -> int:
        sent = 0
        for uid in dict.fromkeys(int(i) for i in ids):
            if exclude is not None and uid == int(exclude):
                continue
            sent += await self.send(uid, text, reply_markup, sound=sound)
            await asyncio.sleep(0.05)  # Telegram limitlariga rioya
        return sent

    async def to_roles(self, roles, text: str, reply_markup=None, exclude=None, sound: str | None = None) -> int:
        return await self.to_ids(await self.users.ids_with_roles(roles), text, reply_markup, exclude, sound)

    async def to_admins(self, text: str, reply_markup=None, exclude=None) -> int:
        return await self.to_roles([ROLE_ADMIN], text, reply_markup, exclude)

    async def to_staff(self, text: str, exclude=None, include_admin: bool = True, sound: str | None = None) -> int:
        roles = [ROLE_OMBORCHI, ROLE_XODIM] + ([ROLE_ADMIN] if include_admin else [])
        return await self.to_roles(roles, text, exclude=exclude, sound=sound)

    async def to_client(self, client_name: str, text: str, reply_markup=None, sound: str | None = None) -> int:
        return await self.to_ids(await self.users.diller_ids_for_client(client_name), text, reply_markup, sound=sound)
