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
