"""Ombor (mebellar) bilan ishlash. Qoldiq o'zgarishlari tranzaksiya orqali — poyga holatisiz."""
from __future__ import annotations

from ..store import Store
from ..utils import clean_text, iter_records, money, now_str, parse_number, product_key, to_int
from .errors import NotFound, ServiceError

MAX_QTY = 100_000


def _valid_image(url: str) -> str:
    url = clean_text(url, 500)
    if url and not url.startswith("https://"):
        raise ServiceError("Rasm manzili https:// bilan boshlanishi kerak.")
    return url


class InventoryService:
    def __init__(self, store: Store):
        self.store = store

    async def all(self) -> dict[str, dict]:
        return {k: v for k, v in iter_records(await self.store.get("mebellar") or {})}

    async def get(self, product_id: str) -> dict | None:
        p = await self.store.get(f"mebellar/{product_key(product_id)}")
        return p if isinstance(p, dict) else None

    @staticmethod
    def unit_price(product: dict | None) -> float:
        return money(product.get("narxi")) if product else 0.0

    async def upsert(self, actor_id, *, name: str, model: str = "", price=None,
                     quantity=None, image: str = "") -> dict:
        name = clean_text(name, 60)
        pid = product_key(name)
        if not pid or not pid.replace("_", "").isalnum():
            raise ServiceError("Mebel nomi faqat harf, raqam, bo'sh joy va '-' dan iborat bo'lsin.")
        existing = await self.get(pid) or {}
        record = {
            "id": pid,
            "nomi": name,
            "modeli": clean_text(model, 60) or existing.get("modeli", ""),
            "rasm": _valid_image(image) if image else existing.get("rasm", ""),
        }
        if price is not None and str(price).strip() != "":
            p = parse_number(price)
            if p is None or p < 0 or p > 1_000_000:
                raise ServiceError("Narx noto'g'ri.")
            record["narxi"] = money(p)
        elif "narxi" in existing:
            record["narxi"] = existing["narxi"]
        if quantity is not None and str(quantity).strip() != "":
            q = to_int(quantity, -1)
            if q < 0 or q > MAX_QTY:
                raise ServiceError("Soni 0 dan katta yoki teng butun son bo'lsin.")
            record["soni"] = q
        else:
            record["soni"] = to_int(existing.get("soni"), 0)
        await self.store.update(f"mebellar/{pid}", record)
        await self._log(actor_id, pid, "upsert", record["soni"] - to_int(existing.get("soni"), 0), record["soni"])
        return record

    async def set_quantity(self, actor_id, product_id: str, qty: int) -> int:
        pid = product_key(product_id)
        if not await self.get(pid):
            raise NotFound("Mebel topilmadi.")
        if not isinstance(qty, int) or qty < 0 or qty > MAX_QTY:
            raise ServiceError("Soni 0 dan katta yoki teng butun son bo'lsin.")
        old = {}

        def tx(cur):
            old["v"] = to_int(cur, 0)
            return qty

        await self.store.transaction(f"mebellar/{pid}/soni", tx)
        await self._log(actor_id, pid, "set", qty - old.get("v", 0), qty)
        return qty

    async def set_price(self, actor_id, product_id: str, price) -> float:
        pid = product_key(product_id)
        if not await self.get(pid):
            raise NotFound("Mebel topilmadi.")
        p = parse_number(price)
        if p is None or p < 0 or p > 1_000_000:
            raise ServiceError("Narx noto'g'ri.")
        await self.store.update(f"mebellar/{pid}", {"narxi": money(p)})
        await self.store.push("audit_log", {"action": "set_price", "product_id": pid, "price": money(p),
                                            "by": str(actor_id), "at": now_str()})
        return money(p)

    async def delete(self, actor_id, product_id: str) -> None:
        pid = product_key(product_id)
        if not await self.get(pid):
            raise NotFound("Mebel topilmadi.")
        await self.store.delete(f"mebellar/{pid}")
        await self.store.push("audit_log", {"action": "delete_product", "product_id": pid,
                                            "by": str(actor_id), "at": now_str()})

    async def reserve(self, product_id: str, amount: int) -> int:
        """Ombordan mavjud miqdor qadar ayiradi. Haqiqatda ayirilgan sonni qaytaradi."""
        pid = product_key(product_id)
        if amount <= 0 or not await self.get(pid):
            return 0
        taken = {"n": 0}

        def tx(cur):
            have = max(0, to_int(cur, 0))
            taken["n"] = min(have, amount)
            return have - taken["n"]

        await self.store.transaction(f"mebellar/{pid}/soni", tx)
        return taken["n"]

    async def release(self, product_id: str, qty: int) -> None:
        pid = product_key(product_id)
        if qty <= 0 or not await self.get(pid):
            return
        # Eski buyurtmalar qoldiqni manfiyga tushirgan bo'lishi mumkin — shuning uchun clamp qilinmaydi.
        await self.store.transaction(f"mebellar/{pid}/soni", lambda cur: to_int(cur, 0) + qty)

    async def _log(self, actor_id, pid: str, action: str, delta: int, result: int) -> None:
        await self.store.push("stock_log", {"product_id": pid, "action": action, "delta": delta,
                                            "result": result, "by": str(actor_id), "at": now_str()})
