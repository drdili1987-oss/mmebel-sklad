"""Mobil ilovaga push-bildirishnomalar (Firebase Cloud Messaging).

Telegram xabari qaysi xodimga ketsa, o'sha xodimning ilova o'rnatilgan telefonlariga ham push yuboriladi.
Tokenlar `push_tokens/{telegram_id}/{xesh}` da saqlanadi; yaroqsiz bo'lib qolganlari avtomatik o'chiriladi.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging

from .store import Store
from .utils import clean_text, iter_records, now_str

log = logging.getLogger(__name__)
MAX_TOKENS_PER_USER = 5

# Ovozli xabarlar: tur -> (Android kanali, res/raw dagi fayl nomi).
# Android 8+ da ovoz kanalga bog'langan, shuning uchun har bir ovozga alohida kanal.
DEFAULT_CHANNEL = "orders"
SOUNDS: dict[str, tuple[str, str]] = {
    "new": ("order_new", "yangi_buyurtma"),
    "ready": ("order_ready", "buyurtma_tayyor"),
    "cancel": ("order_cancel", "buyurtma_bekor"),
}


def _key(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def split_message(text: str) -> tuple[str, str]:
    """Telegram matnidan (HTML olib tashlangan) push sarlavhasi va matnini ajratadi."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "Munosib Mebel", ""
    title = lines[0][:80]
    body = " · ".join(lines[1:6])
    return title, (body[:240] + "…") if len(body) > 240 else body


class FCMSender:
    """firebase_admin.messaging orqali yuboradi. Natija: o'chirilishi kerak bo'lgan tokenlar ro'yxati."""

    def send(self, tokens: list[str], title: str, body: str, sound: str | None = None) -> list[str]:
        from firebase_admin import messaging

        channel, raw = SOUNDS.get(sound or "", (DEFAULT_CHANNEL, None))
        an = (messaging.AndroidNotification(channel_id=channel, sound=raw, color="#3D8B2A", icon="ic_stat_notify")
              if raw else
              messaging.AndroidNotification(channel_id=channel, color="#3D8B2A", icon="ic_stat_notify",
                                            default_sound=True))
        msgs = [messaging.Message(
            token=t,
            notification=messaging.Notification(title=title, body=body),
            data={"sound": sound or ""},
            android=messaging.AndroidConfig(priority="high", notification=an),
        ) for t in tokens]
        resp = messaging.send_each(msgs)
        dead = []
        for t, r in zip(tokens, resp.responses, strict=False):
            if r.success:
                continue
            code = getattr(r.exception, "code", "") or ""
            name = type(r.exception).__name__
            if name in ("UnregisteredError", "SenderIdMismatchError") or code in ("NOT_FOUND", "INVALID_ARGUMENT"):
                dead.append(t)
            else:
                log.warning("Push yuborilmadi (%s): %s", name, r.exception)
        return dead


class PushService:
    def __init__(self, store: Store, sender=None):
        self.store = store
        self.sender = sender
        self._tasks: set[asyncio.Task] = set()

    @property
    def enabled(self) -> bool:
        return self.sender is not None

    async def register(self, user_id, token: str, device: str = "") -> None:
        token = (token or "").strip()
        if not (20 <= len(token) <= 4096) or any(c.isspace() for c in token):
            from .services import ServiceError
            raise ServiceError("Push token noto'g'ri.")
        uid = str(user_id)
        existing = await self.store.get(f"push_tokens/{uid}") or {}
        # Bitta token faqat bitta foydalanuvchiga tegishli (telefonda akkaunt almashsa)
        all_tokens = await self.store.get("push_tokens") or {}
        key = _key(token)
        updates = {f"{other}/{key}": None for other, recs in (all_tokens or {}).items()
                   if other != uid and isinstance(recs, dict) and key in recs}
        updates[f"{uid}/{key}"] = {"token": token, "device": clean_text(device, 120), "updated": now_str()}
        # Eng eski tokenlarni cheklash
        recs = sorted(iter_records(existing), key=lambda kv: kv[1].get("updated", ""))
        while len(recs) >= MAX_TOKENS_PER_USER:
            old_key, _ = recs.pop(0)
            if old_key != key:
                updates[f"{uid}/{old_key}"] = None
        await self.store.update("push_tokens", updates)

    async def unregister(self, user_id, token: str) -> None:
        if token:
            await self.store.delete(f"push_tokens/{user_id}/{_key(token)}")

    async def unregister_user(self, user_id) -> None:
        await self.store.delete(f"push_tokens/{user_id}")

    async def tokens_for(self, user_id) -> list[str]:
        raw = await self.store.get(f"push_tokens/{user_id}") or {}
        return [r["token"] for _, r in iter_records(raw) if r.get("token")]

    async def notify(self, user_id, title: str, body: str, sound: str | None = None) -> int:
        if not self.enabled:
            return 0
        tokens = await self.tokens_for(user_id)
        if not tokens:
            return 0
        try:
            dead = await asyncio.to_thread(self.sender.send, tokens, title, body, sound)
        except Exception as e:  # noqa: BLE001 — push Telegram xabarini to'xtatmasligi kerak
            log.warning("Push xatosi (%s): %s", user_id, e)
            return 0
        for t in dead:
            await self.unregister(user_id, t)
        return len(tokens) - len(dead)

    def notify_later(self, user_id, title: str, body: str, sound: str | None = None) -> None:
        """Fon vazifasi sifatida yuborish — bot javobini sekinlashtirmaydi."""
        if not self.enabled:
            return
        task = asyncio.create_task(self.notify(user_id, title, body, sound))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
