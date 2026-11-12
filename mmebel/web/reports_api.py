"""Yetkazilgan mebellar hisoboti (admin): ro'yxat (nusxa olish), PDF va CSV.

Fayl Telegram/Android ilova ichida Authorization sarlavhasisiz ochilishi kerak, shuning uchun
avval qisqa muddatli bir martalik havola olinadi: POST /api/reports/delivered/link -> /files/report/{token}.
"""
from __future__ import annotations

import secrets
import time
from datetime import date

from aiohttp import web

from ..constants import ROLE_ADMIN
from ..services import NotFound, ServiceError
from ..services.delivered_report import as_csv, as_pdf, as_text, delivered_rows
from ..utils import is_valid_key, now, parse_date
from .api import actor, body, requires

routes = web.RouteTableDef()
LINK_TTL = 300


def _params(src) -> dict:
    client = str(src.get("client", "")).strip()
    if not client or not is_valid_key(client):
        raise ServiceError("Dillerni tanlang.")
    start = parse_date(src.get("from")) if src.get("from") else None
    end = parse_date(src.get("to")) if src.get("to") else None
    if (src.get("from") and not start) or (src.get("to") and not end):
        raise ServiceError("Sana noto'g'ri.")
    if start and end and start > end:
        raise ServiceError("Boshlanish sanasi tugash sanasidan keyin bo'lmasin.")
    unsettled = str(src.get("unsettled", "")).lower() in ("1", "true", "yes")
    return {"client": client, "from": start.isoformat() if start else "", "to": end.isoformat() if end else "",
            "unsettled": unsettled}


async def _rows(services, p: dict) -> list[dict]:
    return await delivered_rows(services, client=p["client"],
                                start=date.fromisoformat(p["from"]) if p["from"] else None,
                                end=date.fromisoformat(p["to"]) if p["to"] else None,
                                unsettled_only=p["unsettled"])


def _subtitle(p: dict, n: int) -> str:
    period = (f"{p['from'] or '…'} — {p['to'] or '…'}" if p["from"] or p["to"] else "barcha davr")
    kind = "hisob-kitob qilinmaganlar" if p["unsettled"] else "yetkazilganlar"
    return f"{p['client']} · {kind} · {period} · {n} ta"


@routes.get("/api/reports/delivered")
@requires(ROLE_ADMIN)
async def delivered(request):
    p = _params(request.query)
    rows = await _rows(request.app["services"], p)
    return web.json_response({"items": rows, "text": as_text(rows), "subtitle": _subtitle(p, len(rows))})


@routes.post("/api/reports/delivered/link")
@requires(ROLE_ADMIN)
async def delivered_link(request):
    d = await body(request)
    p = _params(d)
    fmt = str(d.get("format", "pdf"))
    if fmt not in ("pdf", "csv"):
        raise ServiceError("Format: pdf yoki csv.")
    token = secrets.token_urlsafe(24)
    await request.app["services"].store.set(f"report_links/{token}", {**p, "format": fmt, "by": str(actor(request)),
                                                                        "exp": int(time.time()) + LINK_TTL})
    return web.json_response({"url": f"/files/report/{token}", "expires_in": LINK_TTL})


@routes.get("/files/report/{token}")
async def delivered_file(request):
    token = request.match_info["token"]
    store = request.app["services"].store
    rec = await store.get(f"report_links/{token}") if is_valid_key(token) and len(token) >= 20 else None
    if not isinstance(rec, dict) or rec.get("exp", 0) < time.time():
        raise web.HTTPNotFound(text="Havola eskirgan. Ilovada qayta yuklab oling.")
    rows = await _rows(request.app["services"], rec)
    stamp = now().strftime("%Y%m%d")
    safe = "".join(ch for ch in rec["client"] if ch.isascii() and ch.isalnum()) or "diller"
    if rec["format"] == "csv":
        data, ctype, name = as_csv(rows), "text/csv; charset=utf-8", f"{safe}_yetkazilgan_{stamp}.csv"
    else:
        data = as_pdf(rows, title="Yetkazilgan mebellar", subtitle=_subtitle(rec, len(rows)))
        ctype, name = "application/pdf", f"{safe}_yetkazilgan_{stamp}.pdf"
    return web.Response(body=data, headers={
        "Content-Type": ctype, "Content-Disposition": f'attachment; filename="{name}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


async def cleanup_links(store) -> int:
    raw = await store.get("report_links") or {}
    now = time.time()
    old = {f"report_links/{k}": None for k, v in (raw.items() if isinstance(raw, dict) else [])
           if not isinstance(v, dict) or v.get("exp", 0) < now}
    if old:
        await store.update("", old)
    return len(old)


__all__ = ["routes", "cleanup_links", "NotFound"]
