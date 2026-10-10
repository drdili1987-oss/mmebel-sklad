"""HTTP server: Telegram webhook, panel (Mini App), API, cron va health endpointlari."""
from __future__ import annotations

import asyncio
import hmac
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from .bot import create_bot, create_dispatcher
from .config import Settings, load_settings
from .events import Events
from .notify import Notifier
from .scheduler import Scheduler
from .services import Services
from .store import Store, init_firebase
from .web.api import AUTH_GLOBAL_LIMIT, RATE_LIMIT, AuthLimiter, RateLimiter, api_middleware, routes as api_routes

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"

CSP = ("default-src 'self'; script-src 'self' https://telegram.org; style-src 'self'; "
       "img-src 'self' https: data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
       "form-action 'self'; frame-ancestors https://web.telegram.org https://*.telegram.org")


@web.middleware
async def security_headers(request: web.Request, handler):
    resp = await handler(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path.startswith("/panel") or request.path.startswith("/api/"):
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("Cache-Control", "no-store")
    return resp


def _cron_authorized(request: web.Request, settings: Settings) -> bool:
    if not settings.cron_secret:
        return False
    given = request.headers.get("X-Cron-Secret") or request.query.get("key", "")
    return hmac.compare_digest(given.encode(), settings.cron_secret.encode())


def build_app(settings: Settings, services: Services, bot: Bot, dp: Dispatcher, scheduler: Scheduler,
              events: Events) -> web.Application:
    app = web.Application(middlewares=[security_headers, api_middleware], client_max_size=256 * 1024)
    app["settings"] = settings
    app["services"] = services
    app["events"] = events
    app["limiter"] = RateLimiter(RATE_LIMIT)
    app["auth_limiter"] = AuthLimiter()
    app["auth_global"] = RateLimiter(AUTH_GLOBAL_LIMIT)
    _username: dict = {}

    async def bot_username() -> str:
        if "v" not in _username:
            _username["v"] = (await bot.me()).username
        return _username["v"]

    app["bot_username"] = bot_username

    async def health(_):
        return web.json_response({"ok": True})

    async def root(_):
        return web.Response(text="MMebel bot ishlayapti")

    async def cron(request: web.Request):
        if not _cron_authorized(request, settings):
            raise web.HTTPNotFound()
        kind = request.match_info["kind"]
        if kind == "backup":
            sent = await scheduler.claim("backup")
            if sent:
                await scheduler.send_backup()
            return web.json_response({"ok": True, "sent": sent})
        if kind not in ("morning", "overdue", "tomorrow"):
            raise web.HTTPNotFound()
        sent = await scheduler.run_reminder(kind)
        return web.json_response({"ok": True, "sent": sent})

    async def panel_index(_):
        return web.FileResponse(STATIC_DIR / "index.html")

    async def panel_redirect(_):
        raise web.HTTPFound("/panel/")

    app.router.add_get("/", root)
    app.router.add_get("/health", health)
    app.router.add_get("/cron/{kind}", cron)
    app.router.add_post("/cron/{kind}", cron)
    app.router.add_get("/panel", panel_redirect)
    app.router.add_get("/panel/", panel_index)

    async def dashboard_page(_):
        return web.FileResponse(STATIC_DIR / "dashboard.html")

    app.router.add_get("/panel/dashboard", dashboard_page)

    async def service_worker(_):
        # /panel/ ostida bo'lishi shart: SW faqat o'z papkasi va undan pastini boshqaradi
        resp = web.FileResponse(STATIC_DIR / "sw.js")
        resp.content_type = "text/javascript"
        return resp

    async def manifest(_):
        resp = web.FileResponse(STATIC_DIR / "manifest.webmanifest")
        resp.content_type = "application/manifest+json"
        return resp

    app.router.add_get("/panel/sw.js", service_worker)
    app.router.add_get("/panel/manifest.webmanifest", manifest)
    app.router.add_static("/panel/static/", STATIC_DIR, show_index=False, follow_symlinks=False)
    app.add_routes(api_routes)
    from .web.diller_api import routes as diller_routes
    app.add_routes(diller_routes)

    if not settings.use_polling:
        SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.webhook_secret).register(
            app, path=settings.webhook_path)
        setup_application(app, dp, bot=bot)
    return app


async def configure_bot(bot: Bot, settings: Settings) -> None:
    await bot.set_my_commands([BotCommand(command="start", description="Bosh menyu"),
                               BotCommand(command="id", description="Telegram ID ni ko'rish")])
    if settings.use_polling:
        await bot.delete_webhook(drop_pending_updates=False)
        return
    if not settings.webhook_url:
        raise RuntimeError("PUBLIC_URL (yoki RENDER_EXTERNAL_URL) o'rnatilmagan — webhook manzili noma'lum.")
    await bot.set_webhook(settings.webhook_url, secret_token=settings.webhook_secret,
                          allowed_updates=["message", "callback_query"], drop_pending_updates=False)
    log.info("Webhook o'rnatildi: %s", settings.webhook_url)


def assemble(settings: Settings, store: Store):
    services = Services(store, owner_ids=settings.owner_ids)
    from .push import FCMSender
    from .store import FirebaseStore
    if isinstance(store, FirebaseStore):
        services.push.sender = FCMSender()
    if settings.vapid_private_key:
        from .webpush import VapidKey, WebPushSender
        subject = settings.public_url or "https://mmebel-bot.onrender.com"
        services.push.web = WebPushSender(VapidKey(settings.vapid_private_key), subject)
    bot = create_bot(settings.api_token)
    notifier = Notifier(bot, services.users, push=services.push)
    events = Events(notifier)
    scheduler = Scheduler(services, notifier, bot, settings)
    dp = create_dispatcher(services, notifier, events, settings, scheduler)
    return services, bot, dp, scheduler, events


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    store = init_firebase(settings)
    services, bot, dp, scheduler, events = assemble(settings, store)
    await services.catalog.run_migrations()
    if settings.role_assign:
        done = await services.users.apply_role_assignments(settings.role_assign)
        if done:
            log.info("ROLE_ASSIGN qo'llandi: %s", ", ".join(done))
    await configure_bot(bot, settings)

    app = build_app(settings, services, bot, dp, scheduler, events)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", settings.port).start()
    log.info("Server %s-portda ishga tushdi", settings.port)
    scheduler.start()
    try:
        if settings.use_polling:
            await dp.start_polling(bot)
        else:
            await asyncio.Event().wait()
    finally:
        await scheduler.stop()
        await runner.cleanup()
        await bot.session.close()
