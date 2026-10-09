"""Telegram Mini App initData tekshiruvi.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
Server bot tokeni bilan HMAC imzoni tekshiradi — mijoz (brauzer) rolni yoki ID ni soxtalashtira olmaydi.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

MAX_AGE_SECONDS = 24 * 3600


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class TgUser:
    id: int
    first_name: str
    last_name: str
    username: str

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


def validate_init_data(init_data: str, bot_token: str, *, max_age: int = MAX_AGE_SECONDS,
                       now: float | None = None) -> TgUser:
    if not init_data or len(init_data) > 4096:
        raise AuthError("initData yo'q")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError as e:
        raise AuthError("initData formati noto'g'ri") from e
    received = pairs.pop("hash", "")
    if not received:
        raise AuthError("hash yo'q")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise AuthError("imzo noto'g'ri")
    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except ValueError as e:
        raise AuthError("auth_date noto'g'ri") from e
    current = now if now is not None else time.time()
    if auth_date <= 0 or current - auth_date > max_age:
        raise AuthError("sessiya eskirgan")
    try:
        user = json.loads(pairs.get("user", ""))
        return TgUser(id=int(user["id"]), first_name=str(user.get("first_name", "")),
                      last_name=str(user.get("last_name", "")), username=str(user.get("username", "")))
    except (ValueError, KeyError, TypeError) as e:
        raise AuthError("user maydoni noto'g'ri") from e


def sign_init_data(fields: dict, bot_token: str) -> str:
    """Testlar va lokal ishlab chiqish uchun: haqiqiy Telegram kabi imzolangan initData yasaydi."""
    from urllib.parse import urlencode

    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    sig = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": sig})
