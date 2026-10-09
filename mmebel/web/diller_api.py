"""Diller paneli API. Har bir diller faqat o'z kompaniyasining ma'lumotlarini ko'radi va o'zgartiradi."""
from __future__ import annotations

from aiohttp import web

from ..constants import ACTIVE_STATUSES, DELIVERED_STATUSES, ST_PREPARING, ST_SETTLED
from ..services import ServiceError
from ..services.finance import order_gross
from ..utils import is_overdue, money, product_key, to_int
from .api import body

routes = web.RouteTableDef()


def S(request):  # noqa: N802
    return request.app["services"]


async def company(request) -> str:
    name = await S(request).users.client_name_for(request["user"].id)
    if not name:
        raise ServiceError("Sizga kompaniya (diller nomi) biriktirilmagan. Admin bilan bog'laning.")
    return name


def d_order(oid: str, o: dict, me: int) -> dict:
    own = str(o.get("client_tg_id", "")) == str(me)
    st = o.get("status", "")
    return {
        "id": oid,
        "product_id": o.get("product_id", ""),
        "amount": to_int(o.get("amount"), 1),
        "status": st,
        "due_date": o.get("due_date", ""),
        "created_at": o.get("created_at", ""),
        "delivered_at": o.get("delivered_at", ""),
        "comment": o.get("comment", ""),
        "price": money(o.get("price") or 0),
        "total_price": order_gross(o),
        "driver": o.get("driver", ""),
        "own": own,
        "overdue": is_overdue(o.get("due_date"), st, ACTIVE_STATUSES),
        "can_cancel": own and st == ST_PREPARING and o.get("source", "diller") == "diller",
    }


@routes.get("/api/d/catalog")
async def catalog(request):
    s = await S(request).catalog.settings()
    products = await S(request).inventory.all()
    items, seen = [], set()
    for model in s["models"]:
        pid = product_key(model)
        p = products.get(pid) or {}
        seen.add(pid)
        items.append({"id": pid, "name": model, "model": p.get("modeli", ""), "qty": max(0, to_int(p.get("soni"))),
                      "price": money(p.get("narxi") or 0), "image": p.get("rasm", "")})
    for pid, p in products.items():  # ro'yxatda yo'q, lekin omborda bor mebellar
        if pid not in seen and to_int(p.get("soni")) > 0:
            items.append({"id": pid, "name": p.get("nomi", pid), "model": p.get("modeli", ""),
                          "qty": to_int(p.get("soni")), "price": money(p.get("narxi") or 0), "image": p.get("rasm", "")})
    return web.json_response({"items": items, "price_channel": s["price_channel"]})


@routes.get("/api/d/orders")
async def orders(request):
    me = request["user"].id
    rows = await S(request).orders.for_diller(me, await company(request))
    out = [d_order(k, v, me) for k, v in rows]
    return web.json_response({"items": out})


@routes.post("/api/d/orders")
async def create(request):
    me = request["user"]
    client = await company(request)
    d = await body(request)
    o = await S(request).orders.create(me.id, client_name=client, product=str(d.get("product", "")),
                                       amount=d.get("amount"), due_date=str(d.get("due_date", "")),
                                       comment=str(d.get("comment", "")), source="diller", client_tg_id=me.id)
    await request.app["events"].order_created(o, me.id, by_diller=True)
    return web.json_response(d_order(o["order_id"], o, me.id), status=201)


@routes.post("/api/d/orders/{oid}/cancel")
async def cancel(request):
    me = request["user"].id
    oid = request.match_info["oid"]
    o = await S(request).orders.cancel(me, oid, only_preparing=True, owner_tg_id=me)
    await request.app["events"].order_cancelled(oid, o, me, by_diller=True)
    return web.json_response(d_order(oid, o, me))


@routes.get("/api/d/account")
async def account(request):
    client = await company(request)
    acc = await S(request).finance.account(client)
    history = await S(request).finance.history(client)
    payments = [{"date": h.get("accounting_date", ""), "amount": money(h.get("partial_payment") or 0),
                 "note": "To'lov" if not h.get("order_id") else f"To'lov · {h.get('product_id', '')}"}
                for h in history if h.get("accounting_type") == "qisman"]
    settled = [{"date": h.get("accounting_date", ""), "product_id": h.get("product_id", ""),
                "amount": h.get("amount", ""), "total": money(h.get("total_price") or 0)}
               for h in history if h.get("accounting_type") == "toliq"]
    pending = [p for p in await S(request).finance.pending_payments() if p.get("client_name") == client
               and str(p.get("diller_tg_id")) == str(request["user"].id)]
    return web.json_response({
        "client": client, "debt": acc.debt,
        "unsettled": [{k: r[k] for k in ("order_id", "product_id", "amount", "delivered_at", "gross", "discount",
                                          "net", "paid_partial")} for r in acc.unsettled],
        "pending_orders": len(acc.pending),
        "payments": payments[:50], "settled": settled[:50],
        "pending_payments": [{"pay_id": p["pay_id"], "amount": p["amount"], "timestamp": p["timestamp"]} for p in pending],
    })


@routes.post("/api/d/payments")
async def payment(request):
    me = request["user"]
    client = await company(request)
    d = await body(request)
    pay = await S(request).finance.create_pending_payment(me.id, me.full_name or str(me.id), client, d.get("amount"))
    await request.app["events"].payment_requested(pay)
    return web.json_response({"ok": True, "pay_id": pay["pay_id"], "amount": pay["amount"]}, status=201)


@routes.get("/api/d/summary")
async def summary(request):
    me = request["user"].id
    client = await company(request)
    rows = [d_order(k, v, me) for k, v in await S(request).orders.for_diller(me, client)]
    acc = await S(request).finance.account(client, save=False)
    active = [r for r in rows if r["status"] in ACTIVE_STATUSES]
    return web.json_response({
        "client": client,
        "debt": acc.debt,
        "active": len(active),
        "ready": sum(1 for r in active if r["status"] != ST_PREPARING),
        "overdue": sum(1 for r in active if r["overdue"]),
        "delivered": sum(1 for r in rows if r["status"] in DELIVERED_STATUSES or r["status"] == ST_SETTLED),
        "recent": sorted(rows, key=lambda r: r["created_at"], reverse=True)[:6],
    })


__all__ = ["routes"]
