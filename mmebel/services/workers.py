"""Mebel yig'uvchilar (haydovchilar): profil, buyurtmaga tayinlash, mijozga topshirish, ostatka va kassa.

Pul oqimi:
  * yig'uvchi mijozdan NAQD olgan ostatka — uning kassasiga (sexga topshirishi kerak bo'lgan qarz);
  * KARTA orqali kelgani zavod hisobiga tushgan — yig'uvchi kassasiga qo'shilmaydi;
  * har ikkalasi ham diller (masalan, Comfort) qarzidan avtomatik ayriladi (buyurtmaga bog'langan to'lov).
  * yig'uvchi kassani admin yoki omborchiga topshiradi -> qabul qiluvchi tasdiqlaydi;
    omborchiga topshirilgan pul omborchi kassasiga o'tadi, u ham adminga topshiradi.

Bazada:
  workers/{wid}            {name, phone, uid, active, created_at, created_by}
  worker_phones/{digits}   wid   (bot orqali raqam ulashilganda profilga bog'lash uchun)
  wpay/{pid}               mijozdan olingan to'lov yozuvi (naqd/karta, rasmlar, izoh)
  cash/{holder}            kassa qoldig'i ($), holder = w_{wid} | u_{uid}
  cash_log/{holder}/{k}    kassa tarixi
  cash_transfers/{tid}     topshirish so'rovi (pending -> approved/rejected)
  uploads/{uid}/{key}      yuklangan rasm (Telegram file_id) — faqat o'z rasmini biriktira oladi
"""
from __future__ import annotations

import time

from ..constants import (
    ACTIVE_STATUSES,
    DELIVERED_STATUSES,
    ROLE_ADMIN,
    ROLE_MIJOZ,
    ROLE_OMBORCHI,
    ROLE_YIGUVCHI,
)
from ..store import Store
from ..utils import (
    clean_text,
    is_valid_key,
    iter_records,
    money,
    month_key,
    now_str,
    parse_number,
)
from .errors import Conflict, NotFound, ServiceError, run_tx
from .finance import order_client

MAX_PHOTOS = 5
MAX_CASH = 10_000_000
METHODS = {"naqd": "Naqd", "karta": "Karta"}
TO_ROLES = {ROLE_ADMIN: "adminga", ROLE_OMBORCHI: "omborchiga"}
UPLOAD_TTL = 24 * 3600

UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentyabr", "oktyabr",
             "noyabr", "dekabr"]


def human_date(ts: str) -> str:
    """'2026-11-11 14:03:00' -> '11-noyabr 2026'."""
    try:
        y, m, d = str(ts)[:10].split("-")
        return f"{int(d)}-{UZ_MONTHS[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return str(ts)[:10]


def fmt_usd(v) -> str:
    v = money(v)
    s = f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{s}$"


def worker_holder(wid: str) -> str:
    return f"w_{wid}"


def staff_holder(uid) -> str:
    return f"u_{uid}"


class WorkerService:
    def __init__(self, store: Store, users, orders, finance):
        self.store = store
        self.users = users
        self.orders = orders
        self.finance = finance

    # ---------- profil ----------
    async def all(self) -> dict[str, dict]:
        return {k: v for k, v in iter_records(await self.store.get("workers") or {})}

    async def get(self, wid: str) -> dict:
        if not wid or not is_valid_key(wid):
            raise NotFound("Yig'uvchi topilmadi.")
        w = await self.store.get(f"workers/{wid}")
        if not isinstance(w, dict):
            raise NotFound("Yig'uvchi topilmadi.")
        return w

    async def by_uid(self, uid) -> tuple[str, dict] | None:
        for wid, w in (await self.all()).items():
            if str(w.get("uid") or "") == str(uid):
                return wid, w
        return None

    async def require_self(self, uid) -> tuple[str, dict]:
        found = await self.by_uid(uid)
        if not found:
            raise ServiceError("Sizga yig'uvchi profili biriktirilmagan. Admin yoki omborchiga murojaat qiling.")
        if found[1].get("active") is False:
            raise ServiceError("Profilingiz o'chirilgan. Admin bilan bog'laning.")
        return found

    async def create(self, actor_id, name: str, phone: str) -> tuple[str, dict]:
        from .sessions import normalize_phone
        name = clean_text(name, 60)
        if not name or not is_valid_key(name):
            raise ServiceError("Ismni kiriting (. $ # [ ] / belgilarisiz).")
        digits = normalize_phone(phone)
        if not digits:
            raise ServiceError("Telefon raqamini to'liq kiriting, masalan: +998 90 123 45 67")
        existing = await self.all()
        for wid, w in existing.items():
            if w.get("phone") == digits:
                raise Conflict(f"Bu raqam bilan yig'uvchi bor: {w.get('name')}.")
            if str(w.get("name", "")).strip().lower() == name.lower():
                raise Conflict("Bu ismli yig'uvchi bor. Familiyasini ham qo'shing.")
        wid = self.store.new_key("workers")
        rec = {"name": name, "phone": digits, "uid": "", "active": True, "created_at": now_str(),
               "created_by": str(actor_id)}
        await self.store.update("", {f"workers/{wid}": rec, f"worker_phones/{digits}": wid})
        uid = await self.store.get(f"phones/{digits}")  # odam botga raqamini allaqachon ulashgan bo'lsa
        if uid:
            await self.link(wid, str(uid))
            rec["uid"] = str(uid)
        await self._audit(actor_id, "worker_create", {"worker": name, "phone": digits})
        return wid, rec

    async def update(self, actor_id, wid: str, *, name=None, phone=None, active=None) -> dict:
        from .sessions import normalize_phone
        w = await self.get(wid)
        updates: dict = {}
        if name is not None:
            n = clean_text(name, 60)
            if not n or not is_valid_key(n):
                raise ServiceError("Ism noto'g'ri.")
            updates[f"workers/{wid}/name"] = n
        if phone is not None:
            digits = normalize_phone(phone)
            if not digits:
                raise ServiceError("Telefon raqami noto'g'ri.")
            if digits != w.get("phone"):
                other = await self.store.get(f"worker_phones/{digits}")
                if other and other != wid:
                    raise Conflict("Bu raqam boshqa yig'uvchiga biriktirilgan.")
                if w.get("phone"):
                    updates[f"worker_phones/{w['phone']}"] = None
                updates[f"worker_phones/{digits}"] = wid
                updates[f"workers/{wid}/phone"] = digits
        if isinstance(active, bool):
            updates[f"workers/{wid}/active"] = active
        if updates:
            await self.store.update("", updates)
            await self._audit(actor_id, "worker_update", {"worker_id": wid})
        return await self.get(wid)

    async def link(self, wid: str, uid: str) -> None:
        """Profilni Telegram foydalanuvchiga bog'laydi; rol berilmagan bo'lsa — «Yig'uvchi» bo'ladi."""
        await self.store.set(f"workers/{wid}/uid", str(uid))
        if await self.users.role(uid) == ROLE_MIJOZ:
            await self.store.update(f"users/{uid}", {"role": ROLE_YIGUVCHI, "role_updated_at": now_str(),
                                                    "role_updated_by": "worker_profile"})
            self.users.invalidate()

    async def link_by_phone(self, uid, digits: str) -> bool:
        wid = await self.store.get(f"worker_phones/{digits}")
        if not wid:
            return False
        w = await self.store.get(f"workers/{wid}")
        if not isinstance(w, dict) or (w.get("uid") and str(w["uid"]) != str(uid)):
            return False
        await self.link(str(wid), str(uid))
        return True

    async def ensure_for_user(self, actor_id, uid) -> str:
        """Admin foydalanuvchiga «Yig'uvchi» rolini bersa — profil avtomatik ochiladi."""
        found = await self.by_uid(uid)
        if found:
            return found[0]
        u = await self.users.get(str(uid)) or {}
        base = clean_text(u.get("name") or f"Yig'uvchi {uid}", 50)
        base = "".join(c for c in base if c not in ".$#[]/") or f"Yig'uvchi {uid}"
        names = {str(w.get("name", "")).lower() for w in (await self.all()).values()}
        name = base if base.lower() not in names else f"{base} {str(uid)[-4:]}"
        wid = self.store.new_key("workers")
        rec = {"name": name, "phone": u.get("phone", ""), "uid": str(uid), "active": True,
               "created_at": now_str(), "created_by": str(actor_id)}
        updates = {f"workers/{wid}": rec}
        if u.get("phone") and not await self.store.get(f"worker_phones/{u['phone']}"):
            updates[f"worker_phones/{u['phone']}"] = wid
        await self.store.update("", updates)
        return wid

    # ---------- tayinlash ----------
    async def assign(self, actor_id, order_id: str, wid: str, fee=None) -> dict:
        w = await self.get(wid)
        if w.get("active") is False:
            raise ServiceError("Bu yig'uvchi profili o'chirilgan.")
        fee_v = parse_number(fee, 0.0) if fee not in (None, "") else 0.0
        if fee_v is None or fee_v < 0 or fee_v > 100_000:
            raise ServiceError("Yetkazish haqi noto'g'ri.")
        order = await self.orders.get(order_id)
        prev = {}

        def tx(cur):
            if not isinstance(cur, dict) or cur.get("status") not in ACTIVE_STATUSES:
                raise Conflict("Faqat faol (yetkazilmagan) buyurtmani yig'uvchiga yuborish mumkin.")
            prev["wid"] = cur.get("worker_id", "")
            ts = now_str()
            return dict(cur, worker_id=wid, worker_name=w["name"], assigned_at=ts, assigned_by=str(actor_id),
                        delivery_fee=money(fee_v))

        await run_tx(self.store, f"orders/{order_id}", tx)
        await self._audit(actor_id, "order_assign", {"order_id": order_id, "worker": w["name"],
                                                     "prev": prev.get("wid", "")})
        return dict(order, worker_id=wid, worker_name=w["name"], delivery_fee=money(fee_v), _worker=w,
                    _prev_worker=prev.get("wid", ""))

    async def unassign(self, actor_id, order_id: str) -> dict:
        def tx(cur):
            if not isinstance(cur, dict) or cur.get("status") not in ACTIVE_STATUSES:
                raise Conflict("Buyurtma yetkazilgan yoki bekor qilingan.")
            out = dict(cur)
            for k in ("worker_id", "worker_name", "assigned_at", "assigned_by", "delivery_fee"):
                out.pop(k, None)
            return out

        res = await run_tx(self.store, f"orders/{order_id}", tx)
        await self._audit(actor_id, "order_unassign", {"order_id": order_id})
        return res

    async def orders_for(self, wid: str, days: int = 45) -> tuple[list, list]:
        """(faol — yetkazilishi kerak, oxirgi yetkazilganlar)."""
        from datetime import timedelta

        from ..utils import now, parse_datetime
        cutoff = (now() - timedelta(days=days)).replace(tzinfo=None)
        active, done = [], []
        for oid, o in (await self.orders.all()).items():
            if str(o.get("worker_id", "")) != wid:
                continue
            st = o.get("status", "")
            if st in ACTIVE_STATUSES:
                active.append((oid, o))
            elif st in DELIVERED_STATUSES or o.get("handover"):
                ref = parse_datetime(o.get("delivered_at"))
                if not ref or ref >= cutoff:
                    done.append((oid, o))
        active.sort(key=lambda kv: (kv[1].get("assigned_at", ""), kv[0]))
        done.sort(key=lambda kv: kv[1].get("delivered_at", ""), reverse=True)
        return active, done

    # ---------- rasmlar ----------
    async def save_upload(self, uid, file_id: str) -> str:
        key = self.store.new_key(f"uploads/{uid}")
        await self.store.set(f"uploads/{uid}/{key}", {"file_id": file_id, "at": int(time.time())})
        return key

    async def _resolve_uploads(self, uid, keys) -> list[str]:
        if keys in (None, ""):
            return []
        if not isinstance(keys, list) or len(keys) > MAX_PHOTOS:
            raise ServiceError(f"Ko'pi bilan {MAX_PHOTOS} ta rasm.")
        out = []
        for k in keys:
            k = str(k)
            rec = await self.store.get(f"uploads/{uid}/{k}") if is_valid_key(k) else None
            if not isinstance(rec, dict) or time.time() - (rec.get("at") or 0) > UPLOAD_TTL:
                raise ServiceError("Rasm topilmadi yoki eskirgan. Qayta yuklang.")
            out.append(rec["file_id"])
        return out

    async def cleanup_uploads(self) -> int:
        """Biriktirilmay qolgan eski yuklamalar (kalitlar) — Telegram'dagi rasm o'zi qoladi."""
        raw = await self.store.get("uploads") or {}
        cutoff = time.time() - UPLOAD_TTL
        old = {f"uploads/{uid}/{k}": None for uid, recs in (raw.items() if isinstance(raw, dict) else [])
               if isinstance(recs, dict) for k, v in recs.items()
               if not isinstance(v, dict) or (v.get("at") or 0) < cutoff}
        if old:
            await self.store.update("", old)
        return len(old)

    # ---------- topshirish va to'lov ----------
    async def handover(self, uid, order_id: str, *, correct: bool, amount, method: str, note: str = "",
                       photos=None) -> dict:
        """Yig'uvchi: «Mebel mijozga topshirildi» + ostatka. Buyurtma «Biz yetkazib berdik» bo'ladi."""
        wid, w = await self.require_self(uid)
        order = await self.orders.get(order_id)
        if str(order.get("worker_id", "")) != wid:
            raise NotFound("Bu buyurtma sizga biriktirilmagan.")
        if order.get("status") not in ACTIVE_STATUSES:
            raise Conflict("Bu buyurtma allaqachon topshirilgan yoki bekor qilingan.")
        pay = await self._validate_payment(uid, order, correct=correct, amount=amount, method=method, note=note,
                                           photos=photos)
        delivered = await self.orders.deliver(uid, order_id, driver=w["name"], price=order.get("delivery_fee") or 0)
        rec = await self._record_payment(uid, wid, w, order_id, delivered, pay, kind="handover")
        await self.store.update(f"orders/{order_id}", {"handover": {
            "at": rec["ts"], "correct": pay["correct"], "pay_id": rec["pay_id"]}})
        debt = await self.finance.recalc(order_client(order)) if order_client(order) else 0.0
        return {**rec, "order": dict(delivered, debt=debt), "worker": w}

    async def extra_payment(self, uid, order_id: str, *, amount, method: str, note: str = "", photos=None) -> dict:
        """Mijoz qolgan pulni keyinroq bersa — o'sha buyurtmaga qo'shimcha to'lov."""
        wid, w = await self.require_self(uid)
        order = await self.orders.get(order_id)
        if str(order.get("worker_id", "")) != wid or not order.get("handover"):
            raise NotFound("Bu buyurtma sizga tegishli emas yoki hali topshirilmagan.")
        pay = await self._validate_payment(uid, order, correct=True, amount=amount, method=method, note=note,
                                           photos=photos, extra=True)
        rec = await self._record_payment(uid, wid, w, order_id, order, pay, kind="extra")
        return {**rec, "order": order, "worker": w}

    async def _validate_payment(self, uid, order: dict, *, correct, amount, method, note, photos,
                                extra: bool = False) -> dict:
        if not isinstance(correct, bool):
            raise ServiceError("Qoldiq summa to'g'ri olindimi — «Ha» yoki «Yo'q» ni tanlang.")
        if method not in METHODS:
            raise ServiceError("To'lov turi: naqd yoki karta.")
        amt = parse_number(amount)
        if amt is None or amt < 0 or amt > MAX_CASH:
            raise ServiceError("Olingan summani kiriting (0 yoki undan katta).")
        amt = money(amt)
        if extra and amt <= 0:
            raise ServiceError("Summa 0 dan katta bo'lishi kerak.")
        note = clean_text(note, 500)
        expected = money(order.get("collect") or 0)
        if not correct and not note:
            raise ServiceError("Nima uchun farq borligini izohga yozing.")
        if correct and expected and amt != expected and not note:
            raise ServiceError(f"Kutilgan qoldiq {fmt_usd(expected)}, siz {fmt_usd(amt)} kiritdingiz. "
                               "Summani tekshiring yoki «Yo'q» ni tanlab sababini yozing.")
        files = await self._resolve_uploads(uid, photos)
        if method == "karta" and amt > 0 and not files:
            raise ServiceError("Karta orqali to'lov uchun kamida 1 ta skrinshot yuklang.")
        return {"correct": correct, "amount": amt, "method": method, "note": note, "photos": files,
                "expected": expected}

    async def _record_payment(self, uid, wid: str, w: dict, order_id: str, order: dict, pay: dict, *,
                              kind: str) -> dict:
        ts = now_str()
        client = order_client(order)
        pid = self.store.new_key("wpay")
        rec = {"pay_id": pid, "order_id": order_id, "client": client, "serial": order.get("serial", ""),
               "product_id": order.get("product_id", ""), "variant": order.get("variant", ""),
               "worker_id": wid, "worker_name": w["name"], "kind": kind, "ts": ts, "by": str(uid),
               "month": month_key(), **pay}
        await self.store.set(f"wpay/{pid}", rec)
        amt = pay["amount"]
        if amt > 0 and client and is_valid_key(client):
            label = "naqd" if pay["method"] == "naqd" else "karta"
            await self.finance.partial_payment(uid, client, amt, order_id=order_id,
                                               note=f"Mijozdan ostatka ({label}) — {w['name']}"
                                                    + (f". {pay['note']}" if pay["note"] else ""))
        if amt > 0 and pay["method"] == "naqd":
            await self._cash_add(worker_holder(wid), amt, {
                "kind": "collect", "order_id": order_id, "pay_id": pid, "serial": order.get("serial", ""),
                "text": f"{human_date(ts)}: mijozdan {fmt_usd(amt)} naqd olindi ({order.get('product_id', '')}"
                        + (f", №{order['serial']}" if order.get("serial") else "") + ")"})
        return rec

    async def payments(self, *, wid: str | None = None, order_id: str | None = None) -> list[dict]:
        rows = [dict(v, id=k) for k, v in iter_records(await self.store.get("wpay") or {})
                if (not wid or v.get("worker_id") == wid) and (not order_id or v.get("order_id") == order_id)]
        rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
        return rows

    async def payment(self, pid: str) -> dict:
        if not is_valid_key(pid):
            raise NotFound("To'lov topilmadi.")
        rec = await self.store.get(f"wpay/{pid}")
        if not isinstance(rec, dict):
            raise NotFound("To'lov topilmadi.")
        return rec

    # ---------- kassa ----------
    async def balance(self, holder: str) -> float:
        return money(await self.store.get(f"cash/{holder}") or 0)

    async def log(self, holder: str, limit: int = 200) -> list[dict]:
        rows = [dict(v, id=k) for k, v in iter_records(await self.store.get(f"cash_log/{holder}") or {})]
        rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
        return rows[:limit]

    async def _cash_add(self, holder: str, delta: float, entry: dict) -> float:
        new = await self.store.transaction(f"cash/{holder}", lambda cur: money(money(cur or 0) + money(delta)))
        await self.store.push(f"cash_log/{holder}", {**entry, "amount": money(delta), "ts": now_str(),
                                                     "balance": money(new)})
        return money(new)

    async def transfers(self, *, status: str | None = None) -> list[dict]:
        rows = [dict(v, id=k) for k, v in iter_records(await self.store.get("cash_transfers") or {})
                if not status or v.get("status") == status]
        rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
        return rows

    async def request_transfer(self, *, holder: str, from_name: str, from_kind: str, from_uid, to_role: str,
                               amount) -> dict:
        if to_role not in TO_ROLES or (from_kind == "omborchi" and to_role != ROLE_ADMIN):
            raise ServiceError("Kimga topshirishni tanlang.")
        bal = await self.balance(holder)
        amt = parse_number(amount) if amount not in (None, "") else bal
        if amt is None or amt <= 0:
            raise ServiceError("Topshiriladigan summa 0 dan katta bo'lishi kerak.")
        amt = money(amt)
        if amt > bal:
            raise ServiceError(f"Kassangizda {fmt_usd(bal)} bor — undan ko'p topshirib bo'lmaydi.")
        if any(t.get("from_holder") == holder for t in await self.transfers(status="pending")):
            raise Conflict("Oldingi topshirish hali tasdiqlanmagan. Tasdiqlanishini kuting.")
        tid = self.store.new_key("cash_transfers")
        rec = {"transfer_id": tid, "from_holder": holder, "from_name": from_name, "from_kind": from_kind,
               "from_uid": str(from_uid), "to_role": to_role, "amount": amt, "status": "pending", "ts": now_str()}
        await self.store.set(f"cash_transfers/{tid}", rec)
        return rec

    async def resolve_transfer(self, actor_id, actor_role: str, actor_name: str, tid: str, approve: bool) -> dict:
        if not is_valid_key(tid):
            raise NotFound("So'rov topilmadi.")
        cur = await self.store.get(f"cash_transfers/{tid}")
        if approve and isinstance(cur, dict) and cur.get("status") == "pending" \
                and await self.balance(cur.get("from_holder", "")) <= 0:
            raise Conflict("Topshiruvchining kassasida pul qolmagan — so'rovni rad eting.")
        snapshot = {}

        def tx(cur):
            if not isinstance(cur, dict):
                raise NotFound("So'rov topilmadi.")
            if cur.get("status") != "pending":
                raise Conflict("Bu so'rov allaqachon ko'rib chiqilgan.")
            if actor_role != ROLE_ADMIN and cur.get("to_role") != actor_role:
                raise ServiceError("Bu pul sizga topshirilmagan.")
            if str(cur.get("from_uid")) == str(actor_id):
                raise ServiceError("O'z topshirishingizni o'zingiz tasdiqlay olmaysiz.")
            snapshot.update(cur)
            return dict(cur, status="approved" if approve else "rejected", resolved_by=str(actor_id),
                        resolved_name=actor_name, resolved_role=actor_role, resolved_at=now_str())

        res = await run_tx(self.store, f"cash_transfers/{tid}", tx)
        if not approve:
            return res
        # Tasdiqlashgacha kassa o'zgargan bo'lishi mumkin — mavjudidan ko'p yechilmaydi
        amt = min(money(snapshot["amount"]), await self.balance(snapshot["from_holder"]))
        who = TO_ROLES.get(actor_role, "adminga")
        kind_label = "mebel yig'uvchi" if snapshot.get("from_kind") == "worker" else "omborchi"
        text = f"{human_date(res['resolved_at'])}, {kind_label} {snapshot['from_name']} {who} {fmt_usd(amt)} topshirdi"
        if actor_role == ROLE_OMBORCHI:
            text += f" ({actor_name})"
        await self._cash_add(snapshot["from_holder"], -amt, {"kind": "transfer_out", "transfer_id": tid, "text": text})
        if actor_role == ROLE_OMBORCHI:
            await self._cash_add(staff_holder(actor_id), amt, {
                "kind": "transfer_in", "transfer_id": tid,
                "text": f"{human_date(res['resolved_at'])}: {snapshot['from_name']} dan {fmt_usd(amt)} qabul qilindi"})
        await self.store.push("cash_journal", {"transfer_id": tid, "text": text, "amount": amt,
                                               "ts": res["resolved_at"]})
        return dict(res, amount=amt, text=text)

    async def summary(self) -> dict:
        """Admin/omborchi: barcha yig'uvchilar kassasi + shu oy statistikasi."""
        month = month_key()
        workers = await self.all()
        cash = await self.store.get("cash") or {}
        pays = [v for _, v in iter_records(await self.store.get("wpay") or {})]
        orders = await self.orders.all()
        rows = []
        for wid, w in workers.items():
            mine = [p for p in pays if p.get("worker_id") == wid and p.get("month") == month]
            active = sum(1 for o in orders.values()
                         if o.get("worker_id") == wid and o.get("status") in ACTIVE_STATUSES)
            rows.append({
                "id": wid, "name": w.get("name", ""), "phone": w.get("phone", ""), "linked": bool(w.get("uid")),
                "active": w.get("active", True) is not False,
                "cash": money((cash or {}).get(worker_holder(wid), 0) if isinstance(cash, dict) else 0),
                "assigned": active,
                "month_delivered": sum(1 for p in mine if p.get("kind") == "handover"),
                "month_cash": money(sum(p.get("amount", 0) for p in mine if p.get("method") == "naqd")),
                "month_card": money(sum(p.get("amount", 0) for p in mine if p.get("method") == "karta")),
            })
        rows.sort(key=lambda r: (not r["active"], -r["cash"], r["name"].lower()))
        staff = []
        if isinstance(cash, dict):
            for holder, bal in cash.items():
                if holder.startswith("u_") and money(bal):
                    u = await self.users.get(holder[2:]) or {}
                    staff.append({"holder": holder, "uid": holder[2:], "name": u.get("name") or holder[2:],
                                  "cash": money(bal)})
        return {"month": month, "workers": rows, "staff": staff,
                "total_cash": money(sum(r["cash"] for r in rows) + sum(s["cash"] for s in staff)),
                "month_cash": money(sum(r["month_cash"] for r in rows)),
                "month_card": money(sum(r["month_card"] for r in rows)),
                "month_delivered": sum(r["month_delivered"] for r in rows)}

    async def _audit(self, actor_id, action: str, details: dict) -> None:
        await self.store.push("audit_log", {"action": action, **details, "by": str(actor_id), "at": now_str()})


__all__ = ["MAX_PHOTOS", "METHODS", "WorkerService", "fmt_usd", "human_date", "staff_holder", "worker_holder"]
