"""Web Push (RFC 8030 / 8291 / 8292) — iPhone'dagi o'rnatilgan web-ilova va brauzerlar uchun.

Tashqi kutubxonasiz: shifrlash `cryptography` (google-auth orqali allaqachon bor), yuborish aiohttp.
VAPID kaliti `VAPID_PRIVATE_KEY` muhit o'zgaruvchisida (base64url, 32 bayt). Yaratish:
    python -c "from mmebel.webpush import VapidKey; print(VapidKey.generate())"
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import struct
import time
from urllib.parse import urlsplit

import aiohttp
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger(__name__)

# SSRF himoyasi: obuna manzili faqat ma'lum push xizmatlariga bo'lishi mumkin
ALLOWED_PUSH_HOSTS = (
    "web.push.apple.com",                 # iPhone / Safari
    "fcm.googleapis.com",                 # Chrome, Edge (Android/desktop)
    "push.services.mozilla.com",          # Firefox
    "notify.windows.com",                 # Edge (Windows)
)
RECORD_SIZE = 4096
MAX_PAYLOAD = 3000


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    s = str(s).strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def is_allowed_endpoint(url: str) -> bool:
    if not isinstance(url, str) or len(url) > 1024:
        return False
    try:
        p = urlsplit(url)
    except ValueError:
        return False
    host = (p.hostname or "").lower()
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        return False
    return any(host == h or host.endswith("." + h) for h in ALLOWED_PUSH_HOSTS)


def _pub_bytes(key: ec.EllipticCurvePublicKey) -> bytes:
    return key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)


class VapidKey:
    def __init__(self, private_b64u: str):
        raw = b64u_dec(private_b64u)
        if len(raw) != 32:
            raise ValueError("VAPID_PRIVATE_KEY 32 baytli base64url bo'lishi kerak.")
        self.key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
        self.public_b64u = b64u(_pub_bytes(self.key.public_key()))

    @staticmethod
    def generate() -> str:
        k = ec.generate_private_key(ec.SECP256R1())
        return b64u(k.private_numbers().private_value.to_bytes(32, "big"))

    def authorization(self, endpoint: str, subject: str) -> str:
        p = urlsplit(endpoint)
        header = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
        claims = b64u(json.dumps({"aud": f"{p.scheme}://{p.netloc}", "exp": int(time.time()) + 12 * 3600,
                                  "sub": subject}, separators=(",", ":")).encode())
        signing_input = f"{header}.{claims}".encode()
        r, s = decode_dss_signature(self.key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
        sig = b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        return f"vapid t={header}.{claims}.{sig}, k={self.public_b64u}"


def valid_keys(p256dh: str, auth: str) -> bool:
    try:
        pub, a = b64u_dec(p256dh), b64u_dec(auth)
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub)
    except Exception:  # noqa: BLE001
        return False
    return len(pub) == 65 and len(a) == 16


def encrypt(payload: bytes, p256dh: str, auth: str) -> bytes:
    """RFC 8291, aes128gcm: bitta yozuv."""
    ua_pub = b64u_dec(p256dh)
    secret = b64u_dec(auth)
    ua_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub)
    as_priv = ec.generate_private_key(ec.SECP256R1())
    as_pub = _pub_bytes(as_priv.public_key())
    shared = as_priv.exchange(ec.ECDH(), ua_key)
    ikm = HKDF(hashes.SHA256(), 32, salt=secret, info=b"WebPush: info\x00" + ua_pub + as_pub).derive(shared)
    salt = os.urandom(16)
    cek = HKDF(hashes.SHA256(), 16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
    ciphertext = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack("!IB", RECORD_SIZE, len(as_pub)) + as_pub + ciphertext


class WebPushSender:
    """Natija: o'chirilishi kerak bo'lgan (eskirgan) obuna manzillari."""

    def __init__(self, vapid: VapidKey, subject: str):
        self.vapid = vapid
        self.subject = subject

    async def send(self, subs: list[dict], payload: dict) -> list[str]:
        data = json.dumps(payload, ensure_ascii=False).encode()
        if len(data) > MAX_PAYLOAD:
            payload = {**payload, "body": str(payload.get("body", ""))[:200] + "…"}
            data = json.dumps(payload, ensure_ascii=False).encode()[:MAX_PAYLOAD]
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = await asyncio.gather(*(self._one(session, s, data) for s in subs), return_exceptions=True)
        return [s["endpoint"] for s, r in zip(subs, results, strict=False) if r is True]

    async def _one(self, session: aiohttp.ClientSession, sub: dict, data: bytes) -> bool:
        """True — obuna eskirgan, o'chirish kerak."""
        endpoint = sub["endpoint"]
        if not is_allowed_endpoint(endpoint):
            return True
        headers = {
            "TTL": "86400",
            "Urgency": "high",
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "Authorization": self.vapid.authorization(endpoint, self.subject),
        }
        body = encrypt(data, sub["p256dh"], sub["auth"])
        try:
            async with session.post(endpoint, data=body, headers=headers, allow_redirects=False) as resp:
                if resp.status in (404, 410):
                    return True
                if resp.status >= 400:
                    log.warning("Web push %s: %s %s", urlsplit(endpoint).hostname, resp.status,
                                (await resp.text())[:200])
        except Exception as e:  # noqa: BLE001 — tarmoq
            log.warning("Web push xatosi (%s): %s", urlsplit(endpoint).hostname, e)
        return False
