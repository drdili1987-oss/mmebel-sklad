"""Hisobotlar va statistika."""
from __future__ import annotations

from collections import defaultdict

from ..constants import (
    ACTIVE_STATUSES,
    DELIVERED_STATUSES,
    ST_CANCELLED,
    ST_PREPARING,
    ST_READY,
    ST_SETTLED,
)
from ..store import Store
from ..utils import is_overdue, iter_records, money, now, parse_date, parse_number
from .finance import order_amount, order_client, order_gross


class ReportService:
    def __init__(self, store: Store, finance):
        self.store = store
        self.finance = finance

    async def _orders(self) -> dict:
        return {k: v for k, v in iter_records(await self.store.get("orders") or {})}

    async def _orders_with_archive(self) -> dict:
        out: dict = {}
        arch = await self.store.get("orders_archive") or {}
        if isinstance(arch, dict):
            for month in arch.values():
                out.update({k: v for k, v in iter_records(month)})
        out.update(await self._orders())
        return out

    async def dashboard(self) -> dict:
        orders = await self._orders()
        products = {k: v for k, v in iter_records(await self.store.get("mebellar") or {})}
        today = now().date()
        cur_month = now().strftime("%Y-%m")
        stats = {"active": 0, "preparing": 0, "ready": 0, "overdue": 0, "due_today": 0,
                 "due_tomorrow": 0, "delivered_month": 0, "revenue_month": 0.0, "orders_month": 0}
        for o in orders.values():
            st = o.get("status", "")
            if st in ACTIVE_STATUSES:
                stats["active"] += 1
                stats["preparing"] += st == ST_PREPARING
                stats["ready"] += st == ST_READY
                d = parse_date(o.get("due_date"))
                if d:
                    stats["overdue"] += d < today
                    stats["due_today"] += d == today
                    stats["due_tomorrow"] += (d - today).days == 1
            if str(o.get("created_at", "")).startswith(cur_month) and st != ST_CANCELLED:
                stats["orders_month"] += 1
                stats["revenue_month"] += order_gross(o, products)
            if (st in DELIVERED_STATUSES or st == ST_SETTLED) and str(o.get("delivered_at", "")).startswith(cur_month):
                stats["delivered_month"] += 1
        stats["revenue_month"] = money(stats["revenue_month"])
        stock_total = sum(max(0, int(parse_number(p.get("soni"), 0) or 0)) for p in products.values())
        stats["stock_total"] = stock_total
        stats["products"] = len(products)
        stats["pending_payments"] = len(await self.finance.pending_payments())
        return stats

    async def deliveries(self, month: str) -> list[dict]:
        """Oy bo'yicha yetkazishlar (deliveries jadvali + yozuvi yo'q eski buyurtmalar)."""
        raw = await self.store.get(f"deliveries/{month}") or {}
        rows = [dict(d, id=k) for k, d in iter_records(raw)]
        seen = {r.get("order_id") for r in rows}
        orders = await self._orders_with_archive()
        for oid, o in orders.items():
            if oid in seen or o.get("month") != month or o.get("status") not in DELIVERED_STATUSES:
                continue
            rows.append({
                "id": oid, "order_id": oid, "client": order_client(o), "product_id": o.get("product_id", ""),
                "amount": o.get("amount", 1), "driver": o.get("driver") or "O'zi olib ketdi",
                "price": o.get("delivery_price", "0"), "comment": o.get("comment", ""),
                "timestamp": o.get("delivered_at") or o.get("created_at", ""),
            })
        for r in rows:
            o = orders.get(r.get("order_id", ""), {})
            r["order_created"] = o.get("created_at", "")
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return rows

    @staticmethod
    def delivery_totals(rows: list[dict]) -> dict:
        by_driver: dict[str, dict] = defaultdict(lambda: {"count": 0, "items": 0, "sum": 0.0})
        total = {"count": 0, "items": 0, "sum": 0.0}
        for r in rows:
            fee = parse_number(r.get("price"), 0.0) or 0.0
            items = order_amount(r)
            d = by_driver[r.get("driver") or "—"]
            d["count"] += 1
            d["items"] += items
            d["sum"] += fee
            total["count"] += 1
            total["items"] += items
            total["sum"] += fee
        total["sum"] = money(total["sum"])
        drivers = [{"driver": k, **v, "sum": money(v["sum"])} for k, v in by_driver.items()]
        drivers.sort(key=lambda x: x["count"], reverse=True)
        return {"total": total, "drivers": drivers}

    async def driver_deliveries(self, driver: str) -> dict[str, list[dict]]:
        raw = await self.store.get("deliveries") or {}
        out: dict[str, list[dict]] = {}
        if isinstance(raw, dict):
            for month, items in raw.items():
                for _, d in iter_records(items):
                    if d.get("driver") == driver:
                        out.setdefault(month, []).append(d)
        for v in out.values():
            v.sort(key=lambda d: d.get("timestamp", ""))
        return dict(sorted(out.items(), reverse=True))

    async def sales(self, months: int = 12) -> list[dict]:
        """Oylar kesimida eng ko'p buyurtma qilingan mebellar (bekor qilinganlarsiz)."""
        orders = await self._orders_with_archive()
        stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        revenue: dict[str, float] = defaultdict(float)
        for o in orders.values():
            if o.get("status") == ST_CANCELLED:
                continue
            m = str(o.get("created_at", ""))[:7] or o.get("month") or "Avvalgi"
            stats[m][o.get("product_id", "—")] += order_amount(o)
            revenue[m] += order_gross(o)
        out = []
        for m in sorted(stats, reverse=True)[:months]:
            items = sorted(stats[m].items(), key=lambda x: x[1], reverse=True)
            out.append({"month": m, "total": sum(v for _, v in items), "revenue": money(revenue[m]),
                        "items": [{"product_id": k, "count": v} for k, v in items]})
        return out

    async def production_plan(self) -> list[dict]:
        """Xodimlar uchun: tayyorlanishi kerak bo'lgan mebellar modeli bo'yicha jamlangan."""
        agg: dict[str, dict] = {}
        for o in (await self._orders()).values():
            if o.get("status") != ST_PREPARING:
                continue
            pid = o.get("product_id", "—")
            a = agg.setdefault(pid, {"product_id": pid, "count": 0, "orders": 0, "nearest": None, "overdue": 0})
            a["count"] += order_amount(o)
            a["orders"] += 1
            d = parse_date(o.get("due_date"))
            if d and (a["nearest"] is None or d < a["nearest"]):
                a["nearest"] = d
            a["overdue"] += is_overdue(o.get("due_date"), o.get("status"), ACTIVE_STATUSES)
        rows = list(agg.values())
        rows.sort(key=lambda r: (r["nearest"] is None, r["nearest"] or now().date(), -r["count"]))
        for r in rows:
            r["nearest"] = r["nearest"].strftime("%d.%m.%Y") if r["nearest"] else ""
        return rows

    async def due_orders(self, *, until_today: bool = False, tomorrow: bool = False) -> list[tuple[str, dict]]:
        today = now().date()
        out = []
        for oid, o in (await self._orders()).items():
            if o.get("status") not in ACTIVE_STATUSES:
                continue
            d = parse_date(o.get("due_date"))
            if not d:
                continue
            if until_today and d <= today:
                out.append((oid, o))
            elif tomorrow and (d - today).days == 1:
                out.append((oid, o))
        out.sort(key=lambda kv: (parse_date(kv[1].get("due_date")), kv[1].get("created_at", "")))
        return out


async def admin_dashboard(services) -> dict:
    """Admin dashboard uchun barcha ko'rsatkichlar bitta so'rovda."""
    from datetime import timedelta

    from ..utils import format_date, last_months
    reports, finance = services.reports, services.finance
    today = now().date()
    stats = await reports.dashboard()

    # 12 oylik tushum (bekor qilinganlarsiz, arxiv bilan)
    sales = {m["month"]: m for m in await reports.sales(24)}
    months = list(reversed(last_months(12)))
    revenue = [{"month": m, "revenue": sales.get(m, {}).get("revenue", 0.0),
                "orders": sales.get(m, {}).get("total", 0)} for m in months]
    cur = sales.get(months[-1], {"items": []})
    top_models = cur["items"][:8]

    # So'nggi 30 kun yetkazishlar (kunlar bo'yicha)
    deliveries = []
    for m in last_months(2):
        deliveries += await reports.deliveries(m)
    per_day: dict[str, dict] = {}
    start = today - timedelta(days=29)
    for i in range(30):
        d = start + timedelta(days=i)
        per_day[d.isoformat()] = {"date": d.isoformat(), "count": 0, "items": 0}
    for r in deliveries:
        d = parse_date(r.get("timestamp"))
        if d and d.isoformat() in per_day:
            per_day[d.isoformat()]["count"] += 1
            per_day[d.isoformat()]["items"] += order_amount(r)
    recent = [{"date": format_date(r.get("timestamp")), "client": r.get("client", ""),
               "product_id": r.get("product_id", ""), "amount": order_amount(r), "driver": r.get("driver", "")}
              for r in deliveries[:8]]

    debts = [d for d in await finance.all_debts() if d["debt"] > 0]

    def short(oid, o):
        return {"id": oid, "client": order_client(o), "product_id": o.get("product_id", ""),
                "amount": order_amount(o), "due_date": format_date(o.get("due_date")), "status": o.get("status", "")}

    due = await reports.due_orders(until_today=True)
    overdue = [short(k, v) for k, v in due if (parse_date(v.get("due_date")) or today) < today]
    due_today = [short(k, v) for k, v in due if parse_date(v.get("due_date")) == today]
    tomorrow = [short(k, v) for k, v in await reports.due_orders(tomorrow=True)]

    # Faol buyurtmalar: kechikkan / tayyorlanmoqda / tayyor (har biri faqat bitta guruhda)
    split = {"late": 0, "prep": 0, "ready": 0}
    for o in (await reports._orders()).values():
        st = o.get("status", "")
        if st not in ACTIVE_STATUSES:
            continue
        if is_overdue(o.get("due_date"), st, ACTIVE_STATUSES):
            split["late"] += 1
        elif st == ST_PREPARING:
            split["prep"] += 1
        else:
            split["ready"] += 1
    status_split = [{"key": "prep", "label": "Tayyorlanmoqda", "count": split["prep"]},
                    {"key": "ready", "label": "Tayyor, yetkazilmagan", "count": split["ready"]},
                    {"key": "late", "label": "Muddati o'tgan", "count": split["late"]}]

    products = {k: v for k, v in iter_records(await services.store.get("mebellar") or {})}
    low_stock = sorted(({"id": k, "name": p.get("nomi", k), "qty": int(parse_number(p.get("soni"), 0) or 0)}
                        for k, p in products.items() if int(parse_number(p.get("soni"), 0) or 0) <= 1),
                       key=lambda r: (r["qty"], r["name"]))[:12]

    return {
        "generated_at": now().strftime("%H:%M:%S"),
        "stats": {**stats, "debt_total": money(sum(d["debt"] for d in debts)), "debtors": len(debts)},
        "status": status_split,
        "revenue": revenue,
        "deliveries": list(per_day.values()),
        "top_models": top_models,
        "debts": debts[:10],
        "overdue": overdue[:15],
        "due_today": due_today[:15],
        "tomorrow": tomorrow[:15],
        "low_stock": low_stock,
        "recent": recent,
    }
