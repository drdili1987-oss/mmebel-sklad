"""Mebel yig'uvchilar: tartib raqam, tayinlash, topshirish, ostatka (naqd/karta), kassa topshirish."""
from datetime import timedelta
from types import SimpleNamespace

from mmebel.utils import now
from tests.test_web import (  # noqa: F401 — fixture
    ADMIN,
    DILLER,
    OMBOR,
    XODIM,
    client,
    hdr,
)

WORKER_UID = 77
DUE = (now() + timedelta(days=3)).strftime("%Y-%m-%d")


async def new_order(c, serial="001", client_name="Umid", who=ADMIN, **extra):
    r = await c.post("/api/orders", headers=hdr(who), json={"serial": serial, "client_name": client_name,
                                                            "product": "BF 07", "amount": 1, "due_date": DUE, **extra})
    return r


async def make_worker(c, uid=WORKER_UID, name="Javohir", phone="+998 90 111 22 33"):
    r = await c.post("/api/workers", headers=hdr(OMBOR), json={"name": name, "phone": phone})
    assert r.status == 201, await r.text()
    wid = (await r.json())["id"]
    # odam botga kirib raqamini ulashadi -> profilga bog'lanadi va rol oladi
    services = c.app["services"]
    digits = await services.users.set_phone(uid, phone)
    assert await services.workers.link_by_phone(uid, digits)
    return wid


def fake_photo_bot(c):
    bot = c.app["events"].n.bot
    counter = {"n": 0}

    async def send_photo(chat_id, photo, **kw):
        counter["n"] += 1
        return SimpleNamespace(photo=[SimpleNamespace(file_id=f"small{counter['n']}"),
                                      SimpleNamespace(file_id=f"FILE{counter['n']}")])

    async def send_media_group(chat_id, media, **kw):
        return []

    bot.send_photo = send_photo
    bot.send_media_group = send_media_group


async def test_serial_required_and_unique_per_diller(client):  # noqa: F811
    r = await client.post("/api/orders", headers=hdr(ADMIN),
                          json={"client_name": "Umid", "product": "BF 07", "amount": 1, "due_date": DUE})
    assert r.status == 400 and "Tartib raqam" in (await r.json())["error"]
    assert (await new_order(client, "001", collect=250)).status == 201
    r = await new_order(client, "001")
    assert r.status == 409 and "001" in (await r.json())["error"]
    assert (await new_order(client, "001", client_name="Comfort")).status == 201   # boshqa dillerda bo'lishi mumkin
    items = (await (await client.get("/api/orders", headers=hdr(ADMIN))).json())["items"]
    o = next(x for x in items if x["client_name"] == "Umid")
    assert o["serial"] == "001" and o["collect"] == 250
    # xodim qoldiq summani ko'rmaydi
    ox = (await (await client.get(f"/api/orders/{o['id']}", headers=hdr(XODIM))).json())
    assert "collect" not in ox


async def test_omborchi_creates_order_without_price_override(client):  # noqa: F811
    r = await new_order(client, "010", who=OMBOR, price=1)
    assert r.status == 201, await r.text()
    o = (await (await client.get(f"/api/orders/{(await r.json())['id']}", headers=hdr(ADMIN))).json())
    assert o["price"] == 340                            # omborchi narxni o'zgartira olmaydi
    r = await client.post("/api/orders", headers=hdr(OMBOR), json={"serial": "011", "client_name": "Umid",
                          "product": "Yangi divan", "amount": 1, "due_date": DUE, "price": 100})
    assert r.status == 400                              # shablonda yo'q mebel — faqat admin
    r = await client.post("/api/orders", headers=hdr(OMBOR), json={"serial": "012", "client_name": "Yangi firma",
                          "new_client": True, "product": "BF 07", "amount": 1, "due_date": DUE})
    assert r.status == 400                              # yangi dillerni admin qo'shadi


async def test_worker_profile_links_by_phone_and_access_rules(client):  # noqa: F811
    wid = await make_worker(client)
    assert await client.app["services"].users.role(WORKER_UID) == "yiguvchi"
    r = await client.get("/api/w/me", headers=hdr(WORKER_UID))
    assert r.status == 200
    me = await r.json()
    assert me["worker"]["id"] == wid and me["cash"] == 0 and me["active"] == []
    # yig'uvchi boshqa bo'limlarga kira olmaydi, boshqalar uning bo'limiga kira olmaydi
    for path in ("/api/orders", "/api/debts", "/api/workers", "/api/products"):
        assert (await client.get(path, headers=hdr(WORKER_UID))).status == 403, path
    for uid in (ADMIN, OMBOR, XODIM, DILLER):
        assert (await client.get("/api/w/me", headers=hdr(uid))).status == 403
    assert (await client.get("/api/workers", headers=hdr(XODIM))).status == 403
    # bir xil raqam bilan ikkinchi profil ochilmaydi
    r = await client.post("/api/workers", headers=hdr(ADMIN), json={"name": "Boshqa", "phone": "901112233"})
    assert r.status == 409


async def test_admin_sets_role_creates_profile(client):  # noqa: F811
    r = await client.post("/api/users", headers=hdr(ADMIN), json={"id": "88", "role": "yiguvchi"})
    assert r.status == 200
    assert (await client.get("/api/w/me", headers=hdr(88))).status == 200


async def test_full_flow_cash_card_and_transfers(client):  # noqa: F811
    fake_photo_bot(client)
    wid = await make_worker(client)
    oid = (await (await new_order(client, "001", collect=300)).json())["id"]
    oid2 = (await (await new_order(client, "002", collect=200)).json())["id"]
    for o in (oid, oid2):
        r = await client.post(f"/api/orders/{o}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
        assert r.status == 200, await r.text()
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert {o["id"] for o in me["active"]} == {oid, oid2}
    assert "price" not in me["active"][0] and me["active"][0]["collect"] in (300, 200)
    client.sent.clear()

    # «Yo'q» — izohsiz saqlanmaydi; «Ha» — kutilgandan boshqa summa izohsiz saqlanmaydi
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": False, "amount": 100, "method": "naqd"})
    assert r.status == 400
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 250, "method": "naqd"})
    assert r.status == 400
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 300, "method": "naqd", "note": ""})
    assert r.status == 200, await r.text()
    # ikkinchi marta topshirib bo'lmaydi
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 300, "method": "naqd"})
    assert r.status == 409
    assert any("topshirildi" in t for _, t in client.sent)

    # karta: rasmsiz bo'lmaydi; 6 ta rasm bo'lmaydi
    r = await client.post(f"/api/w/orders/{oid2}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 200, "method": "karta"})
    assert r.status == 400 and "skrinshot" in (await r.json())["error"]
    r = await client.post("/api/w/photos", headers={**hdr(WORKER_UID), "Content-Type": "text/plain"}, data=b"x" * 200)
    assert r.status == 400
    keys = []
    for _ in range(2):
        r = await client.post("/api/w/photos", headers={**hdr(WORKER_UID), "Content-Type": "image/jpeg"},
                              data=b"\xff\xd8" + b"0" * 500)
        assert r.status == 201, await r.text()
        keys.append((await r.json())["key"])
    r = await client.post(f"/api/w/orders/{oid2}/handover", headers=hdr(WORKER_UID),
                          json={"correct": False, "amount": 150, "method": "karta", "photos": ["boshqaning-kaliti"],
                                "note": "Chala ish qoldi"})
    assert r.status == 400                               # begona/yo'q rasm kaliti
    r = await client.post(f"/api/w/orders/{oid2}/handover", headers=hdr(WORKER_UID),
                          json={"correct": False, "amount": 150, "method": "karta", "photos": keys,
                                "note": "Chala ish qoldi, 50$ keyin beradi"})
    assert r.status == 200, await r.text()

    services = client.app["services"]
    o1 = await services.orders.get(oid)
    assert o1["status"] == "Biz yetkazib berdik" and o1["driver"] == "Javohir" and o1["handover"]["correct"] is True
    # diller qarzi: 2 × 340 − 300 (naqd) − 150 (karta)
    assert (await services.finance.account("Umid")).debt == 230
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert me["cash"] == 300                             # karta yig'uvchi kassasiga qo'shilmaydi
    assert {o["id"]: o["paid"] for o in me["done"]} == {oid: 300, oid2: 150}

    # qolgan 50$ ni keyin naqd oldi
    r = await client.post(f"/api/w/orders/{oid2}/payment", headers=hdr(WORKER_UID),
                          json={"amount": 50, "method": "naqd", "note": "qoldig'i"})
    assert r.status == 200
    assert (await services.finance.account("Umid")).debt == 180
    assert (await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json())["cash"] == 350

    # rasm: yig'uvchi o'zinikini, admin hammasini ko'radi; xodim ko'rmaydi
    pays = (await (await client.get(f"/api/orders/{oid2}/wpay", headers=hdr(ADMIN))).json())["items"]
    pid = next(p["pay_id"] for p in pays if p["method"] == "karta")
    assert next(p for p in pays if p["method"] == "karta")["photos"] == 2
    bot = client.app["events"].n.bot

    async def get_file(fid):
        return SimpleNamespace(file_path=f"photos/{fid}.jpg")

    async def download_file(path, dest):
        dest.write(b"JPEGDATA")

    bot.get_file, bot.download_file = get_file, download_file
    r = await client.get(f"/api/wphoto/{pid}/0", headers=hdr(WORKER_UID))
    assert r.status == 200 and await r.read() == b"JPEGDATA"
    assert (await client.get(f"/api/wphoto/{pid}/0", headers=hdr(ADMIN))).status == 200
    assert (await client.get(f"/api/wphoto/{pid}/5", headers=hdr(ADMIN))).status == 404
    assert (await client.get(f"/api/wphoto/{pid}/0", headers=hdr(XODIM))).status == 404

    # kassani omborchiga topshirish -> omborchi tasdiqlaydi
    r = await client.post("/api/w/transfer", headers=hdr(WORKER_UID), json={"to": "omborchi", "amount": 500})
    assert r.status == 400                               # kassadagidan ko'p emas
    r = await client.post("/api/w/transfer", headers=hdr(WORKER_UID), json={"to": "omborchi"})
    assert r.status == 201
    tid = (await r.json())["transfer_id"]
    assert (await client.post("/api/w/transfer", headers=hdr(WORKER_UID), json={"to": "admin"})).status == 409
    summary = await (await client.get("/api/workers", headers=hdr(OMBOR))).json()
    assert [t["id"] for t in summary["pending"]] == [tid]
    r = await client.post(f"/api/cash/transfers/{tid}/resolve", headers=hdr(OMBOR), json={"approve": True})
    assert r.status == 200, await r.text()
    res = await r.json()
    assert "Javohir omborchiga 350$ topshirdi" in res["text"]
    assert (await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json())["cash"] == 0
    r = await client.post(f"/api/cash/transfers/{tid}/resolve", headers=hdr(OMBOR), json={"approve": True})
    assert r.status == 409                               # ikki marta tasdiqlanmaydi

    # omborchi kassasidan adminga
    summary = await (await client.get("/api/workers", headers=hdr(OMBOR))).json()
    assert summary["my_cash"] == 350
    r = await client.post("/api/cash/transfer", headers=hdr(OMBOR), json={"amount": 350})
    assert r.status == 201
    tid2 = (await r.json())["transfer_id"]
    assert (await client.post(f"/api/cash/transfers/{tid2}/resolve", headers=hdr(OMBOR),
                              json={"approve": True})).status == 400   # o'zinikini tasdiqlay olmaydi
    r = await client.post(f"/api/cash/transfers/{tid2}/resolve", headers=hdr(ADMIN), json={"approve": True})
    assert r.status == 200
    summary = await (await client.get("/api/workers", headers=hdr(ADMIN))).json()
    assert summary["total_cash"] == 0 and summary["workers"][0]["month_cash"] == 350
    assert summary["workers"][0]["month_card"] == 150


async def test_unassigned_order_cannot_be_handed_over(client):  # noqa: F811
    await make_worker(client)
    oid = (await (await new_order(client, "001")).json())["id"]
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 0, "method": "naqd"})
    assert r.status == 404


async def test_settle_uses_general_payment_first(client):  # noqa: F811
    """Xato tuzatildi: umumiy to'lov + «To'landi» bitta pulni ikki marta ayirmasin."""
    services = client.app["services"]
    oid = (await (await new_order(client, "001")).json())["id"]
    await services.orders.deliver(ADMIN, oid, driver="Dilmurod", price=0)
    await services.finance.partial_payment(ADMIN, "Umid", 100)          # umumiy to'lov (buyurtmasiz)
    assert (await services.finance.account("Umid")).debt == 240
    res = await services.finance.settle_order(ADMIN, "Umid", oid)
    assert res["from_advance"] == 100 and res["received"] == 240
    assert (await services.finance.account("Umid")).debt == 0           # avval −100 bo'lib qolardi


async def test_delivered_report_sorted_by_serial_pdf_csv(client):  # noqa: F811
    services = client.app["services"]
    for serial in ("10", "2", "1"):
        oid = (await (await new_order(client, serial, collect=100)).json())["id"]
        await services.orders.deliver(ADMIN, oid, driver="Dilmurod", price=0)
    await new_order(client, "3")                                        # yetkazilmagan — hisobotga kirmaydi
    r = await client.get("/api/reports/delivered?client=Umid&unsettled=1", headers=hdr(ADMIN))
    assert r.status == 200, await r.text()
    d = await r.json()
    assert [x["serial"] for x in d["items"]] == ["1", "2", "10"]       # yetkazilgan sana emas, tartib raqami bo'yicha
    assert d["text"].splitlines()[1].startswith("1\tBF07\t340")
    assert (await client.get("/api/reports/delivered?client=Umid", headers=hdr(OMBOR))).status == 403

    r = await client.post("/api/reports/delivered/link", headers=hdr(ADMIN),
                          json={"client": "Umid", "unsettled": True, "format": "pdf"})
    url = (await r.json())["url"]
    r = await client.get(url)                                           # havola sarlavhasiz ochiladi
    assert r.status == 200 and r.headers["Content-Type"] == "application/pdf"
    assert (await r.read()).startswith(b"%PDF")
    r = await client.post("/api/reports/delivered/link", headers=hdr(ADMIN),
                          json={"client": "Umid", "format": "csv"})
    body = await (await client.get((await r.json())["url"])).read()
    assert body.startswith("﻿".encode()) and "Tartib raqam" in body.decode("utf-8-sig")
    assert (await client.get("/files/report/" + "x" * 32)).status == 404


def test_pdf_pages_have_20_rows_and_page_totals():
    from mmebel.services.delivered_report import as_pdf
    rows = [{"serial": f"{i:03d}", "product": "BF07", "variant": "", "amount": 1, "price": 100.0,
             "collected": 50.0, "delivered_at": "2026-11-12", "settled": False, "worker": ""} for i in range(1, 46)]
    pdf = as_pdf(rows, title="Yetkazilgan mebellar", subtitle="Comfort")
    import re
    assert len(re.findall(rb"/Type /Page\b(?!s)", pdf)) == 3            # 45 ta mebel -> 20 + 20 + 5
