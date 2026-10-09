"""Xodim funksiyalari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from ...constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM, ST_PREPARING
from ...utils import chunk_text, h
from .. import keyboards as kb
from ..middlewares import Role
from ..texts import grouped_by_due

router = Router(name="worker")
router.message.filter(Role(ROLE_XODIM, ROLE_ADMIN, ROLE_OMBORCHI))


@router.message(F.text == kb.B_ACTIVE)
async def active_orders(message: Message, services):
    rows = [(k, v) for k, v in await services.orders.active() if v.get("status") == ST_PREPARING]
    if not rows:
        await message.answer("✅ Hozircha tayyorlanadigan buyurtma yo'q.")
        return
    plan = await services.reports.production_plan()
    head = [f"🔨 <b>Tayyorlanishi kerak ({len(rows)} ta buyurtma)</b>\n", "<b>Jami modellar bo'yicha:</b>"]
    for p in plan:
        warn = f" · 🔴 {p['overdue']} ta kechikkan" if p["overdue"] else ""
        head.append(f"  • <b>{h(p['product_id'])}</b> — {p['count']} ta (eng yaqin: {p['nearest']}){warn}")
    text = "\n".join(head) + "\n\n" + grouped_by_due(rows, show_status=False)
    for chunk in chunk_text(text):
        await message.answer(chunk)
