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
from .errors import Conflict, NotFound, ServiceError, run_tx

LOGIN_TTL = 5 * 60
CODE_TTL = 5 * 60
CODE_ATTEMPTS = 5            # bitta kod uchun noto'g'ri urinishlar
PHONE_RESEND = 60            # bir raqamga kod qayta yuborish oralig'i (soniya)
PHONE_PER_HOUR = 5           # bir raqamga soatiga kodlar soni
SESSION_TTL = 60 * 24 * 3600  # oxirgi foydalanishdan boshlab (faol xodim chiqarib yuborilmaydi)
TOUCH_EVERY = 3600
_CACHE_TTL = 60.0


def _h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_phone(raw: str) -> str | None:
    """'+998 90 123-45-67' / '901234567' -> '998901234567'. Noto'g'ri bo'lsa None."""
    digits = "".join(c for c in str(raw or "") if c.isdigit())
    if len(digits) == 9:            # O'zbekiston: operator kodi + raqam
        digits = "998" + digits
    if not 10 <= len(digits) <= 15:
        return None
    return digits


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

    async def peek(self, code: str) -> dict:
        """Kutilayotgan kirish so'rovi (tasdiqlashdan oldin foydalanuvchiga qurilmani ko'rsatish uchun)."""
        if not code or not code.isalnum() or len(code) > 40:
            raise NotFound("Kirish havolasi noto'g'ri.")
        rec = await self.store.get(f"app_login/{code}")
        if not isinstance(rec, dict):
            raise NotFound("Kirish havolasi topilmadi yoki eskirgan.")
        if time.time() - float(rec.get("created", 0)) > LOGIN_TTL:
            await self.store.delete(f"app_login/{code}")
            raise Conflict("Kirish havolasi eskirgan. Ilovada qaytadan «Kirish» ni bosing.")
        if rec.get("status") != "pending":
            raise Conflict("Bu havola allaqachon ishlatilgan.")
        return rec

    async def approve(self, code: str, user_id: int, approve: bool = True) -> dict:
        rec = await self.peek(code)

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
        token = await self._issue(rec["user_id"], rec.get("device", ""))
        return {"status": "approved", "token": token, "user_id": rec["user_id"]}

    async def _issue(self, user_id, device: str) -> str:
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        await self.store.set(f"sessions/{_h(token)}", {
            "user_id": str(user_id), "created": now, "last_used": now, "device": clean_text(device, 120),
        })
        return token

    # ---------- telefon raqam + botga kod ----------
    async def phone_start(self, phone: str, device: str = "") -> dict:
        """Kod yaratadi. Natija: request_id (ilovaga), user_id va code (botga yuborish uchun; raqam
        ro'yxatda bo'lmasa user_id=None). Raqam bor-yo'qligi ilovaga oshkor qilinmaydi."""
        digits = normalize_phone(phone)
        if not digits:
            raise ServiceError("Telefon raqamini to'liq kiriting, masalan: +998 90 123 45 67")
        now = time.time()
        rate = {}

        def tx(cur):
            recent = [t for t in (cur or []) if isinstance(t, (int, float)) and now - t < 3600]
            if recent and now - max(recent) < PHONE_RESEND:
                rate["wait"] = int(PHONE_RESEND - (now - max(recent))) + 1
                return recent
            if len(recent) >= PHONE_PER_HOUR:
                rate["wait"] = int(3600 - (now - min(recent))) + 1
                return recent
            return recent + [int(now)]

        await self.store.transaction(f"phone_rate/{digits}", tx)
        if rate.get("wait"):
            raise Conflict(f"Kod yaqinda yuborilgan. {rate['wait']} soniyadan so'ng qayta urinib ko'ring.")
        uid = await self.store.get(f"phones/{digits}")
        rid = secrets.token_urlsafe(24)
        code = f"{secrets.randbelow(10**6):06d}"
        await self.store.set(f"phone_login/{rid}", {
            "user_id": str(uid) if uid else "", "code_hash": _h(rid + code), "created": int(now),
            "attempts": 0, "device": clean_text(device, 120),
        })
        return {"request_id": rid, "expires_in": CODE_TTL, "user_id": str(uid) if uid else None, "code": code}

    async def phone_verify(self, request_id: str, code: str) -> dict:
        rid = str(request_id or "")
        if not rid or len(rid) > 64 or not rid.replace("-", "").replace("_", "").isalnum():
            raise NotFound("Kirish so'rovi topilmadi. Qaytadan kod oling.")
        rec = await self.store.get(f"phone_login/{rid}")
        if not isinstance(rec, dict):
            raise NotFound("Kirish so'rovi topilmadi. Qaytadan kod oling.")
        if time.time() - float(rec.get("created", 0)) > CODE_TTL:
            await self.store.delete(f"phone_login/{rid}")
            raise Conflict("Kod muddati tugadi. Qaytadan kod oling.")
        left = {}

        def tx(cur):
            if not isinstance(cur, dict):
                raise NotFound("Kirish so'rovi topilmadi. Qaytadan kod oling.")
            n = int(cur.get("attempts", 0)) + 1
            if n > CODE_ATTEMPTS:
                raise Conflict("Urinishlar tugadi. Qaytadan kod oling.")
            cur["attempts"] = n
            left["n"] = CODE_ATTEMPTS - n
            return cur

        await run_tx(self.store, f"phone_login/{rid}", tx)   # urinish avval sanaladi (parallel taxminga qarshi)
        code = "".join(c for c in str(code or "") if c.isdigit())
        ok = bool(rec.get("user_id")) and hmac.compare_digest(rec.get("code_hash", ""), _h(rid + code))
        if not ok:
            if left["n"] <= 0:
                await self.store.delete(f"phone_login/{rid}")
            raise Conflict(f"Kod noto'g'ri. Qolgan urinishlar: {left['n']}." if left["n"] > 0
                           else "Kod noto'g'ri. Urinishlar tugadi — qaytadan kod oling.")
        await self.store.delete(f"phone_login/{rid}")   # bir martalik
        token = await self._issue(rec["user_id"], rec.get("device", ""))
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

    async def cleanup(self) -> tuple[int, int]:
        """Eskirgan kirish so'rovlari va sessiyalarni o'chiradi (tungi vazifa)."""
        now = time.time()
        logins = sessions = 0
        for code, rec in iter_records(await self.store.get("app_login") or {}):
            if now - float(rec.get("created", 0) or 0) > LOGIN_TTL:
                await self.store.delete(f"app_login/{code}")
                logins += 1
        for rid, rec in iter_records(await self.store.get("phone_login") or {}):
            if now - float(rec.get("created", 0) or 0) > CODE_TTL:
                await self.store.delete(f"phone_login/{rid}")
                logins += 1
        for key, rec in iter_records(await self.store.get("sessions") or {}):
            if now - float(rec.get("last_used") or rec.get("created", 0) or 0) > SESSION_TTL:
                await self.store.delete(f"sessions/{key}")
                self._cache.pop(key, None)
                sessions += 1
        return logins, sessions

    async def list_for(self, user_id) -> list[dict]:
        raw = await self.store.get("sessions") or {}
        return [{"device": r.get("device", ""), "created": r.get("created"), "last_used": r.get("last_used")}
                for _, r in iter_records(raw) if str(r.get("user_id")) == str(user_id)]

