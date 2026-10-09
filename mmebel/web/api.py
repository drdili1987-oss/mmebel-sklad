"""Panel uchun REST API. Har bir so'rov Telegram imzosi bilan tasdiqlanadi va rol bo'yicha cheklanadi."""
from __future__ import annotations

import functools
import logging
import time
from collections import defaultdict, deque

from aiohttp import web

from ..constants import (
    ACTIVE_STATUSES,
    DELIVERED_STATUSES,
    PANEL_ROLES,
    ROLE_ADMIN,
    ROLE_LABELS,
    ROLE_OMBORCHI,
    ROLE_XODIM,
    SELF_PICKUP_DRIVER,
    ST_CANCELLED,
    ST_SETTLED,
)
from ..services import Conflict, NotFound, ServiceError
from ..services.finance import order_client, order_gross
from ..utils import is_overdue, iter_records, last_months, money, parse_date, to_int
from .auth import AuthError, validate_init_data

log = logging.getLogger(__name__)
routes = web.RouteTableDef()

PRICE_FIELDS = ("price", "total_price")
RATE_LIMIT = 120  # so'rov / daqiqa / foydalanuvchi


class RateLimiter:
    def __init__(self, limit: int, window: float = 60.0):
        self.limit, self.window = limit, window
        self.hits: dict[int, deque] = defaultdict(deque)

    def allow(self, key: int) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def _json_error(status: int, message: str) -> web.Response:
    return web.json_response({"error": message}, status=status)


@web.middleware
async def api_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)
    services = request.app["services"]
    settings = request.app["settings"]
    header = request.headers.get("Authorization", "")
    init_data = header[4:] if header.startswith("tma ") else ""
    try:
        user = validate_init_data(init_data, settings.api_token)
    except AuthError as e:
        return _json_error(401, f"Avtorizatsiya xatosi: {e}. Panelni bot orqali qayta oching.")
    if not request.app["limiter"].allow(user.id):
        return _json_error(429, "Juda ko'p so'rov. Bir daqiqadan so'ng urinib ko'ring.")
    role = await services.users.role(user.id)
    if role not in PANEL_ROLES:
        return _json_error(403, "Panel faqat admin, omborchi va xodimlar uchun.")
    request["user"] = user
    request["role"] = role
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except NotFound as e:
        return _json_error(404, str(e))
    except Conflict as e:
        return _json_error(409, str(e))
    except ServiceError as e:
        return _json_error(400, str(e))
    except Exception:  # noqa: BLE001
        log.exception("API xatosi: %s %s", request.method, request.path)
        return _json_error(500, "Server xatosi. Keyinroq urinib ko'ring.")


def requires(*roles: str):
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(request: web.Request):
            if request["role"] not in roles:
                return _json_error(403, "Bu amal uchun ruxsatingiz yo'q.")
            return await fn(request)
        return wrapper
    return deco


async def body(request: web.Request) -> dict:
    try:
        data = await request.json()
    except Exception as e:  # noqa: BLE001
        raise ServiceError("So'rov tanasi JSON bo'lishi kerak.") from e
    if not isinstance(data, dict):
        raise ServiceError("So'rov tanasi obyekt bo'lishi kerak.")
    return data


def S(request):  # noqa: N802
    return request.app["services"]


def E(request):  # noqa: N802
    return request.app["events"]


def actor(request) -> int:
    return request["user"].id


def order_out(oid: str, o: dict, role: str) -> dict:
    out = {k: v for k, v in o.items() if not k.startswith("_")}
    out["id"] = oid
    out["client_name"] = order_client(o)
    out["amount"] = to_int(o.get("amount"), 1)
    out["overdue"] = is_overdue(o.get("due_date"), o.get("status", ""), ACTIVE_STATUSES)
    if role == ROLE_ADMIN:
        out["total_price"] = order_gross(o)
    else:
        for f in PRICE_FIELDS + ("pickup_discount", "delivery_price"):
            out.pop(f, None)
    for f in ("created_by", "delivered_by", "ready_by", "cancelled_by", "client_tg_id"):
        out.pop(f, None)
    return out


# ================= umumiy =================
@routes.get("/api/me")
async def me(request):
    u = request["user"]
    role = request["role"]
    s = await S(request).catalog.settings()
    meta = {"models": s["models"], "statuses": {"active": sorted(ACTIVE_STATUSES)}}
    if role in (ROLE_ADMIN, ROLE_OMBORCHI):
        meta.update(drivers=s["drivers"], delivery_prices=s["delivery_prices"],
                    pickup_discounts=s["pickup_discounts"], self_pickup=SELF_PICKUP_DRIVER)
    if role == ROLE_ADMIN:
        meta.update(clients=s["clients"], months=last_months(12), roles=ROLE_LABELS)
    elif role == ROLE_OMBORCHI:
        meta.update(months=last_months(12))
    return web.json_response({"id": u.id, "name": u.full_name, "username": u.username,
                              "role": role, "role_label": ROLE_LABELS[role], "meta": meta})


@routes.get("/api/dashboard")
async def dashboard(request):
    stats = await S(request).reports.dashboard()
    if request["role"] != ROLE_ADMIN:
        for k in ("revenue_month", "pending_payments"):
            stats.pop(k, None)
    return web.json_response(stats)


# ================= buyurtmalar =================
@routes.get("/api/orders")
async def orders_list(request):
    role = request["role"]
    scope = request.query.get("scope", "active")
    month = request.query.get("month", "")
    if role == ROLE_XODIM:
        scope = "active"
    rows = await S(request).orders.all()
    out = []
    for oid, o in rows.items():
        st = o.get("status", "")
        if scope == "active" and st not in ACTIVE_STATUSES:
            continue
        if scope == "done" and st not in DELIVERED_STATUSES and st != ST_SETTLED:
            continue
        if scope == "cancelled" and st != ST_CANCELLED:
            continue
        if scope == "overdue" and not is_overdue(o.get("due_date"), st, ACTIVE_STATUSES):
            continue
        if month and not str(o.get("created_at", "")).startswith(month):
            continue
        out.append(order_out(oid, o, role))
    if scope in ("active", "overdue"):
        out.sort(key=lambda r: (parse_date(r.get("due_date")) or parse_date("01.01.2100"), r.get("created_at", "")))
    else:
        out.sort(key=lambda r: r.get("delivered_at") or r.get("created_at", ""), reverse=True)
    limit = min(to_int(request.query.get("limit"), 500) or 500, 2000)
    return web.json_response({"items": out[:limit], "total": len(out)})


@routes.get("/api/orders/{oid}")
async def order_get(request):
    oid = request.match_info["oid"]
    o = await S(request).orders.get(oid)
    if request["role"] == ROLE_XODIM and o.get("status") not in ACTIVE_STATUSES:
        raise NotFound("Buyurtma topilmadi.")
    return web.json_response(order_out(oid, o, request["role"]))


@routes.post("/api/orders")
@requires(ROLE_ADMIN)
async def order_create(request):
    d = await body(request)
    o = await S(request).orders.create(
        actor(request), client_name=d.get("client_name", ""), product=d.get("product", ""),
        amount=d.get("amount"), due_date=d.get("due_date", ""), comment=d.get("comment", ""),
        source="admin", custom_price=d.get("price"),
    )
    if d.get("new_client"):
        await S(request).catalog.add_client_if_missing(o["client_name"])
    await E(request).order_created(o, actor(request))
    return web.json_response(order_out(o["order_id"], o, request["role"]), status=201)


@routes.patch("/api/orders/{oid}")
@requires(ROLE_ADMIN)
async def order_edit(request):
    oid = request.match_info["oid"]
    d = await body(request)
    o = await S(request).orders.edit(actor(request), oid, amount=d.get("amount"), due_date=d.get("due_date"),
                                     comment=d.get("comment"))
    await E(request).order_edited(oid, o, actor(request))
    return web.json_response(order_out(oid, o, request["role"]))


@routes.post("/api/orders/{oid}/ready")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_ready(request):
    oid = request.match_info["oid"]
    o = await S(request).orders.set_ready(actor(request), oid)
    await E(request).order_ready(oid, o, actor(request))
    return web.json_response(order_out(oid, o, request["role"]))


@routes.post("/api/orders/{oid}/unready")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_unready(request):
    oid = request.match_info["oid"]
    o = await S(request).orders.set_preparing(actor(request), oid)
    return web.json_response(order_out(oid, o, request["role"]))


@routes.post("/api/orders/{oid}/deliver")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_deliver(request):
    oid = request.match_info["oid"]
    d = await body(request)
    o = await S(request).orders.deliver(actor(request), oid, driver=str(d.get("driver", "")), price=d.get("price", 0))
    await E(request).order_delivered(oid, o, actor(request))
    return web.json_response(order_out(oid, o, request["role"]))


@routes.post("/api/orders/{oid}/cancel")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def order_cancel(request):
    oid = request.match_info["oid"]
    o = await S(request).orders.cancel(actor(request), oid)
    await E(request).order_cancelled(oid, o, actor(request))
    return web.json_response(order_out(oid, o, request["role"]))


@routes.get("/api/production")
async def production(request):
    return web.json_response({"items": await S(request).reports.production_plan()})


# ================= ombor =================
@routes.get("/api/products")
async def products(request):
    role = request["role"]
    items = []
    for pid, p in (await S(request).inventory.all()).items():
        row = {"id": pid, "name": p.get("nomi", pid), "model": p.get("modeli", ""),
               "qty": to_int(p.get("soni")), "image": p.get("rasm", "")}
        if role == ROLE_ADMIN:
            row["price"] = money(p.get("narxi") or 0)
        items.append(row)
    items.sort(key=lambda r: r["name"])
    return web.json_response({"items": items})


@routes.post("/api/products")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def product_upsert(request):
    d = await body(request)
    price = d.get("price") if request["role"] == ROLE_ADMIN else None
    rec = await S(request).inventory.upsert(actor(request), name=d.get("name", ""), model=d.get("model", ""),
                                            price=price, quantity=d.get("qty"), image=d.get("image", ""))
    if request["role"] != ROLE_ADMIN:
        rec.pop("narxi", None)
    return web.json_response(rec, status=201)


@routes.put("/api/products/{pid}/qty")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def product_qty(request):
    d = await body(request)
    q = d.get("qty")
    if isinstance(q, bool) or not isinstance(q, int):
        raise ServiceError("Soni butun son bo'lishi kerak.")
    qty = await S(request).inventory.set_quantity(actor(request), request.match_info["pid"], q)
    return web.json_response({"qty": qty})


@routes.put("/api/products/{pid}/price")
@requires(ROLE_ADMIN)
async def product_price(request):
    d = await body(request)
    price = await S(request).inventory.set_price(actor(request), request.match_info["pid"], d.get("price"))
    return web.json_response({"price": price})


@routes.delete("/api/products/{pid}")
@requires(ROLE_ADMIN)
async def product_delete(request):
    await S(request).inventory.delete(actor(request), request.match_info["pid"])
    return web.json_response({"ok": True})


# ================= yetkazishlar =================
@routes.get("/api/deliveries")
@requires(ROLE_ADMIN, ROLE_OMBORCHI)
async def deliveries(request):
    month = request.query.get("month") or last_months(1)[0]
    if month not in last_months(36):
        raise ServiceError("Oy noto'g'ri.")
    rows = await S(request).reports.deliveries(month)
    return web.json_response({"month": month, "items": rows, "totals": S(request).reports.delivery_totals(rows)})


# ================= moliya (admin) =================
@routes.get("/api/debts")
@requires(ROLE_ADMIN)
async def debts(request):
    return web.json_response({"items": await S(request).finance.all_debts()})


@routes.get("/api/accounts/{client}")
@requires(ROLE_ADMIN)
async def account(request):
    client = request.match_info["client"]
    acc = await S(request).finance.account(client)
    return web.json_response({**acc.to_dict(), "history": (await S(request).finance.history(client))[:200],
                              "transactions": (await S(request).finance.client_transactions(client))[:200]})


@routes.post("/api/accounts/{client}/settle")
@requires(ROLE_ADMIN)
async def account_settle(request):
    d = await body(request)
    res = await S(request).finance.settle_order(actor(request), request.match_info["client"], str(d.get("order_id", "")))
    return web.json_response(res)


@routes.post("/api/accounts/{client}/partial")
@requires(ROLE_ADMIN)
async def account_partial(request):
    d = await body(request)
    debt = await S(request).finance.partial_payment(actor(request), request.match_info["client"], d.get("amount"),
                                                    order_id=d.get("order_id") or None, note=d.get("note", ""))
    return web.json_response({"debt": debt})


@routes.post("/api/accounts/{client}/settle_all")
@requires(ROLE_ADMIN)
async def account_settle_all(request):
    return web.json_response(await S(request).finance.settle_all(actor(request), request.match_info["client"]))


@routes.get("/api/payments")
@requires(ROLE_ADMIN)
async def payments(request):
    return web.json_response({"items": await S(request).finance.pending_payments()})


@routes.post("/api/payments/{pay_id}/resolve")
@requires(ROLE_ADMIN)
async def payment_resolve(request):
    d = await body(request)
    approve = bool(d.get("approve"))
    pay, debt = await S(request).finance.resolve_payment(actor(request), request.match_info["pay_id"], approve)
    await E(request).payment_resolved(pay, approve, debt, actor(request))
    return web.json_response({"ok": True, "debt": debt})


@routes.get("/api/drivers")
@requires(ROLE_ADMIN)
async def drivers(request):
    month = last_months(1)[0]
    totals = S(request).reports.delivery_totals(await S(request).reports.deliveries(month))
    stats = {d["driver"]: d for d in totals["drivers"]}
    items = []
    for b in await S(request).finance.driver_balances():
        s = stats.get(b["driver"], {})
        items.append({**b, "month_count": s.get("count", 0), "month_sum": s.get("sum", 0)})
    return web.json_response({"month": month, "items": items})


@routes.get("/api/drivers/{name}")
@requires(ROLE_ADMIN)
async def driver_detail(request):
    name = request.match_info["name"]
    return web.json_response({
        "driver": name,
        "balance": await S(request).finance.driver_balance(name),
        "history": (await S(request).finance.driver_history(name))[:200],
        "deliveries": await S(request).reports.driver_deliveries(name),
    })


@routes.post("/api/drivers/{name}/payment")
@requires(ROLE_ADMIN)
async def driver_payment(request):
    d = await body(request)
    bal = await S(request).finance.driver_payment(actor(request), request.match_info["name"], d.get("amount"),
                                                  str(d.get("direction", "")))
    return web.json_response({"balance": bal})


@routes.get("/api/sales")
@requires(ROLE_ADMIN)
async def sales(request):
    return web.json_response({"items": await S(request).reports.sales(12)})


# ================= foydalanuvchilar va sozlamalar (admin) =================
@routes.get("/api/users")
@requires(ROLE_ADMIN)
async def users(request):
    return web.json_response({"items": await S(request).users.list()})


@routes.post("/api/users")
@requires(ROLE_ADMIN)
async def user_set(request):
    d = await body(request)
    await S(request).users.set_role(actor(request), str(d.get("id", "")), str(d.get("role", "")),
                                    str(d.get("client_name", "")))
    return web.json_response({"ok": True})


@routes.delete("/api/users/{uid}")
@requires(ROLE_ADMIN)
async def user_revoke(request):
    await S(request).users.remove(actor(request), request.match_info["uid"])
    return web.json_response({"ok": True})


@routes.get("/api/settings")
@requires(ROLE_ADMIN)
async def settings_get(request):
    return web.json_response(await S(request).catalog.settings(fresh=True))


@routes.put("/api/settings/{key}")
@requires(ROLE_ADMIN)
async def settings_put(request):
    d = await body(request)
    items = d.get("items")
    if not isinstance(items, list):
        raise ServiceError("items ro'yxat bo'lishi kerak.")
    saved = await S(request).catalog.set_list(request.match_info["key"], [str(x) for x in items], actor(request))
    return web.json_response({"items": saved})


@routes.get("/api/audit")
@requires(ROLE_ADMIN)
async def audit(request):
    raw = await S(request).store.get_last("audit_log", 200) or {}
    rows = [dict(v, id=k) for k, v in iter_records(raw)]
    rows.sort(key=lambda r: r.get("at", ""), reverse=True)
    return web.json_response({"items": rows[:200]})


__all__ = ["routes", "api_middleware", "RateLimiter", "RATE_LIMIT"]
