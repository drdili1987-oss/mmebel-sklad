"""Sozlanadigan ro'yxatlar (mijozlar, haydovchilar, modellar) va bir martalik migratsiya."""
from __future__ import annotations

import logging
import time

from ..constants import (
    DEFAULT_CLIENTS,
    DEFAULT_DELIVERY_PRICES,
    DEFAULT_DRIVERS,
    DEFAULT_MODELS,
    DEFAULT_PICKUP_DISCOUNTS,
    DEFAULT_PRICE_CHANNEL,
    LEGACY_DILLERS,
    LEGACY_ROLE_IDS,
    ROLE_DILLER,
)
from ..store import Store
from ..utils import clean_text, is_valid_key, now_str
from .errors import ServiceError

log = logging.getLogger(__name__)

LIST_KEYS = ("clients", "drivers", "models")
_DEFAULTS = {
    "clients": DEFAULT_CLIENTS,
    "drivers": DEFAULT_DRIVERS,
    "models": DEFAULT_MODELS,
}
_TTL = 60.0


class CatalogService:
    def __init__(self, store: Store):
        self.store = store
        self._cache: dict | None = None
        self._at = 0.0

    async def settings(self, fresh: bool = False) -> dict:
        if fresh or self._cache is None or time.monotonic() - self._at > _TTL:
            raw = await self.store.get("settings") or {}
            data = {}
            for key in LIST_KEYS:
                val = raw.get(key)
                data[key] = [str(x) for x in val if x] if isinstance(val, list) else list(_DEFAULTS[key])
            data["delivery_prices"] = raw.get("delivery_prices") or list(DEFAULT_DELIVERY_PRICES)
            data["pickup_discounts"] = raw.get("pickup_discounts") or list(DEFAULT_PICKUP_DISCOUNTS)
            data["price_channel"] = raw.get("price_channel") or DEFAULT_PRICE_CHANNEL
            self._cache, self._at = data, time.monotonic()
        return self._cache

    async def clients(self) -> list[str]:
        return (await self.settings())["clients"]

    async def drivers(self) -> list[str]:
        return (await self.settings())["drivers"]

    async def models(self) -> list[str]:
        return (await self.settings())["models"]

    async def set_list(self, key: str, items: list[str], actor_id) -> list[str]:
        if key not in LIST_KEYS:
            raise ServiceError("Noma'lum ro'yxat.")
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in items or []:
            s = clean_text(item, 60)
            if not s:
                continue
            if key in ("clients", "drivers") and not is_valid_key(s):
                raise ServiceError(f"'{s}' nomida . $ # [ ] / belgilaridan foydalanib bo'lmaydi.")
            if s.lower() in seen:
                continue
            seen.add(s.lower())
            cleaned.append(s)
        if len(cleaned) > 300:
            raise ServiceError("Ro'yxat juda uzun (maksimum 300).")
        await self.store.set(f"settings/{key}", cleaned)
        await self.store.push("audit_log", {"action": f"settings_{key}", "count": len(cleaned),
                                            "by": str(actor_id), "at": now_str()})
        self._cache = None
        return cleaned

    async def add_client_if_missing(self, name: str) -> None:
        name = clean_text(name, 60)
        if not name:
            return
        clients = await self.clients()
        if name.lower() not in {c.lower() for c in clients}:
            await self.store.set("settings/clients", clients + [name])
            self._cache = None

    async def run_migrations(self) -> None:
        """Eski kodda qattiq yozilgan qiymatlarni bazaga bir marta ko'chiradi (idempotent)."""
        done = await self.store.get("meta/migrations") or {}
        if not done.get("v1_settings"):
            existing = await self.store.get("settings") or {}
            updates = {}
            for key in LIST_KEYS:
                if not isinstance(existing.get(key), list):
                    updates[key] = list(_DEFAULTS[key])
            if updates:
                await self.store.update("settings", updates)
            await self.store.set("meta/migrations/v1_settings", now_str())
            log.info("Migratsiya v1_settings bajarildi")
        if not done.get("v1_roles"):
            users = await self.store.get("users") or {}
            updates = {}
            # Eski kod bu ID'larni bazadan qat'i nazar majburan shu rolga qo'yardi — xatti-harakat saqlanadi.
            for uid, role in LEGACY_ROLE_IDS.items():
                updates[f"{uid}/role"] = role
            for client, ids in LEGACY_DILLERS.items():
                for tg in ids:
                    updates[f"{tg}/role"] = ROLE_DILLER
                    updates[f"{tg}/client_name"] = client
            # Eski "ishchi" rolini "xodim"ga normallashtirish
            for uid, u in users.items():
                if isinstance(u, dict) and u.get("role") == "ishchi" and f"{uid}/role" not in updates:
                    updates[f"{uid}/role"] = "xodim"
            await self.store.update("users", updates)
            await self.store.set("meta/migrations/v1_roles", now_str())
            log.info("Migratsiya v1_roles bajarildi: %d yozuv", len(updates))
        if not done.get("v2_prices"):
            # "350 so'm" kabi matnli narxlarni songa o'girish (valyuta — $)
            from ..utils import iter_records, money, parse_number
            products = await self.store.get("mebellar") or {}
            updates = {}
            for pid, p in iter_records(products):
                raw = p.get("narxi")
                if isinstance(raw, str):
                    n = parse_number(raw)
                    updates[f"{pid}/narxi"] = money(n) if n is not None else None
            if updates:
                await self.store.update("mebellar", updates)
            await self.store.set("meta/migrations/v2_prices", now_str())
            log.info("Migratsiya v2_prices bajarildi: %d ta narx", len(updates))
        self._cache = None
