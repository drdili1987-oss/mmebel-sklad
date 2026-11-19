import asyncio
from datetime import timedelta

import pytest

from mmebel.constants import (
    SELF_PICKUP_DRIVER,
    ST_CANCELLED,
    ST_DELIVERED,
    ST_PICKED_UP,
    ST_PREPARING,
    ST_READY,
    ST_SETTLED,
)
from mmebel.services import Conflict, Services, ServiceError
from mmebel.store import MemoryStore
from mmebel.utils import now

ADMIN = 1


def due(days=2):
    return (now() + timedelta(days=days)).strftime("%d.%m.%Y")


@pytest.fixture
def svc():
    store = MemoryStore({
        "mebellar": {
            "BF07": {"id": "BF07", "nomi": "BF 07", "modeli": "Spalniy", "narxi": "340", "soni": 3},
            "BF09": {"id": "BF09", "nomi": "BF 09", "modeli": "", "narxi": 200, "soni": 0},
        },
        "users": {"10": {"role": "ishchi"}, "20": {"role": "diller", "client_name": "Umid"}},
    })
    return Services(store, owner_ids=[ADMIN])


@pytest.mark.asyncio
async def test_roles(svc):
    assert await svc.users.role(ADMIN) == "admin"
    assert await svc.users.role(10) == "xodim"          # ishchi -> xodim
    assert await svc.users.role(20) == "diller"
    assert await svc.users.role(999) == "mijoz"
    assert await svc.users.diller_ids_for_client("umid") == [20]
    with pytest.raises(ServiceError):
        await svc.users.set_role(ADMIN, ADMIN, "xodim")
    await svc.users.set_role(ADMIN, 30, "omborchi")
    assert await svc.users.role(30) == "omborchi"


@pytest.mark.asyncio
async def test_create_reserves_only_available_stock(svc):
    o = await svc.orders.create(ADMIN, client_name="Umid", product="BF 07", amount=5, due_date=due())
    assert o["deducted_qty"] == 3
    assert o["total_price"] == 1700
    assert (await svc.inventory.get("BF07"))["soni"] == 0
    # bekor qilinganda faqat ayirilgan miqdor qaytadi
    await svc.orders.cancel(ADMIN, o["order_id"])
    assert (await svc.inventory.get("BF07"))["soni"] == 3
    with pytest.raises(Conflict):
        await svc.orders.cancel(ADMIN, o["order_id"])  # ikki marta bekor qilib bo'lmaydi
    assert (await svc.inventory.get("BF07"))["soni"] == 3


@pytest.mark.asyncio
async def test_create_validation(svc):
    with pytest.raises(ServiceError):
        await svc.orders.create(ADMIN, client_name="Umid", product="BF 07", amount="abc", due_date=due())
    with pytest.raises(ServiceError):
        await svc.orders.create(ADMIN, client_name="Umid", product="BF 07", amount=1, due_date="32.13.2026")
    with pytest.raises(ServiceError):
        await svc.orders.create(ADMIN, client_name="Umid", product="BF 07", amount=1, due_date=due(-3))
    with pytest.raises(ServiceError):
        await svc.orders.create(ADMIN, client_name="a/b", product="BF 07", amount=1, due_date=due())


@pytest.mark.asyncio
async def test_concurrent_reserve_never_oversells(svc):
    results = await asyncio.gather(*[svc.inventory.reserve("BF07", 1) for _ in range(10)])
    assert sum(results) == 3
    assert (await svc.inventory.get("BF07"))["soni"] == 0


@pytest.mark.asyncio
async def test_edit_amount_adjusts_stock(svc):
    o = await svc.orders.create(ADMIN, client_name="Umid", product="BF07", amount=1, due_date=due())
    assert (await svc.inventory.get("BF07"))["soni"] == 2
    await svc.orders.edit(ADMIN, o["order_id"], amount=3)
    assert (await svc.inventory.get("BF07"))["soni"] == 0
    await svc.orders.edit(ADMIN, o["order_id"], amount=2)
    assert (await svc.inventory.get("BF07"))["soni"] == 1
    got = await svc.orders.get(o["order_id"])
    assert got["deducted_qty"] == 2 and got["total_price"] == 680


@pytest.mark.asyncio
async def test_delivery_debt_and_settlement(svc):
    o = await svc.orders.create(ADMIN, client_name="Umid", product="BF07", amount=2, due_date=due())
    oid = o["order_id"]
    acc = await svc.finance.account("Umid")
    assert acc.debt == 0 and len(acc.pending) == 1

    await svc.orders.set_ready(ADMIN, oid)
    assert (await svc.orders.get(oid))["status"] == ST_READY
    res = await svc.orders.deliver(ADMIN, oid, driver="Dilmurod", price="3.5$")
    assert res["status"] == ST_DELIVERED and res["debt"] == 680
    assert await svc.finance.driver_balance("Dilmurod") == 3.5   # kasr yo'qolmaydi
    with pytest.raises(Conflict):
        await svc.orders.deliver(ADMIN, oid, driver="Dilmurod", price="6")  # qayta yetkazib bo'lmaydi
    assert await svc.finance.driver_balance("Dilmurod") == 3.5

    debt = await svc.finance.partial_payment(ADMIN, "Umid", 180, order_id=oid)
    assert debt == 500
    res = await svc.finance.settle_order(ADMIN, "Umid", oid)
    assert res["debt"] == 0 and res["received"] == 500
    assert (await svc.orders.get(oid))["status"] == ST_SETTLED
    with pytest.raises(Conflict):
        await svc.finance.settle_order(ADMIN, "Umid", oid)


@pytest.mark.asyncio
async def test_pickup_discount(svc):
    o = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    res = await svc.orders.deliver(ADMIN, o["order_id"], driver=SELF_PICKUP_DRIVER, price="10$")
    assert res["status"] == ST_PICKED_UP
    assert res["net"] == 190 and res["debt"] == 190
    assert await svc.finance.driver_balance(SELF_PICKUP_DRIVER) == 0


@pytest.mark.asyncio
async def test_settle_all_consumes_unlinked_payments(svc):
    """Eski xato: 'Barchasini hisob kitob' dan keyin qarz manfiy bo'lib qolardi."""
    for _ in range(2):
        o = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
        await svc.orders.deliver(ADMIN, o["order_id"], driver="Baxrom", price=6)
    pay = await svc.finance.create_pending_payment(20, "Umid", "Umid", "150$")
    _, debt = await svc.finance.resolve_payment(ADMIN, pay["pay_id"], True)
    assert debt == 250
    with pytest.raises(Conflict):
        await svc.finance.resolve_payment(ADMIN, pay["pay_id"], False)  # tasdiqlanganni rad etib bo'lmaydi
    res = await svc.finance.settle_all(ADMIN, "Umid")
    assert res["settled"] == 2 and res["received"] == 250 and res["debt"] == 0


@pytest.mark.asyncio
async def test_settle_all_keeps_advance_for_pending_order(svc):
    pending = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    done = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    await svc.orders.deliver(ADMIN, done["order_id"], driver="Baxrom", price=6)
    await svc.finance.partial_payment(ADMIN, "Umid", 50, order_id=pending["order_id"])
    res = await svc.finance.settle_all(ADMIN, "Umid")
    assert res["debt"] == -50  # avans saqlanadi


@pytest.mark.asyncio
async def test_diller_cancel_rules(svc):
    o = await svc.orders.create(20, client_name="Umid", product="BF07", amount=1, due_date=due(),
                                source="diller", client_tg_id=20)
    with pytest.raises(ServiceError):
        await svc.orders.cancel(21, o["order_id"], only_preparing=True, owner_tg_id=21)
    await svc.orders.set_ready(ADMIN, o["order_id"])
    with pytest.raises(Conflict):
        await svc.orders.cancel(20, o["order_id"], only_preparing=True, owner_tg_id=20)


@pytest.mark.asyncio
async def test_status_transitions(svc):
    o = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    await svc.orders.cancel(ADMIN, o["order_id"])
    with pytest.raises(Conflict):
        await svc.orders.set_ready(ADMIN, o["order_id"])
    assert (await svc.orders.get(o["order_id"]))["status"] == ST_CANCELLED


@pytest.mark.asyncio
async def test_legacy_orders_compatible(svc):
    """Eski formatdagi buyurtmalar (amount satr, total_price yo'q) to'g'ri hisoblanadi."""
    await svc.store.set("orders/OLD-1", {"client_name": "Umid", "product_id": "BF07", "amount": "2",
                                         "status": "Biz yetkazib berdik", "due_date": "01.01.2026"})
    await svc.store.set("orders/OLD-2", {"client": "umid", "product_id": "BF09", "amount": "1",
                                         "price": 150, "status": "Dillerni o'zi olib ketdi",
                                         "driver": SELF_PICKUP_DRIVER, "pickup_discount": "10"})
    acc = await svc.finance.account("Umid")
    assert acc.debt == 680 + 140
    assert ST_PREPARING  # import ishlatildi


@pytest.mark.asyncio
async def test_driver_payments(svc):
    assert await svc.finance.driver_payment(ADMIN, "Javxar", 20, "give") == -20
    assert await svc.finance.driver_payment(ADMIN, "Javxar", 5, "receive") == -15
    with pytest.raises(ServiceError):
        await svc.finance.driver_payment(ADMIN, "Javxar", -5, "give")


async def test_archive_moves_only_old_closed_orders(svc):
    old = "2026-01-05 10:00:00"
    await svc.store.update("orders", {
        "A-1": {"client_name": "Umid", "product_id": "BF07", "amount": 1, "status": "Hisob kitob qilindi",
                "created_at": old, "delivered_at": old, "price": 100},
        "A-2": {"client_name": "Umid", "product_id": "BF07", "amount": 1, "status": "Biz yetkazib berdik",
                "created_at": old, "delivered_at": old, "price": 100},
        "A-3": {"client_name": "Umid", "product_id": "BF07", "amount": 1, "status": "Bekor qilindi",
                "created_at": old},
    })
    debt_before = (await svc.finance.account("Umid")).debt
    n = await svc.orders.archive_old(days=60)
    assert n == 2
    assert set(await svc.orders.all()) == {"A-2"}          # qarzdagi buyurtma qoladi
    assert (await svc.finance.account("Umid")).debt == debt_before == 100
    sales = await svc.reports.sales()
    assert sum(m["total"] for m in sales) == 2              # arxiv statistikada hisoblanadi (bekor qilingansiz)


async def test_price_migration(svc):
    await svc.store.set("mebellar/X1", {"id": "X1", "nomi": "X 1", "narxi": "350 so'm", "soni": 1})
    await svc.catalog.run_migrations()
    assert (await svc.inventory.get("X1"))["narxi"] == 350


async def test_role_assign_applies_once(svc):
    assert await svc.users.apply_role_assignments({"555": "omborchi", "556": "diller", "557": "boss"}) == ["555:omborchi"]
    assert await svc.users.role(555) == "omborchi"
    await svc.users.set_role(ADMIN, 555, "xodim")              # keyin paneldan o'zgartirildi
    assert await svc.users.apply_role_assignments({"555": "omborchi"}) == []
    assert await svc.users.role(555) == "xodim"                # qayta ustidan yozilmaydi


async def test_role_assign_tag_forces_reapply(svc):
    await svc.users.apply_role_assignments({"555": "admin"})
    await svc.users.set_role(ADMIN, 555, "omborchi")           # adashib o'zgartirildi
    assert await svc.users.apply_role_assignments({"555": "admin"}) == []
    assert await svc.users.apply_role_assignments({"555": "admin@2"}) == ["555:admin"]
    assert await svc.users.role(555) == "admin"
    await svc.users.set_role(ADMIN, 555, "xodim")
    assert await svc.users.apply_role_assignments({"555": "admin@2"}) == []   # belgi o'sha — yana yozilmaydi


async def test_admin_custom_product_order(svc):
    due = (now() + timedelta(days=3)).strftime("%d.%m.%Y")
    name = "Shkaf 4 eshik (oq, 2.4 m) / oynali"
    try:
        await svc.orders.create(ADMIN, client_name="Umid", product=name, amount=1, due_date=due)
        raise AssertionError("narxsiz o'tib ketdi")
    except ServiceError as e:
        assert "narxini" in str(e)
    o = await svc.orders.create(ADMIN, client_name="Umid", product=name, amount=2, due_date=due, custom_price=450)
    assert o["product_id"] == name and o["total_price"] == 900 and o["deducted_qty"] == 0
    assert o["order_id"].split("-")[0].isalnum() and len(o["order_id"]) <= 20
    got = await svc.orders.get(o["order_id"])
    assert got["product_id"] == name
    # bekor qilish ombor bilan ishlaydi (yo'q mebel — hech narsa qaytmaydi, xato ham yo'q)
    await svc.orders.cancel(ADMIN, o["order_id"])
    # diller shablondan tashqari mebel bera olmaydi
    try:
        await svc.orders.create(ADMIN, client_name="Umid", product=name, amount=1, due_date=due,
                                source="diller", custom_price=1)
        raise AssertionError
    except ServiceError:
        pass


@pytest.mark.asyncio
async def test_previous_settlement_not_counted_again(svc):
    """Oy boshida hisob-kitob qilingan buyurtmalar keyingi hisob-kitobga qayta qo'shilmaydi."""
    # 1-davr: 2 ta yetkazilgan buyurtma (200$ + 340$), biriga 50$ qisman to'lov
    o1 = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    o2 = await svc.orders.create(ADMIN, client_name="Umid", product="BF07", amount=1, due_date=due())
    for o in (o1, o2):
        await svc.orders.deliver(ADMIN, o["order_id"], driver="Baxrom", price=6)
    await svc.finance.partial_payment(ADMIN, "Umid", 50, order_id=o1["order_id"])
    first = await svc.finance.settle_all(ADMIN, "Umid")
    assert first["settled"] == 2 and first["received"] == 490 and first["debt"] == 0

    # 2-davr: bitta yangi buyurtma (200$)
    o3 = await svc.orders.create(ADMIN, client_name="Umid", product="BF09", amount=1, due_date=due())
    await svc.orders.deliver(ADMIN, o3["order_id"], driver="Baxrom", price=6)
    acc = await svc.finance.account("Umid")
    assert [r["order_id"] for r in acc.unsettled] == [o3["order_id"]]   # eskilari ko'rinmaydi
    assert acc.debt == 200                                              # 540 qayta qo'shilmadi

    # hisobotda ham faqat yangisi (yopilmaganlar filtri)
    from mmebel.services.delivered_report import delivered_rows
    rows = await delivered_rows(svc, client="Umid", unsettled_only=True)
    assert [r["order_id"] for r in rows] == [o3["order_id"]]

    # 2-hisob-kitob faqat yangisini yopadi, summa faqat 200$
    second = await svc.finance.settle_all(ADMIN, "Umid")
    assert second["settled"] == 1 and second["received"] == 200 and second["debt"] == 0
    # eski buyurtmani qayta yopib bo'lmaydi, uchinchi marta bosilsa hech narsa yopilmaydi
    with pytest.raises(Conflict):
        await svc.finance.settle_order(ADMIN, "Umid", o1["order_id"])
    third = await svc.finance.settle_all(ADMIN, "Umid")
    assert third["settled"] == 0 and third["received"] == 0 and third["debt"] == 0


async def _delivered(svc, product, day, price=6):
    o = await svc.orders.create(ADMIN, client_name="Umid", product=product, amount=1, due_date=due())
    await svc.orders.deliver(ADMIN, o["order_id"], driver="Baxrom", price=price)
    await svc.store.update(f"orders/{o['order_id']}", {"delivered_at": f"{day} 10:00:00"})
    return o["order_id"]


@pytest.mark.asyncio
async def test_settle_range_only_selected_dates_and_not_twice(svc):
    from datetime import date
    a = await _delivered(svc, "BF09", "2026-11-01")      # 200$ — chegara (kiradi)
    b = await _delivered(svc, "BF07", "2026-11-19")      # 340$ — chegara (kiradi)
    c = await _delivered(svc, "BF09", "2026-11-20")      # 200$ — oraliqdan tashqarida
    await svc.finance.partial_payment(ADMIN, "Umid", 50, order_id=a)
    d1, d2 = date(2026, 11, 1), date(2026, 11, 19)

    pv = await svc.finance.settle_range(ADMIN, "Umid", d1, d2)          # faqat ko'rinish
    assert pv["count"] == 2 and pv["net_total"] == 540 and pv["paid_total"] == 50 and pv["to_receive"] == 490
    assert (await svc.orders.get(a))["status"] != ST_SETTLED             # hech narsa o'zgarmagan
    assert await svc.finance.last_settlement("Umid") is None

    res = await svc.finance.settle_range(ADMIN, "Umid", d1, d2, confirm=True)
    assert res["settled"] == 2 and res["received"] == 490 and res["debt"] == 200
    assert (await svc.orders.get(a))["status"] == ST_SETTLED
    assert (await svc.orders.get(b))["status"] == ST_SETTLED
    assert (await svc.orders.get(c))["status"] != ST_SETTLED             # sanasi tashqarida — tegilmagan
    last = await svc.finance.last_settlement("Umid")
    assert last["from"] == "2026-11-01" and last["to"] == "2026-11-19" and last["count"] == 2 and last["kind"] == "davr"

    # xuddi shu oraliq qayta tanlansa — hech narsa qayta sanalmaydi
    pv2 = await svc.finance.settle_range(ADMIN, "Umid", d1, d2)
    assert pv2["count"] == 0 and pv2["to_receive"] == 0
    with pytest.raises(Conflict):
        await svc.finance.settle_range(ADMIN, "Umid", d1, d2, confirm=True)
    assert (await svc.finance.account("Umid")).debt == 200


@pytest.mark.asyncio
async def test_settle_range_uses_unlinked_payment_once_and_validates(svc):
    from datetime import date
    await _delivered(svc, "BF09", "2026-11-05")           # 200$
    await _delivered(svc, "BF09", "2026-11-25")           # 200$ — tashqarida
    await svc.finance.partial_payment(ADMIN, "Umid", 150)  # umumiy to'lov
    pv = await svc.finance.settle_range(ADMIN, "Umid", date(2026, 11, 1), date(2026, 11, 10))
    assert pv["from_advance"] == 150 and pv["to_receive"] == 50
    res = await svc.finance.settle_range(ADMIN, "Umid", date(2026, 11, 1), date(2026, 11, 10), confirm=True)
    assert res["received"] == 50 and res["debt"] == 200   # 150$ avans ikki marta ayirilmadi
    with pytest.raises(ServiceError):
        await svc.finance.settle_range(ADMIN, "Umid", date(2026, 11, 10), date(2026, 11, 1))
    with pytest.raises(ServiceError):
        await svc.finance.settle_range(ADMIN, "Umid", None, date(2026, 11, 1))


@pytest.mark.asyncio
async def test_settle_all_records_last_settlement(svc):
    await _delivered(svc, "BF09", "2026-11-03")
    await _delivered(svc, "BF09", "2026-11-12")
    await svc.finance.settle_all(ADMIN, "Umid")
    last = await svc.finance.last_settlement("Umid")
    assert last["from"] == "2026-11-03" and last["to"] == "2026-11-12" and last["kind"] == "hammasi"


@pytest.mark.asyncio
async def test_settlement_history_batches_and_pdf(svc):
    from datetime import date
    from mmebel.services.settlement_report import as_pdf, settlement_report
    a = await _delivered(svc, "BF09", "2026-11-01")      # 200$
    b = await _delivered(svc, "BF07", "2026-11-19")      # 340$
    c = await _delivered(svc, "BF09", "2026-11-20")      # 200$ — alohida «To'landi» (oraliqsiz, eski usul)
    await svc.finance.settle_range(ADMIN, "Umid", date(2026, 11, 1), date(2026, 11, 19), confirm=True)
    await svc.finance.settle_order(ADMIN, "Umid", c)

    batches = await settlement_report(svc, "Umid")
    assert len(batches) == 2
    davr = next(x for x in batches if not x["legacy"])
    assert davr["from"] == "2026-11-01" and davr["to"] == "2026-11-19" and davr["count"] == 2
    assert sorted(davr["order_ids"]) == sorted([a, b]) and davr["price_total"] == 540
    assert davr["range_label"] == "01.11.2026 – 19.11.2026" and davr["by_name"] == str(ADMIN)
    eski = next(x for x in batches if x["legacy"])
    assert eski["kind"] == "eski" and eski["received"] is None and eski["order_ids"] == [c]
    assert eski["range_label"] == "noma'lum" and eski["price_total"] == 200
    # hech bir buyurtma ikki hisob-kitobda chiqmaydi
    assert not set(davr["order_ids"]) & set(eski["order_ids"])

    pdf = as_pdf("Umid", batches)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500
    assert as_pdf("Umid", []).startswith(b"%PDF")        # bo'sh tarix ham xatosiz
    pypdf = pytest.importorskip("pypdf")
    import io
    text = "".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(pdf)).pages)
    assert "01.11.2026" in text and "noma'lum" in text
