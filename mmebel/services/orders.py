"""Buyurtmalar: yaratish, o'zgartirish, bekor qilish, status va yetkazib berish.

Status o'zgarishlari tranzaksiya orqali — bir buyurtmani ikki kishi bir vaqtda
"yetkazildi" yoki "bekor qilindi" qila olmaydi.
"""
from __future__ import annotations

import uuid

from ..constants import (
    ACTIVE_STATUSES,
    ALLOWED_TRANSITIONS,
    SELF_PICKUP_DRIVER,
    ST_CANCELLED,
    ST_DELIVERED,
    ST_PICKED_UP,
    ST_PREPARING,
    ST_READY,
)
from ..store import Store
from ..utils import (
    clean_text,
    is_valid_key,
    iter_records,
    money,
    month_key,
    normalize_due_date,
    now_str,
    parse_date,
    parse_number,
    product_key,
)
from .errors import Conflict, NotFound, ServiceError, run_tx
from .finance import order_amount, order_client, order_gross, order_net

MAX_AMOUNT = 10_000


class OrderService:
    def __init__(self, store: Store, inventory, finance):
        self.store = store
        self.inventory = inventory
        self.finance = finance

    # ---------- o'qish ----------
    async def all(self) -> dict[str, dict]:
        return {k: v for k, v in iter_records(await self.store.get("orders") or {})}

    async def get(self, order_id: str) -> dict:
        if not order_id or not is_valid_key(order_id):
            raise NotFound("Buyurtma topilmadi.")
        o = await self.store.get(f"orders/{order_id}")
        if not isinstance(o, dict):
            raise NotFound("Buyurtma topilmadi.")
        return o

    async def find(self, raw_id: str) -> tuple[str, dict]:
        """ID ni katta-kichik harfga qaramay topadi."""
        raw = clean_text(raw_id, 64)
        if "(" in raw and raw.endswith(")"):
            raw = raw.rsplit("(", 1)[1][:-1].strip()
        for candidate in (raw, raw.upper()):
            if is_valid_key(candidate):
                o = await self.store.get(f"orders/{candidate}")
                if isinstance(o, dict):
                    return candidate, o
        for k, v in (await self.all()).items():
            if k.lower() == raw.lower():
                return k, v
        raise NotFound("Bunday ID li buyurtma topilmadi.")

    async def active(self) -> list[tuple[str, dict]]:
        rows = [(k, v) for k, v in (await self.all()).items() if v.get("status") in ACTIVE_STATUSES]
        rows.sort(key=lambda kv: (parse_date(kv[1].get("due_date")) or parse_date("01.01.2100"),
                                  kv[1].get("created_at", "")))
        return rows

    async def for_diller(self, tg_id: int, client_name: str | None) -> list[tuple[str, dict]]:
        target = (client_name or "").strip().lower()
        out = []
        for k, v in (await self.all()).items():
            own = str(v.get("client_tg_id", "")) == str(tg_id)
            by_name = bool(target) and order_client(v).lower() == target
            if own or by_name:
                out.append((k, dict(v, _own=own)))
        out.sort(key=lambda kv: kv[1].get("created_at", ""), reverse=True)
        return out

    # ---------- yaratish ----------
    async def _new_id(self, pid: str) -> str:
        for _ in range(5):
            oid = f"{pid}-{uuid.uuid4().hex[:5].upper()}"
            if not await self.store.get(f"orders/{oid}/status"):
                return oid
        raise ServiceError("ID yaratib bo'lmadi, qayta urinib ko'ring.")

    async def create(self, actor_id, *, client_name: str, product: str, amount, due_date: str,
                     comment: str = "", source: str = "admin", client_tg_id=None,
                     custom_price=None, allow_past: bool = False) -> dict:
        client_name = clean_text(client_name, 80)
        if not client_name or not is_valid_key(client_name):
            raise ServiceError("Mijoz nomi bo'sh yoki unda . $ # [ ] / belgilari bor.")
        pid = product_key(product)
        if not pid or not pid.replace("_", "").isalnum() or len(pid) > 40:
            raise ServiceError("Mebel nomi noto'g'ri.")
        qty = parse_number(amount)
        if qty is None or qty != int(qty) or not (0 < qty <= MAX_AMOUNT):
            raise ServiceError(f"Soni 1 dan {MAX_AMOUNT} gacha butun son bo'lishi kerak.")
        qty = int(qty)
        due = normalize_due_date(due_date, allow_past=allow_past)
        if not due:
            raise ServiceError("Sana noto'g'ri. Format: KK.OO.YYYY (bugundan oldin bo'lmasin).")

        product_rec = await self.inventory.get(pid)
        if custom_price not in (None, ""):
            unit = parse_number(custom_price)
            if unit is None or unit < 0 or unit > 1_000_000:
                raise ServiceError("Narx noto'g'ri.")
            unit = money(unit)
        else:
            unit = self.inventory.unit_price(product_rec)

        oid = await self._new_id(pid)
        deducted = await self.inventory.reserve(pid, qty)
        ts = now_str()
        record = {
            "order_id": oid,
            "client_name": client_name,
            "product_id": pid,
            "amount": qty,
            "due_date": due,
            "comment": clean_text(comment, 500),
            "status": ST_PREPARING,
            "source": source,
            "created_at": ts,
            "created_by": str(actor_id),
            "month": month_key(),
            "price": unit,
            "total_price": money(unit * qty),
            "deducted_qty": deducted,
        }
        if client_tg_id is not None:
            record["client_tg_id"] = str(client_tg_id)
        try:
            await self.store.set(f"orders/{oid}", record)
        except Exception:
            await self.inventory.release(pid, deducted)  # omborni qaytarib qo'yamiz
            raise
        await self._audit(actor_id, oid, "create", {"amount": qty, "client": client_name})
        return dict(record, product_name=(product_rec or {}).get("nomi", pid),
                    product_model=(product_rec or {}).get("modeli", ""))

    # ---------- status ----------
    async def _transition(self, order_id: str, allowed_from: set[str] | frozenset, to: str) -> str:
        prev = {}

        def tx(cur):
            if cur not in allowed_from or to not in ALLOWED_TRANSITIONS.get(cur, ()):
                raise Conflict(f"Buyurtma holati '{cur or '—'}' — bu amalni bajarib bo'lmaydi.")
            prev["status"] = cur
            return to

        await run_tx(self.store, f"orders/{order_id}/status", tx)
        return prev["status"]

    async def cancel(self, actor_id, order_id: str, *, only_preparing: bool = False,
                     owner_tg_id: int | None = None) -> dict:
        order = await self.get(order_id)
        if owner_tg_id is not None:
            if str(order.get("client_tg_id", "")) != str(owner_tg_id) or order.get("source", "diller") != "diller":
                raise ServiceError("Faqat o'zingiz bergan zakazni bekor qila olasiz.")
        allowed = {ST_PREPARING} if only_preparing else set(ACTIVE_STATUSES)
        await self._transition(order_id, allowed, ST_CANCELLED)
        deducted = parse_number(order.get("deducted_qty"))
        qty = int(deducted) if deducted is not None and deducted >= 0 else order_amount(order)
        await self.inventory.release(order.get("product_id", ""), qty)
        await self.store.update(f"orders/{order_id}", {"cancelled_at": now_str(), "cancelled_by": str(actor_id),
                                                        "deducted_qty": 0})
        await self._audit(actor_id, order_id, "cancel", {"returned": qty})
        return dict(order, status=ST_CANCELLED, returned_qty=qty)

    async def set_ready(self, actor_id, order_id: str) -> dict:
        order = await self.get(order_id)
        await self._transition(order_id, set(ACTIVE_STATUSES), ST_READY)
        await self.store.update(f"orders/{order_id}", {"ready_at": now_str(), "ready_by": str(actor_id)})
        await self._audit(actor_id, order_id, "ready", {})
        return dict(order, status=ST_READY)

    async def set_preparing(self, actor_id, order_id: str) -> dict:
        order = await self.get(order_id)
        await self._transition(order_id, {ST_READY}, ST_PREPARING)
        await self._audit(actor_id, order_id, "unready", {})
        return dict(order, status=ST_PREPARING)

    async def deliver(self, actor_id, order_id: str, *, driver: str, price) -> dict:
        """Haydovchi yetkazib berdi yoki diller o'zi olib ketdi (driver == SELF_PICKUP_DRIVER)."""
        driver = clean_text(driver, 60)
        if not driver or not is_valid_key(driver):
            raise ServiceError("Haydovchi nomi noto'g'ri.")
        fee = parse_number(price, 0.0)
        if fee is None or fee < 0 or fee > 100_000:
            raise ServiceError("Narx noto'g'ri.")
        fee = money(fee)
        pickup = driver == SELF_PICKUP_DRIVER
        to = ST_PICKED_UP if pickup else ST_DELIVERED

        order = await self.get(order_id)
        await self._transition(order_id, set(ACTIVE_STATUSES), to)
        ts = now_str()
        price_label = f"{fee:g}$"
        await self.store.update(f"orders/{order_id}", {
            "driver": driver,
            "delivery_price": price_label,
            "pickup_discount": fee if pickup else 0,
            "month": month_key(),
            "delivered_at": ts,
            "delivered_by": str(actor_id),
        })
        client = order_client(order)
        await self.store.push(f"deliveries/{month_key()}", {
            "order_id": order_id, "client": client, "driver": driver, "price": price_label,
            "product_id": order.get("product_id", ""), "amount": order.get("amount", 1),
            "timestamp": ts, "comment": order.get("comment", ""),
        })
        updated = dict(order, status=to, driver=driver, delivery_price=price_label,
                       pickup_discount=fee if pickup else 0, delivered_at=ts)
        net = order_net(updated)
        if net > 0 and client and is_valid_key(client):
            note = (f"Olib ketdi (chegirma: {fee:g}$): " if pickup and fee else "Yetkazildi: ") + \
                   f"{order.get('product_id', '')} ({order_amount(order)} ta) (Buyurtma: {order_id})"
            await self.store.push(f"transactions/clients/{client}", {
                "type": "Chiqim", "amount": net, "timestamp": ts, "note": note,
            })
        if not pickup and fee > 0:
            await self.finance.adjust_driver(actor_id, driver, fee, "Kirim",
                                             f"Yetkazib berish haqi (Buyurtma: {order_id})")
        debt = await self.finance.recalc(client) if client else 0.0
        await self._audit(actor_id, order_id, "deliver", {"driver": driver, "price": fee})
        return dict(updated, net=net, gross=order_gross(updated), debt=debt)

    # ---------- tahrirlash ----------
    async def edit(self, actor_id, order_id: str, *, amount=None, due_date=None, comment=None) -> dict:
        order = await self.get(order_id)
        if order.get("status") not in ACTIVE_STATUSES:
            raise Conflict("Faqat faol buyurtmani o'zgartirish mumkin.")
        updates: dict = {}
        changes: dict = {}
        if amount is not None:
            qty = parse_number(amount)
            if qty is None or qty != int(qty) or not (0 < qty <= MAX_AMOUNT):
                raise ServiceError(f"Soni 1 dan {MAX_AMOUNT} gacha butun son bo'lishi kerak.")
            qty = int(qty)
            old_qty = order_amount(order)
            if qty != old_qty:
                pid = order.get("product_id", "")
                old_ded = parse_number(order.get("deducted_qty"))
                old_ded = int(old_ded) if old_ded is not None and old_ded >= 0 else old_qty
                # Avval eski ayirilganini qaytaramiz, keyin yangisini band qilamiz
                await self.inventory.release(pid, old_ded)
                new_ded = await self.inventory.reserve(pid, qty)
                unit = money(order.get("price") or 0)
                updates.update({"amount": qty, "deducted_qty": new_ded, "total_price": money(unit * qty)})
                changes["amount"] = qty
        if due_date is not None:
            due = normalize_due_date(due_date)
            if not due:
                raise ServiceError("Sana noto'g'ri. Format: KK.OO.YYYY (bugundan oldin bo'lmasin).")
            if due != order.get("due_date"):
                updates["due_date"] = due
                changes["due_date"] = due
        if comment is not None:
            c = clean_text(comment, 500)
            if c != order.get("comment", ""):
                updates["comment"] = c
                changes["comment"] = c
        if not updates:
            return dict(order, _changes={})
        updates["updated_at"] = now_str()
        await self.store.update(f"orders/{order_id}", updates)
        await self._audit(actor_id, order_id, "edit", changes)
        return dict(order, **updates, _changes=changes)

    async def _audit(self, actor_id, order_id: str, action: str, details: dict) -> None:
        await self.store.push("audit_log", {"action": f"order_{action}", "order_id": order_id,
                                            "details": details, "by": str(actor_id), "at": now_str()})


__all__ = ["OrderService"]
