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


async def test_omborchi_no_orders_no_new_models_no_prices(client):  # noqa: F811
    # zakaz ochmaydi va o'zgartirmaydi
    assert (await new_order(client, "010", who=OMBOR)).status == 403
    oid = (await (await new_order(client, "011")).json())["id"]
    r = await client.patch(f"/api/orders/{oid}", headers=hdr(OMBOR), json={"serial": "012"})
    assert r.status == 403
    # narxlarni ko'rmaydi
    o = await (await client.get(f"/api/orders/{oid}", headers=hdr(OMBOR))).json()
    assert "price" not in o and "total_price" not in o
    items = (await (await client.get("/api/products", headers=hdr(OMBOR))).json())["items"]
    assert items and all("price" not in p for p in items)
    me = await (await client.get("/api/me", headers=hdr(OMBOR))).json()
    assert "clients" not in me["meta"]
    # mavjud mebelni omborga qo'sha oladi, yangi modelni qo'sha olmaydi; narx yuborsa ham e'tiborsiz
    r = await client.post("/api/products", headers=hdr(OMBOR), json={"name": "BF 07", "qty": 9, "price": 1})
    assert r.status == 201 and "narxi" not in await r.json()
    assert (await client.app["services"].inventory.get("BF07"))["narxi"] == 340
    r = await client.post("/api/products", headers=hdr(OMBOR), json={"name": "Yangi model X", "qty": 1})
    assert r.status == 400


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


async def test_admin_custom_price_kept_for_known_product(client):  # noqa: F811
    """O'zgarishli mebelga kiritilgan narx katalog narxi bilan almashib ketmasin."""
    r = await new_order(client, "050", price=500, changed=True)
    o = await (await client.get(f"/api/orders/{(await r.json())['id']}", headers=hdr(ADMIN))).json()
    assert o["price"] == 500 and o["total_price"] == 500


async def test_admin_edits_product_and_price(client):  # noqa: F811
    services = client.app["services"]
    oid = (await (await new_order(client, "060")).json())["id"]
    stock_before = (await services.inventory.get("BF07"))["soni"]
    r = await client.patch(f"/api/orders/{oid}", headers=hdr(ADMIN), json={"product": "Maxsus divan", "price": 610})
    assert r.status == 200, await r.text()
    o = await services.orders.get(oid)
    assert o["product_id"] == "Maxsus divan" and o["price"] == 610 and o["total_price"] == 610
    assert (await services.inventory.get("BF07"))["soni"] == stock_before + 1     # eski mebel omborga qaytdi
    # yetkazilgandan keyin narx tuzatiladi — qarz qayta hisoblanadi; mebel nomi esa o'zgarmaydi
    await services.orders.deliver(ADMIN, oid, driver="Dilmurod", price=0)
    assert (await services.finance.account("Umid")).debt == 610
    r = await client.patch(f"/api/orders/{oid}", headers=hdr(ADMIN), json={"price": 590})
    assert r.status == 200
    assert (await services.finance.account("Umid")).debt == 590
    assert (await client.patch(f"/api/orders/{oid}", headers=hdr(ADMIN), json={"product": "BF 07"})).status == 409
    # omborchiga narx haqida xabar bormaydi
    assert not any("590" in t for uid, t in client.sent if str(uid) == str(OMBOR))


async def test_admin_renames_user_and_fixes_wrong_id(client):  # noqa: F811
    services = client.app["services"]
    # telefon raqami ID sifatida kiritilgan xodim
    await client.post("/api/users", headers=hdr(ADMIN), json={"id": "998901112233", "role": "xodim", "name": "Bobur"})
    u = await services.users.get("998901112233")
    assert u["role"] == "xodim" and u["name"] == "Bobur"
    r = await client.patch("/api/users/998901112233", headers=hdr(ADMIN), json={"name": "Bobur usta", "new_id": "555"})
    assert r.status == 200 and (await r.json())["id"] == "555"
    assert await services.users.get("998901112233") is None
    moved = await services.users.get("555")
    assert moved["role"] == "xodim" and moved["name"] == "Bobur usta"
    # Telegram'dagi ism admin yozgan ismni almashtirmaydi
    await services.users.touch(555, "Bobur T", "bobur")
    assert (await services.users.get("555"))["name"] == "Bobur usta"
    # rolli foydalanuvchi ustiga yozilmaydi; admin o'zini/OWNER ni ko'chira olmaydi
    assert (await client.patch("/api/users/555", headers=hdr(ADMIN), json={"new_id": str(OMBOR)})).status == 409
    assert (await client.patch(f"/api/users/{ADMIN}", headers=hdr(ADMIN), json={"new_id": "999"})).status == 400
    assert (await client.patch("/api/users/555", headers=hdr(OMBOR), json={"name": "x"})).status == 403


async def _scope_ids(c, scope, who=ADMIN):
    d = await (await c.get(f"/api/orders?scope={scope}", headers=hdr(who))).json()
    return {o["id"] for o in d["items"]}


async def test_return_to_warehouse_with_expense(client):  # noqa: F811
    services = client.app["services"]
    wid = await make_worker(client)
    oid = (await (await new_order(client, "070", collect=300)).json())["id"]
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
    # «Ha» — summa va sabab majburiy
    r = await client.post(f"/api/w/orders/{oid}/return", headers=hdr(WORKER_UID), json={"expense_yes": True, "expense": 20})
    assert r.status == 400
    r = await client.post(f"/api/w/orders/{oid}/return", headers=hdr(WORKER_UID),
                          json={"expense_yes": True, "expense": 20, "note": "Mijoz rad etdi, yuk tashuvchiga 20$"})
    assert r.status == 200, await r.text()
    # tasdiqlanguncha topshirib ham, qayta so'rab ham bo'lmaydi
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 300, "method": "naqd"})
    assert r.status == 409
    appr = await (await client.get("/api/approvals", headers=hdr(OMBOR))).json()
    assert [x["order_id"] for x in appr["returns"]] == [oid] and appr["returns"][0]["expense"] == 20
    r = await client.post(f"/api/orders/{oid}/return/resolve", headers=hdr(OMBOR), json={"approve": True})
    assert r.status == 200
    assert oid in await _scope_ids(client, "returned") and oid not in await _scope_ids(client, "assigned")
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert me["active"] == [] and me["cash"] == -20            # xarajatni sex ko'taradi — sex unga qarzdor
    assert (await services.finance.account("Umid")).debt == 0  # yetkazilmagan — dillerga qarz yo'q
    # qaytgan mebel qayta yuboriladi
    r = await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
    assert r.status == 200
    assert oid not in await _scope_ids(client, "returned")


async def test_return_rejected_keeps_order_with_worker(client):  # noqa: F811
    wid = await make_worker(client)
    oid = (await (await new_order(client, "071")).json())["id"]
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(ADMIN), json={"worker_id": wid})
    await client.post(f"/api/w/orders/{oid}/return", headers=hdr(WORKER_UID), json={"expense_yes": False})
    r = await client.post(f"/api/orders/{oid}/return/resolve", headers=hdr(ADMIN), json={"approve": False})
    assert r.status == 200
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert [o["id"] for o in me["active"]] == [oid] and me["cash"] == 0
    assert (await client.post(f"/api/orders/{oid}/return/resolve", headers=hdr(ADMIN),
                              json={"approve": True})).status == 409


async def test_defect_reassign_and_completion(client):  # noqa: F811
    services = client.app["services"]
    w1 = await make_worker(client)
    w2 = await make_worker(client, uid=78, name="Sardor", phone="+998 90 999 88 77")
    oid = (await (await new_order(client, "080", collect=300)).json())["id"]
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": w1})
    r = await client.post(f"/api/w/orders/{oid}/defect", headers=hdr(WORKER_UID),
                          json={"amount": 120, "method": "naqd"})
    assert r.status == 400                                      # izohsiz bo'lmaydi
    r = await client.post(f"/api/w/orders/{oid}/defect", headers=hdr(WORKER_UID),
                          json={"amount": 350, "method": "naqd", "note": "Fasad tirnalgan"})
    assert r.status == 400                                      # qoldiqdan ko'p
    r = await client.post(f"/api/w/orders/{oid}/defect", headers=hdr(WORKER_UID),
                          json={"amount": 120, "method": "naqd", "note": "Fasad tirnalgan, fabrikaga qaytarish kerak"})
    assert r.status == 200, await r.text()
    assert (await r.json())["left_uzs"] == 180000
    assert oid in await _scope_ids(client, "defect", OMBOR)
    assert (await services.finance.account("Umid")).debt == 340 - 120     # mebel mijozda — qarzga kiradi
    me1 = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert me1["active"] == [] and me1["cash"] == 120 and [o["id"] for o in me1["done"]] == [oid]
    # boshqa yig'uvchiga qayta yuboriladi — izoh va qolgan summa ko'rinadi
    r = await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": w2})
    assert r.status == 200, await r.text()
    me2 = await (await client.get("/api/w/me", headers=hdr(78))).json()
    o2 = me2["active"][0]
    assert o2["id"] == oid and o2["left"] == 180 and "Fasad" in o2["defect"]["note"]
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(78),
                          json={"correct": True, "amount": 180, "method": "naqd"})
    assert r.status == 200, await r.text()
    assert oid not in await _scope_ids(client, "defect")
    assert (await services.finance.account("Umid")).debt == 340 - 300
    me2 = await (await client.get("/api/w/me", headers=hdr(78))).json()
    assert me2["cash"] == 180 and me2["active"] == []


async def test_worker_edit_needs_approval_and_is_audited(client):  # noqa: F811
    services = client.app["services"]
    wid = await make_worker(client)
    oid = (await (await new_order(client, "090", collect=300)).json())["id"]
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
    await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                      json={"correct": True, "amount": 300, "method": "naqd"})
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    pid = me["done"][0]["payments"][0]["pay_id"]
    assert (await client.post(f"/api/w/pay/{pid}/edit", headers=hdr(WORKER_UID), json={"amount": 250})).status == 400
    r = await client.post(f"/api/w/pay/{pid}/edit", headers=hdr(WORKER_UID),
                          json={"amount": 250, "note": "Xato yozibman, 250 olganman"})
    assert r.status == 200
    # tasdiqlanguncha hech narsa o'zgarmaydi
    assert (await services.finance.account("Umid")).debt == 40
    assert (await client.post(f"/api/w/pay/{pid}/edit", headers=hdr(WORKER_UID),
                              json={"amount": 200, "note": "yana"})).status == 409
    appr = await (await client.get("/api/approvals", headers=hdr(ADMIN))).json()
    assert [e["pay_id"] for e in appr["edits"]] == [pid]
    r = await client.post(f"/api/wpay/{pid}/edit/resolve", headers=hdr(OMBOR), json={"approve": True})
    assert r.status == 200, await r.text()
    assert (await services.finance.account("Umid")).debt == 90
    me = await (await client.get("/api/w/me", headers=hdr(WORKER_UID))).json()
    assert me["cash"] == 250
    p = await services.workers.payment(pid)
    assert p["amount"] == 250 and p["history"][0]["from"] == 300 and p["history"][0]["to"] == 250


async def test_large_photo_upload_not_truncated(client):  # noqa: F811
    """Katta rasm (bir necha bo'lak) kesilmasdan Telegram'ga yetib borishi kerak."""
    seen = []
    fake_photo_bot(client)
    orig = client.app["events"].n.bot.send_photo

    async def spy(chat_id, photo, **kw):
        seen.append(len(photo.data))
        return await orig(chat_id, photo, **kw)

    client.app["events"].n.bot.send_photo = spy
    await make_worker(client)
    payload = b"\xff\xd8" + b"0" * 600_000
    r = await client.post("/api/w/photos", headers={**hdr(WORKER_UID), "Content-Type": "image/jpeg"}, data=payload)
    assert r.status == 201, await r.text()
    assert seen == [len(payload)]
    big = b"\xff\xd8" + b"0" * (5 * 1024 * 1024 + 10)
    r = await client.post("/api/w/photos", headers={**hdr(WORKER_UID), "Content-Type": "image/jpeg"}, data=big)
    assert r.status == 400


async def test_return_note_only_and_admin_removes_user(client):  # noqa: F811
    wid = await make_worker(client)
    oid = (await (await new_order(client, "090", collect=100)).json())["id"]
    assert (await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})).status == 200
    r = await client.post(f"/api/w/orders/{oid}/return", headers=hdr(WORKER_UID), json={"note": "mijoz uyda yo'q"})
    assert r.status == 200, await r.text()
    o = await (await client.get(f"/api/orders/{oid}", headers=hdr(ADMIN))).json()
    assert o["ret"]["expense"] == 0 and o["ret"]["note"] == "mijoz uyda yo'q"
    # faqat admin xodimni o'chira oladi
    assert (await client.delete(f"/api/users/{WORKER_UID}", headers=hdr(OMBOR))).status == 403
    assert (await client.delete(f"/api/users/{WORKER_UID}", headers=hdr(ADMIN))).status == 409  # buyurtma hali yig'uvchida
    assert (await client.post(f"/api/orders/{oid}/return/resolve", headers=hdr(OMBOR), json={"approve": True})).status == 200
    assert (await client.delete(f"/api/users/{WORKER_UID}", headers=hdr(ADMIN))).status == 200
    assert (await client.get("/api/w/me", headers=hdr(WORKER_UID))).status == 403
    ids = [u["id"] for u in (await (await client.get("/api/users", headers=hdr(ADMIN))).json())["items"]]
    assert str(WORKER_UID) not in ids


async def test_remove_user_blocked_with_cash_or_orders(client):  # noqa: F811
    wid = await make_worker(client)
    oid = (await (await new_order(client, "091", collect=100)).json())["id"]
    assert (await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})).status == 200
    r = await client.delete(f"/api/users/{WORKER_UID}", headers=hdr(ADMIN))
    assert r.status == 409 and "buyurtma" in (await r.json())["error"]
    ids = [u["id"] for u in (await (await client.get("/api/users", headers=hdr(ADMIN))).json())["items"]]
    assert str(WORKER_UID) in ids


async def test_settle_range_api_admin_only(client):  # noqa: F811
    url = "/api/accounts/Umid/settle_range"
    body = {"from": "2026-11-01", "to": "2026-11-19"}
    assert (await client.post(url, headers=hdr(OMBOR), json=body)).status == 403
    r = await client.post(url, headers=hdr(ADMIN), json=body)
    assert r.status == 200 and (await r.json())["count"] == 0
    r = await client.post(url, headers=hdr(ADMIN), json={"from": "bad", "to": "2026-11-19"})
    assert r.status == 400
    r = await client.post(url, headers=hdr(ADMIN), json={**body, "confirm": True})
    assert r.status == 409
    acc = await (await client.get("/api/accounts/Umid", headers=hdr(ADMIN))).json()
    assert acc["last_settlement"] is None


async def test_settlements_report_api_admin_only(client):  # noqa: F811
    for h in (hdr(OMBOR),):
        assert (await client.get("/api/reports/settlements?client=Umid", headers=h)).status == 403
        assert (await client.post("/api/reports/settlements/link", headers=h, json={"client": "Umid"})).status == 403
    r = await client.get("/api/reports/settlements?client=Umid", headers=hdr(ADMIN))
    assert r.status == 200 and (await r.json())["items"] == []
    assert (await client.post("/api/reports/settlements/link", headers=hdr(ADMIN), json={})).status == 400
    link = await (await client.post("/api/reports/settlements/link", headers=hdr(ADMIN), json={"client": "Umid"})).json()
    f = await client.get(link["url"])                      # Authorization'siz, bir martalik havola
    assert f.status == 200 and f.headers["Content-Type"] == "application/pdf"
    assert (await f.read()).startswith(b"%PDF")


# ---------- so'm va dollar kursi (API) ----------
async def test_fx_endpoints_admin_only_and_convert(client):  # noqa: F811
    r = await client.post("/api/fx", headers=hdr(OMBOR), json={"rate": 12500})
    assert r.status == 403
    assert (await client.get("/api/fx", headers=hdr(OMBOR))).status == 403
    r = await client.post("/api/fx", headers=hdr(ADMIN), json={"rate": 12500})
    assert r.status == 200 and (await r.json())["rate"] == 12500
    assert (await client.post("/api/fx", headers=hdr(ADMIN), json={"rate": 3})).status == 400
    assert (await client.get("/api/fx/convert?ming=1", headers=hdr(OMBOR))).status == 403   # kurs faqat adminga
    r = await client.get("/api/fx/convert?ming=48534", headers=hdr(ADMIN))
    j = await r.json()
    assert j["uzs"] == 48_534_000 and j["rate"] == 12500 and j["usd"] == 3882.72


async def test_worker_pays_in_uzs_rate_frozen_and_checked(client):  # noqa: F811
    await client.post("/api/fx", headers=hdr(ADMIN), json={"rate": 12000})
    wid = await make_worker(client)
    oid = (await (await new_order(client, "090", collect=1800)).json())["id"]      # 1 800 000 so'm = 150$
    o = next(x for x in (await (await client.get("/api/orders", headers=hdr(ADMIN))).json())["items"] if x["id"] == oid)
    assert o["collect_uzs"] == 1_800_000 and o["collect"] == 150
    xo = next(x for x in (await (await client.get("/api/orders", headers=hdr(XODIM))).json())["items"] if x["id"] == oid)
    assert "collect" not in xo and "collect_uzs" not in xo                      # xodim qoldiqni ko'rmaydi
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": True, "amount": 1500, "method": "naqd"})
    assert r.status == 400 and "1 800 000" in (await r.json())["error"]         # kutilganidan farq — izoh shart
    await client.post("/api/fx", headers=hdr(ADMIN), json={"rate": 13000})      # kurs o'zgardi
    r = await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID),
                          json={"correct": False, "amount": 1500, "method": "naqd", "note": "300 ming keyin beradi"})
    assert r.status == 200, await r.text()
    pays = await client.app["services"].workers.payments(order_id=oid)
    assert pays[0]["uzs"] == 1_500_000 and pays[0]["rate"] == 13000 and pays[0]["amount"] == 115.38
    hist = [h for h in await client.app["services"].finance.history("Umid") if h["order_id"] == oid]
    assert hist[0]["uzs"] == 1_500_000 and hist[0]["rate"] == 13000 and hist[0]["partial_payment"] == 115.38
    assert await client.app["services"].workers.remaining_uzs(oid, await client.app["services"].orders.get(oid)) == 300_000


async def test_legacy_payment_migration_to_uzs(client):  # noqa: F811
    svc = client.app["services"]
    wid = await make_worker(client)
    oid = (await (await new_order(client, "095", collect=1000)).json())["id"]     # rate 1000: 1000$
    await client.post(f"/api/orders/{oid}/assign", headers=hdr(OMBOR), json={"worker_id": wid})
    await client.post(f"/api/w/orders/{oid}/handover", headers=hdr(WORKER_UID), json={"correct": True, "amount": 1000, "method": "naqd"})
    # eski yozuvga o'xshatamiz: so'm maydonlarini olib tashlaymiz
    pay = (await svc.workers.payments(order_id=oid))[0]
    await svc.store.update(f"wpay/{pay['id']}", {"uzs": None, "rate": None})
    hist = [h for h in await svc.finance.history("Umid") if h["order_id"] == oid][0]
    await svc.store.update(f"accounting_history/Umid/{hist['id']}", {"cur": None, "uzs": None, "rate": None})
    r = await client.get("/api/fx/legacy", headers=hdr(OMBOR))
    assert r.status == 403
    items = (await (await client.get("/api/fx/legacy", headers=hdr(ADMIN))).json())["items"]
    assert [i["pay_id"] for i in items] == [pay["id"]]
    r = await client.post("/api/fx/legacy", headers=hdr(ADMIN), json={"pay_ids": [pay["id"]], "rate": 12000})
    assert (await r.json())["migrated"] == 1
    p2 = await svc.workers.payment(pay["id"])
    assert p2["uzs"] == 1_000_000 and p2["amount"] == 83.33 and p2["orig_amount"] == 1000
    h2 = [h for h in await svc.finance.history("Umid") if h["order_id"] == oid][0]
    assert h2["partial_payment"] == 83.33 and h2["uzs"] == 1_000_000
    from mmebel.services.workers import worker_holder
    assert await svc.workers.balance(worker_holder(wid)) == 83.33                 # kassa ham so'm kursiga to'g'rilandi
    again = await (await client.post("/api/fx/legacy", headers=hdr(ADMIN), json={"pay_ids": [pay["id"]]})).json()
    assert again["migrated"] == 0                                                 # ikki marta o'tkazilmaydi
