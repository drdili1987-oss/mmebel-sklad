import json
import time
from datetime import timedelta

import pytest

from mmebel.config import Settings
from mmebel.server import assemble, build_app
from mmebel.store import MemoryStore
from mmebel.utils import now
from mmebel.web.auth import AuthError, sign_init_data, validate_init_data

TOKEN = "123456:TEST-token"
ADMIN, OMBOR, XODIM, DILLER, STRANGER = 1, 2, 3, 4, 5


def settings(**kw) -> Settings:
    base = dict(api_token=TOKEN, firebase_db_url="", firebase_credentials_json="", firebase_credentials_file="",
                public_url="https://example.test", webhook_secret="whsecret", cron_secret="cronsecret", port=0,
                owner_ids=[ADMIN], keep_awake=False, use_polling=False)
    base.update(kw)
    return Settings(**base)


def init_data(uid: int, auth_date: int | None = None, token: str = TOKEN) -> str:
    return sign_init_data({"auth_date": str(auth_date or int(time.time())), "query_id": "AAE",
                           "user": json.dumps({"id": uid, "first_name": f"U{uid}"})}, token)


def hdr(uid: int, **kw) -> dict:
    return {"Authorization": "tma " + init_data(uid, **kw)}


@pytest.fixture
async def client(aiohttp_client):
    store = MemoryStore({
        "users": {str(OMBOR): {"role": "omborchi"}, str(XODIM): {"role": "xodim"},
                  str(DILLER): {"role": "diller", "client_name": "Umid"}},
        "mebellar": {"BF07": {"id": "BF07", "nomi": "BF 07", "narxi": 340, "soni": 5}},
    })
    s = settings()
    services, bot, dp, scheduler, events = assemble(s, store)

    sent = []

    async def fake_send(chat_id, text, **kw):
        sent.append((chat_id, text))

    bot.send_message = fake_send  # tarmoqqa chiqmaslik uchun
    app = build_app(s, services, bot, dp, scheduler, events)

    async def fake_username():
        return "mmebel_test_bot"

    app["bot_username"] = fake_username
    c = await aiohttp_client(app)
    c.sent = sent
    c.store = store
    return c


# ---------- auth ----------
def test_init_data_validation():
    user = validate_init_data(init_data(42), TOKEN)
    assert user.id == 42
    with pytest.raises(AuthError):
        validate_init_data(init_data(42, token="999:other"), TOKEN)          # boshqa bot imzosi
    with pytest.raises(AuthError):
        validate_init_data(init_data(42, auth_date=int(time.time()) - 90000), TOKEN)  # eskirgan
    tampered = init_data(42).replace("%22id%22%3A+42", "%22id%22%3A+1")
    with pytest.raises(AuthError):
        validate_init_data(tampered, TOKEN)                                  # ID soxtalashtirilgan
    with pytest.raises(AuthError):
        validate_init_data("", TOKEN)


async def test_api_requires_auth(client):
    r = await client.get("/api/me")
    assert r.status == 401
    r = await client.get("/api/me", headers={"Authorization": "tma user=%7B%22id%22%3A1%7D&hash=abc"})
    assert r.status == 401


async def test_non_staff_forbidden(client):
    for uid in (DILLER, STRANGER):
        r = await client.get("/api/me", headers=hdr(uid))
        assert r.status == 403


async def test_role_permissions(client):
    r = await client.get("/api/me", headers=hdr(ADMIN))
    assert (await r.json())["role"] == "admin"
    assert (await client.get("/api/debts", headers=hdr(OMBOR))).status == 403
    assert (await client.get("/api/users", headers=hdr(XODIM))).status == 403
    assert (await client.post("/api/orders/X/ready", headers=hdr(XODIM))).status == 403
    assert (await client.get("/api/debts", headers=hdr(ADMIN))).status == 200


async def test_prices_hidden_from_non_admin(client):
    r = await client.get("/api/products", headers=hdr(OMBOR))
    assert "price" not in (await r.json())["items"][0]
    r = await client.get("/api/products", headers=hdr(ADMIN))
    assert (await r.json())["items"][0]["price"] == 340


async def test_order_lifecycle_via_api(client):
    due = (now() + timedelta(days=3)).strftime("%Y-%m-%d")
    r = await client.post("/api/orders", headers=hdr(ADMIN),
                          json={"client_name": "Umid", "product": "BF 07", "amount": 2, "due_date": due})
    assert r.status == 201, await r.text()
    oid = (await r.json())["id"]
    assert any(cid == DILLER for cid, _ in client.sent)  # dillerga xabar ketdi

    items = (await (await client.get("/api/orders", headers=hdr(XODIM))).json())["items"]
    assert items[0]["id"] == oid and "total_price" not in items[0]

    assert (await client.post(f"/api/orders/{oid}/ready", headers=hdr(OMBOR))).status == 200
    r = await client.post(f"/api/orders/{oid}/deliver", headers=hdr(OMBOR), json={"driver": "Javxar", "price": 6})
    assert r.status == 200
    r = await client.post(f"/api/orders/{oid}/cancel", headers=hdr(OMBOR))
    assert r.status == 409  # yetkazilganni bekor qilib bo'lmaydi

    acc = await (await client.get("/api/accounts/Umid", headers=hdr(ADMIN))).json()
    assert acc["debt"] == 680
    r = await client.post("/api/accounts/Umid/settle", headers=hdr(ADMIN), json={"order_id": oid})
    assert (await r.json())["debt"] == 0


async def test_validation_errors_are_400(client):
    r = await client.post("/api/orders", headers=hdr(ADMIN), json={"client_name": "Umid", "product": "BF07",
                                                                   "amount": -1, "due_date": "2020-01-01"})
    assert r.status == 400
    r = await client.post("/api/orders", headers=hdr(ADMIN), data="not json")
    assert r.status == 400
    r = await client.put("/api/products/BF07/qty", headers=hdr(OMBOR), json={"qty": "5"})
    assert r.status == 400


async def test_user_management(client):
    r = await client.post("/api/users", headers=hdr(ADMIN), json={"id": "777", "role": "xodim"})
    assert r.status == 200
    assert (await client.get("/api/me", headers=hdr(777))).status == 200
    r = await client.post("/api/users", headers=hdr(ADMIN), json={"id": str(ADMIN), "role": "xodim"})
    assert r.status == 400  # o'zini tushira olmaydi


async def test_webhook_requires_secret(client):
    r = await client.post("/webhook", json={"update_id": 1})
    assert r.status == 401
    r = await client.post("/webhook", json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
    assert r.status == 401


async def test_cron_requires_secret(client):
    assert (await client.get("/cron/morning")).status == 404
    assert (await client.get("/cron/morning?key=bad")).status == 404
    r = await client.get("/cron/morning", headers={"X-Cron-Secret": "cronsecret"})
    assert r.status == 200
    first = (await r.json())["sent"]
    r = await client.get("/cron/morning", headers={"X-Cron-Secret": "cronsecret"})
    assert first is True and (await r.json())["sent"] is False  # kuniga bir marta


async def test_panel_static_and_headers(client):
    r = await client.get("/panel/")
    assert r.status == 200
    assert "Content-Security-Policy" in r.headers
    assert (await client.get("/panel/static/app.js")).status == 200
    assert (await client.get("/panel/static/../../config.py")).status in (403, 404)


# ---------- mobil ilova kirishi ----------
async def test_app_login_flow(client):
    r = await client.post("/api/auth/start", json={"device": "Android"})
    d = await r.json()
    assert d["bot_link"] == f"https://t.me/mmebel_test_bot?start=login_{d['code']}"
    services = client.server.app["services"]

    # tasdiqlanmaguncha kutadi; noto'g'ri secret bilan hech narsa olinmaydi
    assert (await (await client.post("/api/auth/poll", json={"code": d["code"], "poll_secret": d["poll_secret"]})).json())["status"] == "pending"
    assert (await client.post("/api/auth/poll", json={"code": d["code"], "poll_secret": "wrong"})).status == 404

    await services.sessions.approve(d["code"], OMBOR)
    res = await (await client.post("/api/auth/poll", json={"code": d["code"], "poll_secret": d["poll_secret"]})).json()
    assert res["status"] == "approved"
    token = res["token"]
    # bir martalik
    assert (await client.post("/api/auth/poll", json={"code": d["code"], "poll_secret": d["poll_secret"]})).status == 404

    bearer = {"Authorization": f"Bearer {token}"}
    me = await (await client.get("/api/me", headers=bearer)).json()
    assert me["role"] == "omborchi" and me["id"] == OMBOR
    assert (await client.get("/api/debts", headers=bearer)).status == 403

    # rol olib tashlansa sessiya ham bekor
    await client.post("/api/users", headers=hdr(ADMIN), json={"id": str(OMBOR), "role": "mijoz"})
    assert (await client.get("/api/me", headers=bearer)).status == 401

    assert (await client.get("/api/me", headers={"Authorization": "Bearer fake"})).status == 401


async def test_app_login_rejected_for_non_staff(client):
    d = await (await client.post("/api/auth/start", json={})).json()
    await client.server.app["services"].sessions.approve(d["code"], DILLER, approve=False)
    res = await (await client.post("/api/auth/poll", json={"code": d["code"], "poll_secret": d["poll_secret"]})).json()
    assert res["status"] == "rejected"


async def test_logout(client):
    services = client.server.app["services"]
    s = await services.sessions.start()
    await services.sessions.approve(s["code"], XODIM)
    token = (await services.sessions.poll(s["code"], s["poll_secret"]))["token"]
    bearer = {"Authorization": f"Bearer {token}"}
    assert (await client.post("/api/logout", headers=bearer)).status == 200
    assert (await client.get("/api/me", headers=bearer)).status == 401


async def test_session_expiry_is_sliding(client, monkeypatch):
    import mmebel.services.sessions as sess
    services = client.server.app["services"]
    s = await services.sessions.start()
    await services.sessions.approve(s["code"], XODIM)
    token = (await services.sessions.poll(s["code"], s["poll_secret"]))["token"]
    t0 = time.time()
    # 50 kundan keyin foydalanildi -> muddat yangilanadi
    monkeypatch.setattr(sess.time, "time", lambda: t0 + 50 * 86400)
    services.sessions._cache.clear()
    assert await services.sessions.resolve(token) == str(XODIM)
    # yana 50 kun (jami 100 kun, lekin oxirgi foydalanishdan 50) -> hali amal qiladi
    monkeypatch.setattr(sess.time, "time", lambda: t0 + 100 * 86400)
    services.sessions._cache.clear()
    assert await services.sessions.resolve(token) == str(XODIM)
    # 61 kun foydalanilmadi -> tugaydi
    monkeypatch.setattr(sess.time, "time", lambda: t0 + 161 * 86400)
    services.sessions._cache.clear()
    assert await services.sessions.resolve(token) is None


async def test_admin_dashboard_endpoint(client):
    due = (now() + timedelta(days=1)).strftime("%Y-%m-%d")
    await client.post("/api/orders", headers=hdr(ADMIN),
                      json={"client_name": "Umid", "product": "BF07", "amount": 2, "due_date": due})
    assert (await client.get("/api/dashboard/full", headers=hdr(OMBOR))).status == 403
    d = await (await client.get("/api/dashboard/full", headers=hdr(ADMIN))).json()
    assert len(d["revenue"]) == 12 and d["revenue"][-1]["revenue"] == 680
    assert len(d["deliveries"]) == 30
    assert {s["key"]: s["count"] for s in d["status"]} == {"prep": 1, "ready": 0, "late": 0}
    assert d["tomorrow"][0]["product_id"] == "BF07"
    assert (await client.get("/panel/dashboard")).status == 200


# ---------- push ----------
class FakeSender:
    def __init__(self):
        self.sent = []
        self.dead = set()

    def send(self, tokens, title, body):
        self.sent.append((tuple(tokens), title, body))
        return [t for t in tokens if t in self.dead]


async def test_push_register_and_delivery(client):
    services = client.server.app["services"]
    fake = FakeSender()
    services.push.sender = fake
    tok = "fcm-token-" + "x" * 40
    r = await client.post("/api/push/register", headers=hdr(OMBOR), json={"token": tok, "device": "Pixel"})
    assert r.status == 200 and (await r.json())["enabled"] is True
    # boshqa akkaunt shu telefonda kirsa, token unga o'tadi
    await client.post("/api/push/register", headers=hdr(XODIM), json={"token": tok})
    assert await services.push.tokens_for(OMBOR) == [] and await services.push.tokens_for(XODIM) == [tok]

    due = (now() + timedelta(days=2)).strftime("%Y-%m-%d")
    await client.post("/api/orders", headers=hdr(ADMIN),
                      json={"client_name": "Umid", "product": "BF07", "amount": 1, "due_date": due})
    await services.push.drain()
    assert any(tok in t and "Yangi buyurtma" in title for t, title, _ in fake.sent)

    # yaroqsiz token o'chiriladi
    fake.dead.add(tok)
    await services.push.notify(XODIM, "t", "b")
    assert await services.push.tokens_for(XODIM) == []
    assert (await client.post("/api/push/register", headers=hdr(XODIM), json={"token": "short"})).status == 400


def test_split_message():
    from mmebel.push import split_message
    t, b = split_message("🔔 Yangi buyurtma!\n\n🆔 X-1\n🧑 Diller: Umid")
    assert t == "🔔 Yangi buyurtma!" and b == "🆔 X-1 · 🧑 Diller: Umid"
