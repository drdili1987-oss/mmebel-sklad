"""Ilova sozlamalari. Barcha maxfiy qiymatlar faqat muhit o'zgaruvchilaridan olinadi."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TASHKENT_TZ = timezone(timedelta(hours=5))


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _int_list(raw: str) -> list[int]:
    out: list[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


@dataclass(frozen=True)
class Settings:
    api_token: str
    firebase_db_url: str
    firebase_credentials_json: str
    firebase_credentials_file: str
    public_url: str
    webhook_secret: str
    cron_secret: str
    port: int
    owner_ids: list[int] = field(default_factory=list)
    keep_awake: bool = True
    use_polling: bool = False

    @property
    def webhook_path(self) -> str:
        return "/webhook"

    @property
    def webhook_url(self) -> str:
        return f"{self.public_url}{self.webhook_path}" if self.public_url else ""

    @property
    def panel_url(self) -> str:
        return f"{self.public_url}/panel/" if self.public_url else ""


_SECRET_RE = re.compile(r"[A-Za-z0-9_-]{1,256}")


def _derive_secret(token: str, purpose: str) -> str:
    return hashlib.sha256(f"{purpose}:{token}".encode()).hexdigest()[:48]


def webhook_secret(raw: str, token: str) -> str:
    """Telegram secret_token faqat [A-Za-z0-9_-], 1..256 belgi bo'lishi mumkin.

    Render generateValue kabi manbalar '+', '/', '=' qo'shishi mumkin — bunday holatda
    qiymatdan xavfsiz hex kalit hosil qilinadi (maxfiyligi saqlanadi).
    """
    if raw and _SECRET_RE.fullmatch(raw):
        return raw
    return _derive_secret(raw or token, "webhook")


def load_settings() -> Settings:
    token = _env("API_TOKEN")
    if not token:
        raise RuntimeError("API_TOKEN muhit o'zgaruvchisi o'rnatilmagan.")
    public_url = _env("PUBLIC_URL") or _env("RENDER_EXTERNAL_URL")
    return Settings(
        api_token=token,
        firebase_db_url=_env(
            "FIREBASE_DB_URL",
            "https://mmebel-bot-default-rtdb.europe-west1.firebasedatabase.app",
        ),
        firebase_credentials_json=_env("FIREBASE_CREDENTIALS_JSON"),
        firebase_credentials_file=_env(
            "FIREBASE_CREDENTIALS_FILE", str(BASE_DIR / "serviceAccountKey.json")
        ),
        public_url=public_url.rstrip("/"),
        webhook_secret=webhook_secret(_env("WEBHOOK_SECRET"), token),
        cron_secret=_env("CRON_SECRET"),
        port=int(_env("PORT", "8080") or 8080),
        owner_ids=_int_list(_env("OWNER_IDS")),
        keep_awake=_env("KEEP_AWAKE", "1") not in ("0", "false", "no"),
        use_polling=_env("USE_POLLING", "0") in ("1", "true", "yes"),
    )
