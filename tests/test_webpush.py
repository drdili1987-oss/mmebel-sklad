"""Web Push: shifrlash (RFC 8291), VAPID imzosi, obunalar va API."""
import json
import struct

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from mmebel.webpush import VapidKey, b64u, b64u_dec, encrypt, is_allowed_endpoint
from tests.test_web import DILLER, XODIM, hdr

APPLE = "https://web.push.apple.com/QGh7abc"


def _browser_keys():
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return priv, b64u(pub), b64u(b"0123456789abcdef")


def _decrypt(priv, p256dh, auth, blob):
    """Brauzer tomoni (RFC 8291) — shifrlash to'g'riligini tekshirish uchun."""
    salt, rs, idlen = blob[:16], *struct.unpack("!IB", blob[16:21])
    as_pub = blob[21:21 + idlen]
    ct = blob[21 + idlen:]
    assert rs == 4096
    shared = priv.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    ikm = HKDF(hashes.SHA256(), 32, salt=b64u_dec(auth), info=b"WebPush: info\x00" + b64u_dec(p256dh) + as_pub).derive(shared)
    cek = HKDF(hashes.SHA256(), 16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(hashes.SHA256(), 12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
    pt = AESGCM(cek).decrypt(nonce, ct, None)
    assert pt.endswith(b"\x02")
    return pt[:-1]


def test_encrypt_roundtrip():
    priv, p256dh, auth = _browser_keys()
    msg = json.dumps({"title": "🔔 Yangi buyurtma!", "body": "BF07 · 2 ta"}, ensure_ascii=False).encode()
    assert _decrypt(priv, p256dh, auth, encrypt(msg, p256dh, auth)) == msg


def test_vapid_jwt_signature_valid():
    v = VapidKey(VapidKey.generate())
    auth = v.authorization(APPLE, "https://example.test")
    t = auth.split("t=")[1].split(",")[0]
    k = auth.split("k=")[1]
    assert k == v.public_b64u
    head, claims, sig = t.split(".")
    c = json.loads(b64u_dec(claims))
    assert c["aud"] == "https://web.push.apple.com" and c["sub"] == "https://example.test"
    raw = b64u_dec(sig)
    der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64u_dec(k))
    pub.verify(der, f"{head}.{claims}".encode(), ec.ECDSA(hashes.SHA256()))  # xato bo'lsa — exception


def test_endpoint_allowlist():
    assert is_allowed_endpoint(APPLE)
    assert is_allowed_endpoint("https://fcm.googleapis.com/fcm/send/x")
    assert is_allowed_endpoint("https://wns2-par02p.notify.windows.com/w/?token=1")
    for bad in ("http://web.push.apple.com/x", "https://evil.com/x", "https://web.push.apple.com.evil.com/x",
                "https://user@web.push.apple.com/x", "https://web.push.apple.com:8443/x", "https://169.254.169.254/",
                "", None, "https://web.push.apple.com/" + "a" * 2000):
        assert not is_allowed_endpoint(bad), bad


class FakeWeb:
    def __init__(self):
        self.vapid = VapidKey(VapidKey.generate())
        self.sent, self.dead = [], set()

    async def send(self, subs, payload):
        self.sent.append(([s["endpoint"] for s in subs], payload))
        return [s["endpoint"] for s in subs if s["endpoint"] in self.dead]


def _sub(endpoint=APPLE):
    _, p256dh, auth = _browser_keys()
    return {"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}}


async def test_web_subscribe_api_and_delivery(client):
    services = client.server.app["services"]
    r = await client.get("/api/push/web/key", headers=hdr(XODIM))
    assert (await r.json())["key"] is None                     # VAPID yo'q — o'chiq
    fake = FakeWeb()
    services.push.web = fake
    r = await client.get("/api/push/web/key", headers=hdr(XODIM))
    assert (await r.json())["key"] == fake.vapid.public_b64u

    bad = await client.post("/api/push/web/subscribe", headers=hdr(XODIM),
                            json={"subscription": _sub("https://evil.com/x")})
    assert bad.status == 400
    sub = _sub()
    assert (await client.post("/api/push/web/subscribe", headers=hdr(XODIM), json={"subscription": sub})).status == 200
    # diller ham obuna bo'la oladi; shu endpoint unga o'tadi
    assert (await client.post("/api/push/web/subscribe", headers=hdr(DILLER), json={"subscription": sub})).status == 200
    assert await services.push.web_subs_for(XODIM) == []
    assert len(await services.push.web_subs_for(DILLER)) == 1

    r = await client.post("/api/push/test", headers=hdr(DILLER), json={"sound": "new"})
    assert (await r.json())["sent"] == 1
    assert fake.sent[-1][1]["kind"] == "new" and fake.sent[-1][0] == [APPLE]

    fake.dead.add(APPLE)                                       # eskirgan obuna o'chiriladi
    await services.push.notify(DILLER, "t", "b")
    assert await services.push.web_subs_for(DILLER) == []


async def test_web_subscription_limit_and_logout(client):
    services = client.server.app["services"]
    services.push.web = FakeWeb()
    eps = [f"{APPLE}{i}" for i in range(7)]
    for ep in eps:
        await services.push.web_subscribe(XODIM, _sub(ep))
    subs = await services.push.web_subs_for(XODIM)
    assert len(subs) == 5 and {s["endpoint"] for s in subs} == set(eps[2:])
    await client.post("/api/logout", headers=hdr(XODIM), json={"web_endpoint": eps[-1]})
    assert len(await services.push.web_subs_for(XODIM)) == 4


async def test_pwa_files_served(client):
    r = await client.get("/panel/sw.js")
    assert r.status == 200 and "javascript" in r.headers["Content-Type"]
    assert "showNotification" in await r.text()
    r = await client.get("/panel/manifest.webmanifest")
    assert r.status == 200 and r.headers["Content-Type"].startswith("application/manifest+json")
    m = json.loads(await r.text())
    assert m["display"] == "standalone" and m["scope"] == "/panel/"
    for icon in m["icons"]:
        assert (await client.get(icon["src"])).status == 200
    html = await (await client.get("/panel/")).text()
    assert 'rel="manifest"' in html and "apple-touch-icon" in html
