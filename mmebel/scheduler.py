"""Kunlik eslatmalar va zaxira nusxa.

Eski kod eslatmani faqat aynan 09:00 daqiqasida yuborardi — server shu daqiqada uxlab
qolsa (Render free), eslatma umuman ketmasdi. Endi har bir eslatmaning vaqt oynasi bor
va Firebase tranzaksiyasi bilan kuniga faqat bir marta yuboriladi.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import time as dtime, timedelta

import aiohttp
from aiogram.types import FSInputFile

from .constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM, ST_PREPARING, ST_READY
from .utils import format_date, h, has_comment, now, now_str

BACKUP_EXCLUDE = ("fsm", "sessions", "app_login", "push_tokens", "webpush")
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Reminder:
    key: str
    start: dtime
    end: dtime


REMINDERS = (
    Reminder("morning", dtime(9, 0), dtime(12, 0)),
    Reminder("overdue", dtime(15, 0), dtime(18, 0)),
    Reminder("tomorrow", dtime(15, 5), dtime(20, 0)),
)
BACKUP_AT = dtime(23, 50)
ARCHIVE_AT = dtime(3, 0)
RECIPIENT_ROLES = (ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM)


class Scheduler:
    def __init__(self, services, notifier, bot, settings):
        self.services = services
        self.notifier = notifier
        self.bot = bot
        self.settings = settings
        self._tasks: list[asyncio.Task] = []

    # ---------- dedup ----------
    async def claim(self, key: str) -> bool:
        """Bugun `key` hali yuborilmagan bo'lsa, atomik ravishda band qiladi va True qaytaradi."""
        path = f"reminder_sent/{now().strftime('%Y-%m-%d')}/{key}"
        claimed = {"ok": False}

        def tx(cur):
            if cur:
                claimed["ok"] = False
                return cur
            claimed["ok"] = True
            return now_str()

        await self.services.store.transaction(path, tx)
        return claimed["ok"]

    # ---------- matnlar ----------
    async def _undelivered_text(self, header: str) -> str:
        rows = await self.services.reports.due_orders(until_today=True)
        today = now().strftime("%d.%m.%Y")
        if not rows:
            return f"{header}\n📅 Bugun: <b>{today}</b>\n\n✅ Muddati kelgan yoki o'tgan yetkazilmagan zakaz yo'q."
        lines = [f"{header}\n📅 Bugun: <b>{today}</b>\n", f"📦 Jami: <b>{len(rows)} ta</b> zakaz yetkazilmagan\n"]
        for i, (_, o) in enumerate(rows, 1):
            st = o.get("status")
            ic = "🔧" if st == ST_PREPARING else "✅" if st == ST_READY else "🚛"
            lines.append(f"{i}. {ic} <b>{h(o.get('client_name', '?'))}</b> — {h(o.get('product_id', '?'))} "
                         f"({h(o.get('amount', '?'))} ta)\n   📅 {format_date(o.get('due_date'))} · {h(st)}")
            if has_comment(o.get("comment")):
                lines.append(f"   📝 {h(o.get('comment'))}")
        return "\n".join(lines)

    async def _tomorrow_text(self) -> str:
        rows = await self.services.reports.due_orders(tomorrow=True)
        d = (now() + timedelta(days=1)).strftime("%d.%m.%Y")
        if not rows:
            return f"📢 <b>ERTANGI ZAKAZLAR ({d})</b>\n\n✅ Ertaga yetkaziladigan zakaz yo'q."
        lines = [f"📢 <b>ERTANGI ZAKAZLAR ({d})</b>\n"]
        for i, (_, o) in enumerate(rows, 1):
            lines.append(f"{i}. 👤 <b>{h(o.get('client_name', '?'))}</b> — {h(o.get('product_id', '?'))} "
                         f"({h(o.get('amount', '?'))} ta) · {h(o.get('status'))}")
            if has_comment(o.get("comment")):
                lines.append(f"   📝 {h(o.get('comment'))}")
        return "\n".join(lines)

    async def build(self, key: str) -> str:
        if key == "morning":
            return await self._undelivered_text("🌅 <b>ERTALABKI ESLATMA</b>")
        if key == "overdue":
            return await self._undelivered_text("🔴 <b>TUSHKI ESLATMA — YETKAZILMAGAN ZAKAZLAR</b>")
        if key == "tomorrow":
            return await self._tomorrow_text()
        raise ValueError(key)

    async def run_reminder(self, key: str, *, force: bool = False) -> bool:
        if not force and not await self.claim(key):
            return False
        text = await self.build(key)
        sent = await self.notifier.to_roles(RECIPIENT_ROLES, text)
        log.info("Eslatma %s yuborildi: %d ta qabul qiluvchi", key, sent)
        return True

    async def send_all_now(self) -> None:
        for r in REMINDERS:
            await self.run_reminder(r.key, force=True)
            await asyncio.sleep(1)

    async def tick(self) -> None:
        t = now().time()
        for r in REMINDERS:
            if r.start <= t < r.end:
                try:
                    await self.run_reminder(r.key)
                except Exception:  # noqa: BLE001
                    log.exception("Eslatma %s xatosi", r.key)
        if t >= ARCHIVE_AT:
            try:
                if await self.claim("archive"):
                    n = await self.services.orders.archive_old()
                    log.info("Arxivga ko'chirildi: %d ta buyurtma", n)
                    logins, sessions = await self.services.sessions.cleanup()
                    log.info("Tozalandi: %d ta eski kirish so'rovi, %d ta eskirgan sessiya", logins, sessions)
            except Exception:  # noqa: BLE001
                log.exception("Arxiv xatosi")
        if t >= BACKUP_AT:
            try:
                if await self.claim("backup"):
                    await self.send_backup()
            except Exception:  # noqa: BLE001
                log.exception("Backup xatosi")

    # ---------- backup ----------
    async def send_backup(self, only_to: int | None = None) -> None:
        data = await self.services.store.get("") or {}
        # Kirish tokenlari va qurilma ma'lumotlari zaxiraga kirmaydi: fayl Telegram chatlarida yuradi
        for key in BACKUP_EXCLUDE:
            data.pop(key, None)
        fd, path = tempfile.mkstemp(prefix=f"backup_{now().strftime('%Y%m%d_%H%M')}_", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            ids = [only_to] if only_to else await self.services.users.ids_with_roles([ROLE_ADMIN])
            for uid in ids:
                try:
                    await self.bot.send_document(uid, FSInputFile(path, filename=os.path.basename(path)),
                                                 caption="📁 Baza zaxira nusxasi. Ehtiyot qilib saqlang — "
                                                         "baza o'chib ketsa shu fayldan tiklanadi.")
                except Exception as e:  # noqa: BLE001
                    log.warning("Backup %s ga yuborilmadi: %s", uid, e)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    # ---------- fon vazifalari ----------
    async def _loop(self):
        while True:
            try:
                await self.tick()
            except Exception:  # noqa: BLE001
                log.exception("Scheduler tick xatosi")
            await asyncio.sleep(60)

    async def _keep_awake(self):
        url = self.settings.public_url + "/health"
        while True:
            await asyncio.sleep(600)
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
                    async with s.get(url) as r:
                        await r.read()
            except Exception as e:  # noqa: BLE001
                log.debug("keep-awake: %s", e)

    def start(self):
        self._tasks.append(asyncio.create_task(self._loop()))
        if self.settings.keep_awake and self.settings.public_url:
            self._tasks.append(asyncio.create_task(self._keep_awake()))

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
