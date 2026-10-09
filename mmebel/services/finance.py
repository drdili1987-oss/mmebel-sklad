"""Moliya: diller qarzlari, hisob-kitob, to'lovlar, haydovchi balanslari.

Qarz yagona funksiya — `compute_account` orqali hisoblanadi (avval kodda 4 marta takrorlangan edi).
`debts/{mijoz}` tuguni faqat kesh: har o'zgarishdan keyin qayta hisoblab yoziladi.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from ..constants import (
    DEBT_EXCLUDED_STATUSES,
    SELF_PICKUP_DRIVER,
    ST_PREPARING,
    ST_READY,
    ST_SETTLED,
)
from ..store import Store
from ..utils import clean_text, is_valid_key, iter_records, money, now_str, parse_number, product_key
from .errors import Conflict, NotFound, ServiceError, run_tx

MAX_PAYMENT = 10_000_000


def order_client(o: dict) -> str:
    return str(o.get("client_name") or o.get("client") or "").strip()


def order_amount(o: dict) -> int:
    n = parse_number(o.get("amount"))
    return int(n) if n and n > 0 else 1


def order_gross(o: dict, products: dict | None = None) -> float:
    total = parse_number(o.get("total_price"))
    if total:
        return money(total)
    price = parse_number(o.get("price"))
    if price:
        return money(price * order_amount(o))
    if products:
        p = products.get(product_key(o.get("product_id", "")))
        if isinstance(p, dict):
            unit = parse_number(p.get("narxi"))
            if unit:
                return money(unit * order_amount(o))
    return 0.0


def order_discount(o: dict) -> float:
    if o.get("driver") == SELF_PICKUP_DRIVER:
        return money(o.get("pickup_discount") or 0)
    return 0.0


def order_net(o: dict, products: dict | None = None) -> float:
    return money(max(0.0, order_gross(o, products) - order_discount(o)))


@dataclass
class Account:
    client: str
    debt: float = 0.0
    partial_total: float = 0.0
    pending: list[dict] = field(default_factory=list)      # tayyorlanayotgan (qarzga kirmaydi)
    unsettled: list[dict] = field(default_factory=list)    # yetkazilgan, hisob-kitob qilinmagan
    accounted_ids: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {
            "client": self.client,
            "debt": self.debt,
            "partial_total": self.partial_total,
            "pending": self.pending,
            "unsettled": self.unsettled,
        }


def compute_account(client: str, orders: dict, history: dict | None, products: dict | None) -> Account:
    acc = Account(client=client)
    target = client.strip().lower()
    hist = list(iter_records(history or {}))

    for _, h in hist:
        if h.get("accounting_type") == "toliq" and h.get("order_id"):
            acc.accounted_ids.add(str(h["order_id"]))
    partial_by_order: dict[str, float] = {}
    for _, h in hist:
        if h.get("accounting_type") != "qisman" or h.get("settled"):
            continue
        oid = str(h.get("order_id") or "")
        if oid and oid in acc.accounted_ids:
            continue
        amt = money(h.get("partial_payment") or 0)
        acc.partial_total += amt
        if oid:
            partial_by_order[oid] = partial_by_order.get(oid, 0.0) + amt

    total = 0.0
    for oid, o in iter_records(orders or {}):
        if order_client(o).lower() != target:
            continue
        status = o.get("status", "")
        row = {
            "order_id": oid,
            "product_id": o.get("product_id", ""),
            "amount": order_amount(o),
            "status": status,
            "due_date": o.get("due_date", ""),
            "comment": o.get("comment", ""),
            "created_at": o.get("created_at", ""),
            "delivered_at": o.get("delivered_at", ""),
            "driver": o.get("driver", ""),
            "delivery_price": o.get("delivery_price", ""),
            "gross": order_gross(o, products),
            "discount": order_discount(o),
            "net": order_net(o, products),
            "paid_partial": money(partial_by_order.get(oid, 0.0)),
        }
        if status in (ST_PREPARING, ST_READY):
            acc.pending.append(row)
            continue
        if status in DEBT_EXCLUDED_STATUSES or oid in acc.accounted_ids:
            continue
        total += row["net"]
        acc.unsettled.append(row)

    acc.pending.sort(key=lambda r: (r["due_date"] or "", r["created_at"] or ""))
    acc.unsettled.sort(key=lambda r: r["delivered_at"] or r["created_at"] or "", reverse=True)
    acc.partial_total = money(acc.partial_total)
    acc.debt = money(total - acc.partial_total)
    return acc


class FinanceService:
    def __init__(self, store: Store, catalog):
        self.store = store
        self.catalog = catalog

    # ---------- qarzlar ----------
    async def account(self, client: str, *, save: bool = True) -> Account:
        if not is_valid_key(client):
            raise ServiceError("Mijoz nomi noto'g'ri.")
        orders = await self.store.get("orders") or {}
        history = await self.store.get(f"accounting_history/{client}") or {}
        products = await self.store.get("mebellar") or {}
        acc = compute_account(client, orders, history, products)
        if save:
            await self.store.set(f"debts/{client}", acc.debt)
        return acc

    async def recalc(self, client: str) -> float:
        if not client or not is_valid_key(client):
            return 0.0
        return (await self.account(client)).debt

    async def all_debts(self) -> list[dict]:
        orders = await self.store.get("orders") or {}
        history_all = await self.store.get("accounting_history") or {}
        products = await self.store.get("mebellar") or {}
        names = {c: c for c in await self.catalog.clients()}
        for _, o in iter_records(orders):
            c = order_client(o)
            if c and c.lower() not in {n.lower() for n in names}:
                names[c] = c
        out, updates = [], {}
        for client in names:
            if not is_valid_key(client):
                continue
            hist = history_all.get(client) if isinstance(history_all, dict) else None
            acc = compute_account(client, orders, hist, products)
            updates[client] = acc.debt
            out.append({"client": client, "debt": acc.debt, "unsettled": len(acc.unsettled),
                        "pending": len(acc.pending)})
        if updates:
            await self.store.update("debts", updates)
        out.sort(key=lambda r: r["debt"], reverse=True)
        return out

    async def history(self, client: str) -> list[dict]:
        if not is_valid_key(client):
            raise ServiceError("Mijoz nomi noto'g'ri.")
        raw = await self.store.get(f"accounting_history/{client}") or {}
        rows = [dict(v, id=k) for k, v in iter_records(raw)]
        rows.sort(key=lambda r: r.get("accounting_date", ""), reverse=True)
        return rows

    async def settle_order(self, actor_id, client: str, order_id: str) -> dict:
        acc = await self.account(client, save=False)
        row = next((r for r in acc.unsettled if r["order_id"] == order_id), None)
        if not row:
            raise Conflict("Bu buyurtma hisob-kitob uchun mavjud emas (allaqachon yopilgan yoki yetkazilmagan).")

        def tx(cur):
            if cur in DEBT_EXCLUDED_STATUSES:
                raise Conflict("Buyurtma holati o'zgargan, qaytadan oching.")
            return ST_SETTLED

        await run_tx(self.store, f"orders/{order_id}/status", tx)
        order = await self.store.get(f"orders/{order_id}") or {}
        ts = now_str()
        await self.store.push(f"accounting_history/{client}", {
            "order_id": order_id, "client_name": client,
            "product_id": order.get("product_id", ""), "amount": order.get("amount", "1"),
            "due_date": order.get("due_date", ""), "price": order.get("price", 0),
            "total_price": order.get("total_price", 0), "comment": order.get("comment", ""),
            "accounting_type": "toliq", "accounting_date": ts, "status": ST_SETTLED,
            "by": str(actor_id),
        })
        received = money(max(0.0, row["net"] - row["paid_partial"]))
        if received > 0:
            await self.store.push(f"transactions/clients/{client}", {
                "type": "Kirim", "amount": received, "timestamp": ts,
                "note": f"Hisob kitob qilindi: {order_id} ({order.get('product_id', '')})",
            })
        new_debt = await self.recalc(client)
        return {"order_id": order_id, "net": row["net"], "received": received, "debt": new_debt}

    async def partial_payment(self, actor_id, client: str, amount, order_id: str | None = None,
                              note: str = "") -> float:
        amt = parse_number(amount)
        if amt is None or amt <= 0 or amt > MAX_PAYMENT:
            raise ServiceError("To'lov summasi musbat son bo'lishi kerak.")
        amt = money(amt)
        order = {}
        if order_id:
            order = await self.store.get(f"orders/{order_id}") or {}
            if not order or order_client(order).lower() != client.strip().lower():
                raise NotFound("Buyurtma topilmadi.")
        ts = now_str()
        await self.store.push(f"accounting_history/{client}", {
            "order_id": order_id or "", "client_name": client,
            "product_id": order.get("product_id", ""), "amount": order.get("amount", ""),
            "due_date": order.get("due_date", ""), "partial_payment": amt,
            "comment": clean_text(note, 200) or order.get("comment", ""),
            "accounting_type": "qisman", "accounting_date": ts, "status": "Qisman to'ladi",
            "by": str(actor_id),
        })
        await self.store.push(f"transactions/clients/{client}", {
            "type": "Kirim", "amount": amt, "timestamp": ts,
            "note": f"Qisman to'lov: {order_id or 'umumiy'}" + (f" ({order.get('product_id')})" if order else ""),
        })
        return await self.recalc(client)

    async def settle_all(self, actor_id, client: str) -> dict:
        acc = await self.account(client, save=False)
        history = await self.store.get(f"accounting_history/{client}") or {}
        ts = now_str()
        updates: dict = {}
        settled = 0
        for row in acc.unsettled:
            oid = row["order_id"]
            key = self.store.new_key(f"accounting_history/{client}")
            updates[f"accounting_history/{client}/{key}"] = {
                "order_id": oid, "client_name": client, "product_id": row["product_id"],
                "amount": row["amount"], "due_date": row["due_date"], "total_price": row["gross"],
                "comment": row["comment"], "accounting_type": "toliq", "accounting_date": ts,
                "status": ST_SETTLED, "note": "Barchasini hisob kitob qilish", "by": str(actor_id),
            }
            updates[f"orders/{oid}/status"] = ST_SETTLED
            settled += 1
        # Buyurtmaga bog'lanmagan qisman to'lovlar ham shu hisob-kitobga kiradi — aks holda qarz manfiy bo'lib qolardi.
        # Hali tayyorlanayotgan buyurtmalar uchun avans to'lovlari saqlanib qoladi.
        pending_ids = {r["order_id"] for r in acc.pending}
        for hid, h in iter_records(history):
            oid = str(h.get("order_id") or "")
            if h.get("accounting_type") == "qisman" and not h.get("settled") \
                    and oid not in acc.accounted_ids and oid not in pending_ids:
                updates[f"accounting_history/{client}/{hid}/settled"] = ts
        received = money(max(0.0, acc.debt))
        if updates:
            await self.store.update("", updates)
        if received > 0:
            await self.store.push(f"transactions/clients/{client}", {
                "type": "Kirim", "amount": received, "timestamp": ts,
                "note": f"Barchasini hisob kitob qilish ({settled} ta buyurtma)",
            })
        new_debt = await self.recalc(client)
        return {"settled": settled, "received": received, "debt": new_debt}

    async def client_transactions(self, client: str) -> list[dict]:
        raw = await self.store.get(f"transactions/clients/{client}") or {}
        rows = [dict(v, id=k) for k, v in iter_records(raw)]
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return rows

    # ---------- diller to'lov xabarnomalari ----------
    async def create_pending_payment(self, diller_tg_id: int, diller_name: str, client: str, amount) -> dict:
        amt = parse_number(amount)
        if amt is None or amt <= 0 or amt > MAX_PAYMENT:
            raise ServiceError("To'lov summasi musbat son bo'lishi kerak.")
        if not is_valid_key(client):
            raise ServiceError("Mijoz nomi aniqlanmadi. Admin bilan bog'laning.")
        pay_id = uuid.uuid4().hex[:8].upper()
        record = {"pay_id": pay_id, "diller_tg_id": int(diller_tg_id), "diller_name": clean_text(diller_name, 80),
                  "client_name": client, "amount": money(amt), "timestamp": now_str(), "status": "pending"}
        await self.store.set(f"pending_payments/{pay_id}", record)
        return record

    async def pending_payments(self) -> list[dict]:
        raw = await self.store.get("pending_payments") or {}
        rows = [dict(v, pay_id=v.get("pay_id") or k) for k, v in iter_records(raw) if v.get("status") == "pending"]
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return rows

    async def resolve_payment(self, actor_id, pay_id: str, approve: bool) -> tuple[dict, float | None]:
        pay = await self.store.get(f"pending_payments/{pay_id}")
        if not isinstance(pay, dict):
            raise NotFound("To'lov topilmadi.")
        target = "confirmed" if approve else "rejected"

        def tx(cur):
            if cur != "pending":
                raise Conflict(f"Bu to'lov allaqachon ko'rib chiqilgan ({cur}).")
            return target

        await run_tx(self.store, f"pending_payments/{pay_id}/status", tx)
        await self.store.update(f"pending_payments/{pay_id}", {"resolved_by": str(actor_id), "resolved_at": now_str()})
        new_debt = None
        if approve:
            new_debt = await self.partial_payment(
                actor_id, pay["client_name"], pay["amount"],
                note=f"Diller to'lov bildirdi: {pay.get('diller_name', '')} (ID: {pay_id})",
            )
        return pay, new_debt

    # ---------- haydovchilar ----------
    async def driver_balances(self) -> list[dict]:
        raw = await self.store.get("driver_balances") or {}
        names = list(await self.catalog.drivers())
        for k in raw if isinstance(raw, dict) else {}:
            if k not in names:
                names.append(k)
        return [{"driver": n, "balance": money((raw or {}).get(n, 0) if isinstance(raw, dict) else 0)}
                for n in names]

    async def driver_balance(self, driver: str) -> float:
        if not is_valid_key(driver):
            raise ServiceError("Haydovchi nomi noto'g'ri.")
        return money(await self.store.get(f"driver_balances/{driver}") or 0)

    async def adjust_driver(self, actor_id, driver: str, delta: float, kind: str, note: str) -> float:
        if not is_valid_key(driver):
            raise ServiceError("Haydovchi nomi noto'g'ri.")
        delta = money(delta)
        new = await self.store.transaction(f"driver_balances/{driver}", lambda cur: money(money(cur or 0) + delta))
        await self.store.push(f"transactions/drivers/{driver}", {
            "type": kind, "amount": abs(delta), "timestamp": now_str(), "note": clean_text(note, 200),
            "by": str(actor_id),
        })
        return money(new)

    async def driver_payment(self, actor_id, driver: str, amount, direction: str) -> float:
        amt = parse_number(amount)
        if amt is None or amt <= 0 or amt > MAX_PAYMENT:
            raise ServiceError("Summa musbat son bo'lishi kerak.")
        if direction == "give":
            return await self.adjust_driver(actor_id, driver, -amt, "Chiqim", "Pul berildi")
        if direction == "receive":
            return await self.adjust_driver(actor_id, driver, amt, "Kirim", "Pul qaytardi / Haqqi yozildi")
        raise ServiceError("Noma'lum amal.")

    async def driver_history(self, driver: str) -> list[dict]:
        raw = await self.store.get(f"transactions/drivers/{driver}") or {}
        rows = [dict(v, id=k) for k, v in iter_records(raw)]
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return rows



__all__ = ["FinanceService", "compute_account", "order_net", "order_gross", "order_amount", "order_client"]
