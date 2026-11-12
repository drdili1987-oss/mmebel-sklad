"""Mebel yig'uvchilar API.

/api/w/*          — yig'uvchining o'zi (faqat o'ziga biriktirilgan mebellar va o'z kassasi)
/api/workers*     — admin va omborchi: profillar, kassalar, statistika
/api/cash*        — topshirishlarni tasdiqlash, omborchi kassasi
/api/wphoto/...   — to'lov rasmlari (yig'uvchi faqat o'zinikini, admin/omborchi hammasini ko'radi)
"""
from __future__ import annotations

import io
import logging

from aiohttp import web

from ..constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_YIGUVCHI
from ..services import NotFound, ServiceError
from ..services.finance import order_client
from ..services.workers import MAX_PHOTOS, staff_holder, worker_holder
from ..utils import money, to_int
from .api import actor, body, requires

log = logging.getLogger(__name__)
routes = web.RouteTableDef()

MAX_IMAGE = 5 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
WORKER_PATH_PREFIXES = ("/api/w/", "/api/wphoto/")


def S(request):
    return request.app["services"]


def E(request):
    return request.app["events"]


def w_order(oid: str, o: dict) -> dict:
    """Yig'uvchiga ko'rinadigan buyurtma: diller narxi va ichki maydonlarsiz."""
    hv = o.get("handover") or {}
    return {
        "id": oid, "serial": o.get("serial", ""), "product_id": o.get("product_id", ""),
        "variant": o.get("variant", ""), "amount": to_int(o.get("amount"), 1), "client_name": order_client(o),
        "comment": o.get("comment", ""), "due_date": o.get("due_date", ""), "status": o.get("status", ""),
        "collect": money(o["collect"]) if o.get("collect") not in (None, "") else None,
        "assigned_at": o.get("assigned_at", ""), "delivered_at": o.get("delivered_at", ""),
        "handover": {"at": hv.get("at", ""), "correct": hv.get("correct")} if hv else None,
    }


def pay_out(p: dict) -> dict:
    out = {k: p.get(k) for k in ("pay_id", "order_id", "client", "serial", "product_id", "variant", "worker_id",
                                 "worker_name", "kind", "ts", "correct", "amount", "method", "note", "expected")}
    out["photos"] = len(p.get("photos") or [])
    return out


# ================= yig'uvchi =================
@routes.get("/api/w/me")
@requires(ROLE_YIGUVCHI)
async def w_me(request):
    wid, w = await S(request).workers.require_self(actor(request))
    active, done = await S(request).workers.orders_for(wid)
    holder = worker_holder(wid)
    paid: dict[str, float] = {}
    methods: dict[str, set] = {}
    for p in await S(request).workers.payments(wid=wid):
        paid[p["order_id"]] = money(paid.get(p["order_id"], 0) + (p.get("amount") or 0))
        methods.setdefault(p["order_id"], set()).add(p.get("method", ""))
    pending = [t for t in await S(request).workers.transfers(status="pending") if t.get("from_holder") == holder]
    return web.json_response({
        "worker": {"id": wid, "name": w.get("name", ""), "phone": w.get("phone", "")},
        "cash": await S(request).workers.balance(holder),
        "active": [w_order(k, v) for k, v in active],
        "done": [dict(w_order(k, v), paid=paid.get(k, 0.0), method="+".join(sorted(methods.get(k, set()))))
                 for k, v in done[:60]],
        "log": (await S(request).workers.log(holder))[:100],
        "pending_transfer": pending[0] if pending else None,
    })


@routes.post("/api/w/photos")
@requires(ROLE_YIGUVCHI)
async def w_photo_upload(request):
    """Rasm (JPEG/PNG, ≤5 MB) Telegram'ga saqlanadi; ilovaga faqat kalit qaytadi."""
    await S(request).workers.require_self(actor(request))
    ctype = request.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if ctype not in IMAGE_TYPES:
        raise ServiceError("Faqat JPG yoki PNG rasm yuklash mumkin.")
    if request.content_length and request.content_length > MAX_IMAGE:
        raise ServiceError("Rasm hajmi 5 MB dan oshmasin.")
    data = await request.content.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        raise ServiceError("Rasm hajmi 5 MB dan oshmasin.")
    if len(data) < 100:
        raise ServiceError("Rasm bo'sh.")
    from aiogram.types import BufferedInputFile
    bot = E(request).n.bot
    try:
        msg = await bot.send_photo(actor(request), BufferedInputFile(data, f"tolov.{IMAGE_TYPES[ctype]}"),
                                   caption="📎 To'lov rasmi ilovaga yuklandi", disable_notification=True)
    except Exception as e:
        log.warning("Rasm Telegram'ga yuklanmadi: %s", e)
        raise ServiceError("Rasmni saqlab bo'lmadi. Botga /start yozing va qayta urinib ko'ring.") from e
    key = await S(request).workers.save_upload(actor(request), msg.photo[-1].file_id)
    return web.json_response({"key": key}, status=201)


@routes.post("/api/w/orders/{oid}/handover")
@requires(ROLE_YIGUVCHI)
async def w_handover(request):
    d = await body(request)
    res = await S(request).workers.handover(
        actor(request), request.match_info["oid"], correct=d.get("correct"), amount=d.get("amount"),
        method=str(d.get("method", "")), note=str(d.get("note", "")), photos=d.get("photos"))
    await E(request).order_handover(res)
    return web.json_response({"ok": True, "pay_id": res["pay_id"]})


@routes.post("/api/w/orders/{oid}/payment")
@requires(ROLE_YIGUVCHI)
async def w_extra_payment(request):
    d = await body(request)
    res = await S(request).workers.extra_payment(
        actor(request), request.match_info["oid"], amount=d.get("amount"), method=str(d.get("method", "")),
        note=str(d.get("note", "")), photos=d.get("photos"))
    await E(request).order_handover(res)
    return web.json_response({"ok": True, "pay_id": res["pay_id"]})


@routes.post("/api/w/transfer")
@requires(ROLE_YIGUVCHI)
async def w_transfer(request):
    d = await body(request)
    wid, w = await S(request).workers.require_self(actor(request))
    t = await S(request).workers.request_transfer(holder=worker_holder(wid), from_name=w["name"], from_kind="worker",
                                                  from_uid=actor(request), to_role=str(d.get("to", "")),
                                                  amount=d.get("amount"))
    await E(request).transfer_requested(t)
    return web.json_response(t, status=201)


@routes.get("/api/wphoto/{pid}/{idx}")
async def w_photo(request):
    role = request["role"]
    rec = await S(request).workers.payment(request.match_info["pid"])
    if role == ROLE_YIGUVCHI:
        found = await S(request).workers.by_uid(actor(request))
        if not found or found[0] != rec.get("worker_id"):
            raise NotFound("Rasm topilmadi.")
    elif role not in (ROLE_ADMIN, ROLE_OMBORCHI):
        raise NotFound("Rasm topilmadi.")
    photos = rec.get("photos") or []
    idx = to_int(request.match_info["idx"], -1)
    if not 0 <= idx < len(photos):
        raise NotFound("Rasm topilmadi.")
    bot = E(request).n.bot
    f = await bot.get_file(photos[idx])
    buf = io.BytesIO()
    await bot.download_file(f.file_path, buf)
    return web.Response(body=buf.getvalue(), content_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=86400"})


# ================= admin / omborchi =================
@routes.get("/api/workers")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def workers_list(request):
    summary = await S(request).workers.summary()
    role = request["role"]
    pending = await S(request).workers.transfers(status="pending")
    if role == ROLE_OMBORCHI:
        mine = staff_holder(actor(request))
        summary["staff"] = [s for s in summary["staff"] if s["holder"] == mine]
        pending = [t for t in pending if t.get("to_role") == ROLE_OMBORCHI or t.get("from_holder") == mine]
        summary["my_cash"] = await S(request).workers.balance(mine)
        summary["my_pending"] = next((t for t in pending if t.get("from_holder") == mine), None)
    summary["pending"] = pending
    return web.json_response(summary)


@routes.post("/api/workers")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def worker_create(request):
    d = await body(request)
    wid, rec = await S(request).workers.create(actor(request), str(d.get("name", "")), str(d.get("phone", "")))
    return web.json_response({"id": wid, **rec}, status=201)


@routes.get("/api/workers/{wid}")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def worker_detail(request):
    wid = request.match_info["wid"]
    w = await S(request).workers.get(wid)
    active, done = await S(request).workers.orders_for(wid, days=90)
    return web.json_response({
        "id": wid, **{k: w.get(k) for k in ("name", "phone", "active", "created_at")}, "linked": bool(w.get("uid")),
        "cash": await S(request).workers.balance(worker_holder(wid)),
        "active_orders": [w_order(k, v) for k, v in active],
        "done_orders": [w_order(k, v) for k, v in done[:100]],
        "payments": [pay_out(p) for p in (await S(request).workers.payments(wid=wid))[:100]],
        "log": (await S(request).workers.log(worker_holder(wid)))[:100],
    })


@routes.patch("/api/workers/{wid}")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def worker_update(request):
    d = await body(request)
    active = d.get("active") if isinstance(d.get("active"), bool) else None
    if active is not None and request["role"] != ROLE_ADMIN:
        raise ServiceError("Profilni faqat admin o'chira oladi.")
    w = await S(request).workers.update(actor(request), request.match_info["wid"], name=d.get("name"),
                                        phone=d.get("phone"), active=active)
    return web.json_response(w)


@routes.post("/api/orders/{oid}/assign")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_assign(request):
    d = await body(request)
    oid = request.match_info["oid"]
    o = await S(request).workers.assign(actor(request), oid, str(d.get("worker_id", "")), d.get("fee"))
    await E(request).order_assigned(oid, o, actor(request))
    return web.json_response({"ok": True, "worker_name": o["worker_name"]})


@routes.delete("/api/orders/{oid}/assign")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_unassign(request):
    await S(request).workers.unassign(actor(request), request.match_info["oid"])
    return web.json_response({"ok": True})


@routes.get("/api/orders/{oid}/wpay")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_payments(request):
    rows = await S(request).workers.payments(order_id=request.match_info["oid"])
    return web.json_response({"items": [pay_out(p) for p in rows]})


@routes.post("/api/cash/transfers/{tid}/resolve")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def transfer_resolve(request):
    d = await body(request)
    u = request["user"]
    res = await S(request).workers.resolve_transfer(actor(request), request["role"], u.full_name or str(u.id),
                                                    request.match_info["tid"], d.get("approve") is True)
    await E(request).transfer_resolved(res)
    return web.json_response(res)


@routes.post("/api/cash/transfer")
@requires(ROLE_OMBORCHI)
async def staff_transfer(request):
    """Omborchi o'z kassasidagi pulni adminga topshiradi."""
    d = await body(request)
    u = request["user"]
    t = await S(request).workers.request_transfer(holder=staff_holder(actor(request)), from_name=u.full_name or str(u.id),
                                                  from_kind="omborchi", from_uid=actor(request), to_role=ROLE_ADMIN,
                                                  amount=d.get("amount"))
    await E(request).transfer_requested(t)
    return web.json_response(t, status=201)


@routes.get("/api/cash/{holder}")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def cash_log(request):
    holder = request.match_info["holder"]
    if request["role"] == ROLE_OMBORCHI and holder.startswith("u_") and holder != staff_holder(actor(request)):
        raise NotFound("Topilmadi.")
    if not holder.startswith(("u_", "w_")):
        raise NotFound("Topilmadi.")
    return web.json_response({"balance": await S(request).workers.balance(holder),
                              "log": await S(request).workers.log(holder)})


__all__ = ["MAX_PHOTOS", "WORKER_PATH_PREFIXES", "routes"]
