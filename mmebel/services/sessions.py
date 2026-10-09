"""Mobil ilova uchun kirish: Telegram bot orqali bir martalik tasdiq va sessiya tokenlari.

Oqim:
1. Ilova `start()` chaqiradi -> `code` (bot havolasiga qo'yiladi) va `poll_secret` (faqat ilovada) oladi.
2. Foydalanuvchi botda `/start login_<code>` ni bosadi -> bot `approve()` qiladi.
3. Ilova `poll(code, poll_secret)` bilan sessiya tokenini oladi.

`poll_secret` sababli havolani ko'rgan begona odam sessiyani o'g'irlay olmaydi.
Bazada tokenning o'zi emas, faqat SHA-256 xeshi saqlanadi.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from ..store import Store
from ..utils import clean_text, iter_records
from .errors import Conflict, NotFound, run_tx

LOGIN_TTL = 5 * 60
SESSION_TTL = 60 * 24 * 3600  # oxirgi foydalanishdan boshlab (faol xodim chiqarib yuborilmaydi)
TOUCH_EVERY = 3600
_CACHE_TTL = 60.0


def _h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class SessionService:
    def __init__(self, store: Store):
        self.store = store
        self._cache: dict[str, tuple[float, dict]] = {}

    # ---------- kirish ----------
    async def start(self, device: str = "") -> dict:
        code = secrets.token_urlsafe(18).replace("-", "x").replace("_", "y")[:24]
        poll_secret = secrets.token_urlsafe(32)
        await self.store.set(f"app_login/{code}", {
            "poll_hash": _h(poll_secret), "status": "pending", "created": int(time.time()),
            "device": clean_text(device, 120),
        })
        return {"code": code, "poll_secret": poll_secret, "expires_in": LOGIN_TTL}

    async def approve(self, code: str, user_id: int, approve: bool = True) -> dict:
        if not code.isalnum() or len(code) > 40:
            raise NotFound("Kirish havolasi noto'g'ri.")
        rec = await self.store.get(f"app_login/{code}")
        if not isinstance(rec, dict):
            raise NotFound("Kirish havolasi topilmadi yoki eskirgan.")
        if time.time() - float(rec.get("created", 0)) > LOGIN_TTL:
            await self.store.delete(f"app_login/{code}")
            raise Conflict("Kirish havolasi eskirgan. Ilovada qaytadan «Kirish» ni bosing.")

        def tx(cur):
            if not isinstance(cur, dict) or cur.get("status") != "pending":
                raise Conflict("Bu havola allaqachon ishlatilgan.")
            cur["status"] = "approved" if approve else "rejected"
            cur["user_id"] = str(user_id)
            return cur

        await run_tx(self.store, f"app_login/{code}", tx)
        return rec

    async def poll(self, code: str, poll_secret: str) -> dict:
        if not code or not code.isalnum() or len(code) > 40:
            raise NotFound("Kirish so'rovi topilmadi.")
        rec = await self.store.get(f"app_login/{code}")
        if not isinstance(rec, dict) or not hmac.compare_digest(rec.get("poll_hash", ""), _h(poll_secret or "")):
            raise NotFound("Kirish so'rovi topilmadi.")
        if time.time() - float(rec.get("created", 0)) > LOGIN_TTL:
            await self.store.delete(f"app_login/{code}")
            return {"status": "expired"}
        status = rec.get("status")
        if status == "pending":
            return {"status": "pending"}
        await self.store.delete(f"app_login/{code}")  # bir martalik
        if status != "approved":
            return {"status": "rejected"}
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        await self.store.set(f"sessions/{_h(token)}", {
            "user_id": rec["user_id"], "created": now, "last_used": now, "device": rec.get("device", ""),
        })
        return {"status": "approved", "token": token, "user_id": rec["user_id"]}

    # ---------- sessiyalar ----------
    async def resolve(self, token: str) -> str | None:
        """Token egasining Telegram ID sini qaytaradi (yaroqsiz bo'lsa None)."""
        if not token or len(token) > 128:
            return None
        key = _h(token)
        cached = self._cache.get(key)
        now = time.time()
        if cached and now - cached[0] < _CACHE_TTL:
            rec = cached[1]
        else:
            rec = await self.store.get(f"sessions/{key}")
            if not isinstance(rec, dict):
                self._cache.pop(key, None)
                return None
            self._cache[key] = (now, rec)
        if now - float(rec.get("last_used") or rec.get("created", 0)) > SESSION_TTL:
            await self.revoke_token(token)
            return None
        if now - float(rec.get("last_used", 0)) > TOUCH_EVERY:
            rec["last_used"] = int(now)
            await self.store.update(f"sessions/{key}", {"last_used": int(now)})
        return str(rec.get("user_id"))

    async def revoke_token(self, token: str) -> None:
        key = _h(token)
        self._cache.pop(key, None)
        await self.store.delete(f"sessions/{key}")

    async def revoke_user(self, user_id) -> int:
        raw = await self.store.get("sessions") or {}
        n = 0
        for key, rec in iter_records(raw):
            if str(rec.get("user_id")) == str(user_id):
                await self.store.delete(f"sessions/{key}")
                self._cache.pop(key, None)
                n += 1
        return n

    async def list_for(self, user_id) -> list[dict]:
        raw = await self.store.get("sessions") or {}
        return [{"device": r.get("device", ""), "created": r.get("created"), "last_used": r.get("last_used")}
                for _, r in iter_records(raw) if str(r.get("user_id")) == str(user_id)]

