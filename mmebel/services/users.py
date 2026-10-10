"""Foydalanuvchilar va rollar."""
from __future__ import annotations

import time

from ..constants import ALL_ROLES, ROLE_ADMIN, ROLE_ALIASES, ROLE_DILLER, ROLE_MIJOZ
from ..store import Store
from ..utils import clean_text, iter_records, now_str
from .errors import NotFound, ServiceError

_CACHE_TTL = 30.0


class UserService:
    def __init__(self, store: Store, owner_ids: list[int]):
        self.store = store
        self.owner_ids = {str(i) for i in owner_ids}
        self._cache: dict | None = None
        self._cache_at = 0.0

    # --- kesh ---
    async def all(self, fresh: bool = False) -> dict[str, dict]:
        if fresh or self._cache is None or time.monotonic() - self._cache_at > _CACHE_TTL:
            raw = await self.store.get("users") or {}
            self._cache = {k: v for k, v in iter_records(raw)}
            self._cache_at = time.monotonic()
        return self._cache

    def invalidate(self) -> None:
        self._cache = None

    # --- o'qish ---
    @staticmethod
    def normalize_role(role: str | None) -> str:
        role = ROLE_ALIASES.get(str(role or ""), str(role or ""))
        return role if role in ALL_ROLES else ROLE_MIJOZ

    async def get(self, user_id) -> dict | None:
        return (await self.all()).get(str(user_id))

    async def role(self, user_id) -> str:
        uid = str(user_id)
        if uid in self.owner_ids:
            return ROLE_ADMIN
        user = await self.get(uid)
        return self.normalize_role(user.get("role")) if user else ROLE_MIJOZ

    async def ids_with_roles(self, roles) -> list[int]:
        roles = set(roles)
        out = {int(uid) for uid, u in (await self.all()).items()
               if uid.lstrip("-").isdigit() and self.normalize_role(u.get("role")) in roles}
        if ROLE_ADMIN in roles:
            out |= {int(i) for i in self.owner_ids}
        return sorted(out)

    async def client_name_for(self, user_id) -> str | None:
        user = await self.get(user_id)
        if user and self.normalize_role(user.get("role")) == ROLE_DILLER:
            return user.get("client_name") or None
        return None

    async def diller_ids_for_client(self, client_name: str) -> list[int]:
        target = str(client_name or "").strip().lower()
        if not target:
            return []
        return sorted(
            int(uid) for uid, u in (await self.all()).items()
            if uid.lstrip("-").isdigit()
            and self.normalize_role(u.get("role")) == ROLE_DILLER
            and str(u.get("client_name", "")).strip().lower() == target
        )

    async def list(self) -> list[dict]:
        users = await self.all(fresh=True)
        out = []
        for uid, u in users.items():
            out.append({
                "id": uid,
                "name": u.get("name") or u.get("full_name") or "",
                "username": u.get("username") or "",
                "role": self.normalize_role(u.get("role")),
                "client_name": u.get("client_name") or "",
                "last_seen": u.get("last_seen") or "",
                "owner": uid in self.owner_ids,
            })
        out.sort(key=lambda x: (ALL_ROLES.index(x["role"]), x["name"].lower()))
        return out

    # --- yozish ---
    async def touch(self, user_id, full_name: str | None, username: str | None) -> None:
        """Foydalanuvchi ismini yangilaydi (admin rol berishi uchun ro'yxatda ko'rinadi)."""
        uid = str(user_id)
        user = await self.get(uid) or {}
        name = clean_text(full_name, 80)
        uname = clean_text(username, 64)
        if user.get("name") == name and user.get("username", "") == uname and user.get("last_seen", "")[:10] == now_str()[:10]:
            return
        await self.store.update(f"users/{uid}", {"name": name, "username": uname, "last_seen": now_str()})
        if self._cache is not None:
            self._cache.setdefault(uid, {}).update({"name": name, "username": uname, "last_seen": now_str()})

    async def set_role(self, actor_id, user_id, role: str, client_name: str = "") -> None:
        uid = str(user_id).strip()
        if not uid.lstrip("-").isdigit():
            raise ServiceError("Telegram ID faqat raqamlardan iborat bo'lishi kerak.")
        if role not in ALL_ROLES:
            raise ServiceError("Noma'lum rol.")
        if uid == str(actor_id) and role != ROLE_ADMIN:
            raise ServiceError("O'zingizni admin rolidan tushira olmaysiz.")
        if uid in self.owner_ids and role != ROLE_ADMIN:
            raise ServiceError("Bu foydalanuvchi OWNER_IDS orqali doimiy admin.")
        values = {"role": role, "role_updated_at": now_str(), "role_updated_by": str(actor_id)}
        if role == ROLE_DILLER:
            client_name = clean_text(client_name, 80)
            if not client_name:
                raise ServiceError("Diller uchun mijoz (kompaniya) nomini tanlang.")
            values["client_name"] = client_name
        else:
            values["client_name"] = None
        await self.store.update(f"users/{uid}", values)
        await self.store.push("audit_log", {
            "action": "set_role", "user_id": uid, "role": role,
            "client_name": values.get("client_name") or "", "by": str(actor_id), "at": now_str(),
        })
        self.invalidate()

    async def apply_role_assignments(self, assignments: dict[str, str]) -> list[str]:
        """ROLE_ASSIGN sozlamasidagi rollarni bir marta yozadi.

        Har bir (ID, rol) jufti faqat bir marta qo'llanadi — keyin paneldan o'zgartirilsa, qayta ustidan yozilmaydi.
        Qayta majburan qo'llash uchun yangi belgi qo'shiladi: "123:admin@2" (belgi o'zgarsa — yana bir marta yoziladi).
        """
        applied = await self.store.get("meta/role_assign") or {}
        done = []
        for uid, spec in assignments.items():
            role = spec.partition("@")[0]
            if role not in ALL_ROLES or role == ROLE_DILLER:  # diller uchun kompaniya nomi kerak — panel orqali
                continue
            if applied.get(uid) == spec:
                continue
            await self.store.update(f"users/{uid}", {"role": role, "role_updated_at": now_str(),
                                                     "role_updated_by": "ROLE_ASSIGN"})
            await self.store.set(f"meta/role_assign/{uid}", spec)
            await self.store.push("audit_log", {"action": "set_role", "user_id": uid, "role": role,
                                                "by": "ROLE_ASSIGN", "at": now_str()})
            done.append(f"{uid}:{role}")
        if done:
            self.invalidate()
        return done

    async def remove(self, actor_id, user_id) -> None:
        uid = str(user_id)
        if uid == str(actor_id):
            raise ServiceError("O'zingizni o'chira olmaysiz.")
        if uid in self.owner_ids:
            raise ServiceError("OWNER_IDS dagi foydalanuvchini o'chirib bo'lmaydi.")
        if not await self.get(uid):
            raise NotFound("Foydalanuvchi topilmadi.")
        await self.store.update(f"users/{uid}", {"role": ROLE_MIJOZ, "client_name": None})
        await self.store.push("audit_log", {"action": "revoke", "user_id": uid, "by": str(actor_id), "at": now_str()})
        self.invalidate()
