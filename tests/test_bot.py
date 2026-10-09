"""Bot oqimlarini Telegram'ga chiqmasdan sinash: soxta sessiya so'rovlarni yozib oladi."""
import datetime as dt
import itertools
from datetime import timedelta

import pytest
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, Update, User

from mmebel.server import assemble
from mmebel.store import MemoryStore
from mmebel.utils import now
from tests.test_web import ADMIN, DILLER, OMBOR, XODIM, settings

_ids = itertools.count(1)


class FakeSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(message_id=next(_ids), date=dt.datetime.now(), text=method.text,
                           chat=Chat(id=method.chat_id, type="private")).as_(bot)
        return True

    async def stream_content(self, *a, **kw):  # pragma: no cover
        yield b""

    async def close(self):
        pass


class Harness:
    def __init__(self):
        self.store = MemoryStore({
            "users": {str(OMBOR): {"role": "omborchi"}, str(XODIM): {"role": "xodim"},
                      str(DILLER): {"role": "diller", "client_name": "Umid"}},
            "mebellar": {"BF07": {"id": "BF07", "nomi": "BF 07", "narxi": 340, "soni": 5}},
            "meta": {"migrations": {"v1_settings": "x", "v1_roles": "x"}},
        })
        self.services, self.bot, self.dp, self.scheduler, self.events = assemble(settings(), self.store)
        self.session = FakeSession()
        self.bot.session = self.session

    def user(self, uid):
        return User(id=uid, is_bot=False, first_name=f"U{uid}")

    async def text(self, uid, text):
        self.session.calls.clear()
        msg = Message(message_id=next(_ids), date=dt.datetime.now(), text=text,
                      chat=Chat(id=uid, type="private"), from_user=self.user(uid))
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), message=msg))
        return self.replies()

    async def press(self, uid, data):
        self.session.calls.clear()
        msg = Message(message_id=next(_ids), date=dt.datetime.now(), text="x", chat=Chat(id=uid, type="private"))
        cb = CallbackQuery(id=str(next(_ids)), from_user=self.user(uid), chat_instance="ci", data=data, message=msg)
        await self.dp.feed_update(self.bot, Update(update_id=next(_ids), callback_query=cb))
        return self.replies()

    def replies(self):
        return [c for c in self.session.calls if isinstance(c, SendMessage)]

    def alerts(self):
        return [c.text for c in self.session.calls if isinstance(c, AnswerCallbackQuery) and c.text]

    def buttons(self, msg: SendMessage):
        rm = msg.reply_markup
        if rm is None:
            return []
        if hasattr(rm, "inline_keyboard"):
            return [(b.text, b.callback_data) for row in rm.inline_keyboard for b in row]
        return [b.text for row in rm.keyboard for b in row]


@pytest.fixture
def h():
    return Harness()


def due(days=2):
    return (now() + timedelta(days=days)).strftime("%d.%m.%Y")


async def test_start_shows_role_menu(h):
    r = await h.text(OMBOR, "/start")
    assert "Omborchi" in r[0].text and "🚚 Yetkazishlar nazorati" in h.buttons(r[0])
    r = await h.text(XODIM, "/start")
    assert h.buttons(r[0]) == ["🔨 Faol buyurtmalar", "🖥 Panel"]


async def test_role_isolation(h):
    r = await h.text(XODIM, "📝 Yangi buyurtma")  # admin funksiyasi
    assert "Tushunarsiz" in r[0].text
    assert await h.services.orders.all() == {}


async def test_diller_order_flow(h):
    await h.text(DILLER, "📝 Zakaz berish")
    r = await h.text(DILLER, "BF 07 ✅ 5 ta")
    assert "Nechta" in r[0].text
    r = await h.text(DILLER, "abc")
    assert "butun son" in r[0].text
    await h.text(DILLER, "2")
    r = await h.text(DILLER, "01.01.2020")
    assert "Sana noto'g'ri" in r[0].text
    r = await h.text(DILLER, due())
    assert "Zakaz qabul qilindi" in r[0].text
    staff_ids = {m.chat_id for m in r[1:]}
    assert {ADMIN, OMBOR, XODIM} <= staff_ids
    orders = await h.services.orders.all()
    o = next(iter(orders.values()))
    assert o["client_name"] == "Umid" and o["amount"] == 2 and o["deducted_qty"] == 2


async def test_menu_button_resets_state(h):
    """Eski xato: holat ichida menyu tugmasi bosilsa, u 'kiritilgan qiymat' sifatida qabul qilinardi."""
    await h.text(ADMIN, "📝 Yangi buyurtma")
    await h.text(ADMIN, "Umid")
    await h.text(ADMIN, "BF 07")  # endi soni kutilmoqda
    r = await h.text(ADMIN, "💰 Dillerlar qarzi")
    assert any("qarz" in m.text.lower() for m in r)
    assert await h.services.orders.all() == {}
    assert await h.dp.storage.get_state(_key(h, ADMIN)) is None


def _key(h, uid):
    from aiogram.fsm.storage.base import StorageKey
    return StorageKey(bot_id=h.bot.id, chat_id=uid, user_id=uid)


async def test_admin_order_and_delivery_flow(h):
    await h.text(ADMIN, "📝 Yangi buyurtma")
    await h.text(ADMIN, "Umid")
    await h.text(ADMIN, "BF 07")
    await h.text(ADMIN, "3")
    await h.text(ADMIN, due())
    r = await h.text(ADMIN, "⏩ O'tkazib yuborish")
    assert "Buyurtma qabul qilindi" in r[0].text
    oid = next(iter(await h.services.orders.all()))
    assert any(m.chat_id == DILLER for m in r)

    # omborchi: yetkazishlar nazorati -> buyurtma -> yetkazdik -> haydovchi -> narx
    r = await h.text(OMBOR, "🚚 Yetkazishlar nazorati")
    assert (f"dv:{oid}") in [d for _, d in h.buttons(r[-1])]
    await h.press(OMBOR, f"dv:{oid}")
    await h.press(OMBOR, f"dd:{oid}")
    await h.press(OMBOR, "ddr:0")
    r = await h.press(OMBOR, "ddp:3.5")
    assert "Biz yetkazib berdik" in r[0].text
    assert await h.services.finance.driver_balance("Dilmurod") == 3.5
    # ikkinchi marta bosish ikki marta yozmaydi
    await h.press(OMBOR, f"dd:{oid}")
    await h.press(OMBOR, "ddr:0")
    await h.press(OMBOR, "ddp:3.5")
    assert await h.services.finance.driver_balance("Dilmurod") == 3.5

    # admin: hisob-kitob -> qisman to'lov
    await h.text(ADMIN, "📊 Hisob kitoblar")
    r = await h.text(ADMIN, "Umid")
    assert "1 020$" in r[-1].text
    await h.press(ADMIN, f"asp:{oid}")
    r = await h.text(ADMIN, "20")
    assert "1 000$" in r[0].text


async def test_diller_cannot_cancel_foreign_order(h):
    o = await h.services.orders.create(ADMIN, client_name="Umid", product="BF07", amount=1, due_date=due())
    await h.press(DILLER, f"dcy:{o['order_id']}")
    assert any("o'zingiz" in a for a in h.alerts())
    assert (await h.services.orders.get(o["order_id"]))["status"] == "Tayyorlanmoqda"


async def test_payment_confirm_only_once(h):
    await h.text(DILLER, "📥 Kirim-Chiqim")
    r = await h.text(DILLER, "100")
    pay_btn = next(d for m in r if m.chat_id == ADMIN for _, d in h.buttons(m) if d.startswith("pay_confirm"))
    await h.press(ADMIN, pay_btn)
    await h.press(ADMIN, pay_btn)
    assert any("allaqachon" in a for a in h.alerts())
    hist = await h.services.finance.history("Umid")
    assert len(hist) == 1


async def test_markdown_chars_do_not_break(h):
    await h.services.orders.create(ADMIN, client_name="Umid", product="BF07", amount=1, due_date=due(),
                                   comment="rang_oq *maxsus* <b>")
    r = await h.text(XODIM, "🔨 Faol buyurtmalar")
    assert "rang_oq *maxsus* &lt;b&gt;" in r[0].text
