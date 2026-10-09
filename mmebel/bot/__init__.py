"""Telegram bot: dispatcher yig'ish."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .handlers import admin, common, diller, warehouse, worker
from .middlewares import ContextMiddleware
from .storage import PersistentStorage


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML,
                                                          link_preview_is_disabled=True))


def create_dispatcher(services, notifier, events, settings, scheduler, storage=None) -> Dispatcher:
    dp = Dispatcher(storage=storage or PersistentStorage(services.store))
    dp["services"] = services
    dp["notifier"] = notifier
    dp["events"] = events
    dp["settings"] = settings
    dp["scheduler"] = scheduler
    ctx = ContextMiddleware()
    dp.message.outer_middleware(ctx)
    dp.callback_query.outer_middleware(ctx)
    # Tartib muhim: umumiy -> rolga xos -> fallback
    routers = [common.router, admin.router, warehouse.router, worker.router, diller.router]
    for r in routers:  # modul darajasidagi routerlar faqat bitta dispatcherga ulanadi (testlarda qayta yig'iladi)
        r._parent_router = None
    dp.include_routers(*routers, common.fallback_router())
    return dp
