"""Omborchi (va admin) funksiyalari: ombor, yetkazishlar, hisobotlar."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from ...constants import (
    ROLE_ADMIN,
    ROLE_OMBORCHI,
    SELF_PICKUP_DRIVER,
    ST_READY,
)
from ...services import ServiceError
from ...utils import (
    chunk_text,
    fmt_money,
    format_date,
    h,
    has_comment,
    last_months,
    parse_number,
    product_key,
    to_int,
)
from .. import keyboards as kb
from ..middlewares import Role
from ..texts import grouped_by_due, order_card, short_btn

router = Router(name="warehouse")
router.message.filter(Role(ROLE_ADMIN, ROLE_OMBORCHI))
router.callback_query.filter(Role(ROLE_ADMIN, ROLE_OMBORCHI))


class StockQty(StatesGroup):
    qty = State()


class NewProduct(StatesGroup):
    name = State()
    model = State()
    price = State()
    qty = State()
    image = State()


class Deliver(StatesGroup):
    custom_driver = State()
    custom_price = State()


class Report(StatesGroup):
    month = State()


# ================= OMBOR =================
@router.message(F.text == kb.B_STOCK_UPDATE)
async def stock_menu(message: Message):
    await message.answer("Nima qilmoqchisiz?\n\n📦 <b>Ombor sonini yangilash</b> — mavjud mebel sonini o'zgartirish\n"
                         "➕ <b>Yangi mebel</b> — omborga yangi mebel qo'shish",
                         reply_markup=kb.grid([kb.B_QTY_UPDATE, kb.B_NEW_PRODUCT], 1))


def _stock_items(products: dict) -> list[tuple[str, str]]:
    rows = sorted(products.items(), key=lambda kv: kv[1].get("nomi", kv[0]))
    return [(f"{p.get('nomi', pid)} — {to_int(p.get('soni'))} ta", f"sq:{pid}") for pid, p in rows]


@router.message(F.text == kb.B_QTY_UPDATE)
async def qty_start(message: Message, services):
    products = await services.inventory.all()
    if not products:
        await message.answer("Ombor bo'sh. Avval «➕ Yangi mebel» orqali qo'shing.")
        return
    await message.answer("📦 Qaysi mebelning sonini yangilaysiz?\n<i>Yoki mebel nomini yozib yuboring (masalan BF 07).</i>",
                         reply_markup=kb.paged(_stock_items(products), 0, "sq", per_page=10))


@router.callback_query(F.data.startswith("sq:p:"))
async def qty_page(cb: CallbackQuery, services):
    items = _stock_items(await services.inventory.all())
    await cb.message.edit_reply_markup(reply_markup=kb.paged(items, int(cb.data.split(":")[2]), "sq", per_page=10))
    await cb.answer()


async def _ask_qty(target: Message, state: FSMContext, pid: str, p: dict):
    await state.set_state(StockQty.qty)
    await state.update_data(pid=pid)
    await target.answer(f"🪑 <b>{h(p.get('nomi', pid))}</b> {h(p.get('modeli', ''))}\n"
                        f"📦 Hozirgi qoldiq: <b>{to_int(p.get('soni'))} ta</b>\n\nYangi sonini kiriting:",
                        reply_markup=kb.back_kb())


@router.callback_query(F.data.startswith("sq:"))
async def qty_pick(cb: CallbackQuery, state: FSMContext, services):
    pid = cb.data[3:]
    p = await services.inventory.get(pid)
    if not p:
        await cb.answer("Mebel topilmadi.", show_alert=True)
        return
    await cb.answer()
    await _ask_qty(cb.message, state, pid, p)


@router.message(StockQty.qty)
async def qty_set(message: Message, state: FSMContext, services, role):
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❌ 0 yoki undan katta butun son kiriting (masalan: 9).")
        return
    data = await state.get_data()
    try:
        qty = await services.inventory.set_quantity(message.from_user.id, data["pid"], int(text))
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    await message.answer(f"✅ Ombor yangilandi: <code>{h(data['pid'])}</code> — <b>{qty} ta</b>",
                         reply_markup=kb.main_menu(role))


@router.message(F.text == kb.B_NEW_PRODUCT)
async def np_start(message: Message, state: FSMContext, services):
    await state.set_state(NewProduct.name)
    await message.answer("Qaysi mebelni qo'shasiz? Ro'yxatdan tanlang yoki nomini yozing:",
                         reply_markup=kb.grid(await services.catalog.models(), 3))


@router.message(NewProduct.name)
async def np_name(message: Message, state: FSMContext, services):
    name = (message.text or "").strip()
    pid = product_key(name)
    if not pid or not pid.isalnum() or len(name) > 60:
        await message.answer("❌ Nom faqat harf, raqam, bo'sh joy va '-' dan iborat bo'lsin.")
        return
    existing = await services.inventory.get(pid)
    await state.update_data(name=name)
    note = f"\n<i>Bu mebel bazada bor ({to_int(existing.get('soni'))} ta) — ma'lumotlari yangilanadi.</i>" if existing else ""
    await state.set_state(NewProduct.model)
    await message.answer(f"Modeli/turi (masalan: Spalniy):{note}", reply_markup=kb.grid([kb.SKIP], 1))


@router.message(NewProduct.model)
async def np_model(message: Message, state: FSMContext, role):
    await state.update_data(model="" if message.text == kb.SKIP else (message.text or "")[:60])
    if role == ROLE_ADMIN:
        await state.set_state(NewProduct.price)
        await message.answer("Narxini kiriting ($, masalan: 340):", reply_markup=kb.grid([kb.SKIP], 1))
    else:
        await state.set_state(NewProduct.qty)
        await message.answer("Omborda nechta bor?", reply_markup=kb.back_kb())


@router.message(NewProduct.price)
async def np_price(message: Message, state: FSMContext):
    if message.text != kb.SKIP:
        p = parse_number(message.text)
        if p is None or p < 0:
            await message.answer("❌ Narxni raqam bilan kiriting (masalan: 340).")
            return
        await state.update_data(price=p)
    await state.set_state(NewProduct.qty)
    await message.answer("Omborda nechta bor?", reply_markup=kb.back_kb())


@router.message(NewProduct.qty)
async def np_qty(message: Message, state: FSMContext):
    if not (message.text or "").strip().isdigit():
        await message.answer("❌ Faqat butun son kiriting (masalan: 10).")
        return
    await state.update_data(qty=int(message.text.strip()))
    await state.set_state(NewProduct.image)
    await message.answer("📷 Rasm manzilini (https://...) yuboring yoki rasmsiz saqlang:",
                         reply_markup=kb.grid([kb.NO_IMAGE], 1))


@router.message(NewProduct.image)
async def np_save(message: Message, state: FSMContext, services, role):
    data = await state.get_data()
    image = "" if message.text == kb.NO_IMAGE else (message.text or "").strip()
    try:
        rec = await services.inventory.upsert(message.from_user.id, name=data["name"], model=data.get("model", ""),
                                              price=data.get("price"), quantity=data["qty"], image=image)
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    text = (f"✅ Mebel saqlandi!\n🆔 <code>{rec['id']}</code>\n🪑 {h(rec['nomi'])} {h(rec.get('modeli', ''))}\n"
            f"📦 Soni: {rec['soni']} ta")
    if role == ROLE_ADMIN and rec.get("narxi") is not None:
        text += f"\n💰 Narxi: {fmt_money(rec['narxi'])}"
    if rec.get("rasm"):
        try:
            await message.answer_photo(rec["rasm"], caption=text, reply_markup=kb.main_menu(role))
            return
        except Exception:  # noqa: BLE001
            pass
    await message.answer(text, reply_markup=kb.main_menu(role))


# ================= YETKAZISH NAZORATI =================
def _delivery_items(rows) -> list[tuple[str, str]]:
    return [(short_btn(oid, o), f"dv:{oid}") for oid, o in rows]


@router.message(F.text == kb.B_DELIVERY_CTRL)
async def dc_start(message: Message, services):
    rows = await services.orders.active()
    if not rows:
        await message.answer("✅ Faol buyurtmalar yo'q.")
        return
    for chunk in chunk_text(f"🚚 <b>Faol buyurtmalar ({len(rows)} ta):</b>\n\n" + grouped_by_due(rows)):
        await message.answer(chunk)
    await message.answer("Qaysi buyurtma holatini o'zgartirasiz?", reply_markup=kb.paged(_delivery_items(rows), 0, "dv"))


@router.callback_query(F.data.startswith("dv:p:"))
async def dc_page(cb: CallbackQuery, services):
    rows = await services.orders.active()
    await cb.message.edit_reply_markup(reply_markup=kb.paged(_delivery_items(rows), int(cb.data.split(":")[2]), "dv"))
    await cb.answer()


def _order_actions(oid: str, o: dict) -> list[list[tuple[str, str]]]:
    rows = []
    if o.get("status") != ST_READY:
        rows.append([("✅ Tayyor bo'ldi", f"dr:{oid}")])
    rows.append([("🚚 Biz yetkazib berdik", f"dd:{oid}"), ("🏠 O'zi olib ketdi", f"dp:{oid}")])
    rows.append([("❌ Bekor qilish", f"dx:{oid}"), ("🔙 Yopish", "close")])
    return rows


@router.callback_query(F.data.startswith("dv:"))
async def dc_pick(cb: CallbackQuery, services, role):
    oid = cb.data[3:]
    try:
        o = await services.orders.get(oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.answer(order_card(oid, o, show_price=role == ROLE_ADMIN) + "\n\nYangi holatni tanlang:",
                            reply_markup=kb.inline(_order_actions(oid, o)))
    await cb.answer()


@router.callback_query(F.data.startswith("dr:"))
async def dc_ready(cb: CallbackQuery, services, events):
    oid = cb.data[3:]
    try:
        o = await services.orders.set_ready(cb.from_user.id, oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.edit_text(order_card(oid, o) + "\n\n✅ <b>Tayyor bo'ldi deb belgilandi.</b>")
    await cb.answer("Saqlandi")
    await events.order_ready(oid, o, cb.from_user.id)


@router.callback_query(F.data.startswith("dx:"))
async def dc_cancel_ask(cb: CallbackQuery):
    oid = cb.data[3:]
    await cb.message.edit_reply_markup(reply_markup=kb.inline([[("⚠️ Ha, bekor qilinsin", f"dxy:{oid}"),
                                                                ("🔙 Yo'q", "close")]]))
    await cb.answer()


@router.callback_query(F.data.startswith("dxy:"))
async def dc_cancel(cb: CallbackQuery, services, events):
    oid = cb.data[4:]
    try:
        o = await services.orders.cancel(cb.from_user.id, oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.edit_text(order_card(oid, o) + f"\n\n❌ <b>Bekor qilindi.</b> Omborga qaytdi: {o['returned_qty']} ta")
    await cb.answer()
    await events.order_cancelled(oid, o, cb.from_user.id)


# --- yetkazib berish: haydovchi -> narx ---
@router.callback_query(F.data.startswith("dd:"))
async def dd_driver(cb: CallbackQuery, state: FSMContext, services):
    oid = cb.data[3:]
    drivers = await services.catalog.drivers()
    await state.update_data(dlv_order=oid, dlv_drivers=drivers)
    rows = [[(d, f"ddr:{i}")] for i, d in enumerate(drivers)] + [[("✍️ Boshqa", "ddr:other"), ("🔙 Yopish", "close")]]
    await cb.message.edit_reply_markup(reply_markup=kb.inline(rows))
    await cb.answer("Haydovchini tanlang")


@router.callback_query(F.data.startswith("ddr:"))
async def dd_driver_pick(cb: CallbackQuery, state: FSMContext, services):
    data = await state.get_data()
    val = cb.data[4:]
    if val == "other":
        await state.set_state(Deliver.custom_driver)
        await cb.message.answer("Haydovchi ismini yozing:", reply_markup=kb.back_kb())
        await cb.answer()
        return
    try:
        driver = data.get("dlv_drivers", [])[int(val)]
    except (ValueError, IndexError):
        await cb.answer("Eskirgan tugma, qaytadan oching.", show_alert=True)
        return
    await state.update_data(dlv_driver=driver)
    await _ask_price(cb.message, services, edit=True)
    await cb.answer()


async def _ask_price(msg: Message, services, *, edit: bool, pickup: bool = False):
    s = await services.catalog.settings()
    presets = s["pickup_discounts"] if pickup else s["delivery_prices"]
    row = [(f"{p:g}$" if p else "0", f"ddp:{p:g}") for p in presets]
    markup = kb.inline([row, [("✍️ Boshqa summa", "ddp:other"), ("🔙 Yopish", "close")]])
    text = "Chegirma summasini tanlang ($):" if pickup else "Yetkazib berish narxini tanlang ($):"
    if edit:
        await msg.edit_reply_markup(reply_markup=markup)
    else:
        await msg.answer(text, reply_markup=markup)


@router.message(Deliver.custom_driver)
async def dd_custom_driver(message: Message, state: FSMContext, services):
    name = (message.text or "").strip()[:40]
    if not name or any(c in name for c in ".$#[]/"):
        await message.answer("❌ Ism noto'g'ri (. $ # [ ] / belgilarisiz yozing).")
        return
    await state.update_data(dlv_driver=name)
    await state.set_state(None)
    await message.answer(f"🚚 Haydovchi: {h(name)}", reply_markup=ReplyKeyboardRemove())
    await _ask_price(message, services, edit=False)


@router.callback_query(F.data.startswith("dp:"))
async def dp_pickup(cb: CallbackQuery, state: FSMContext, services):
    await state.update_data(dlv_order=cb.data[3:], dlv_driver=SELF_PICKUP_DRIVER)
    await _ask_price(cb.message, services, edit=True, pickup=True)
    await cb.answer("Chegirmani tanlang")


@router.callback_query(F.data.startswith("ddp:"))
async def dd_price_pick(cb: CallbackQuery, state: FSMContext, services, events, role):
    val = cb.data[4:]
    if val == "other":
        await state.set_state(Deliver.custom_price)
        await cb.message.answer("Summani kiriting ($, masalan 7.5):", reply_markup=kb.back_kb())
        await cb.answer()
        return
    await cb.answer()
    await _finish_delivery(cb.message, cb.from_user.id, state, services, events, role, val)


@router.message(Deliver.custom_price)
async def dd_custom_price(message: Message, state: FSMContext, services, events, role):
    p = parse_number(message.text)
    if p is None or p < 0:
        await message.answer("❌ Summani raqam bilan kiriting (masalan: 7.5).")
        return
    await _finish_delivery(message, message.from_user.id, state, services, events, role, p)


async def _finish_delivery(msg: Message, actor_id: int, state: FSMContext, services, events, role, price):
    data = await state.get_data()
    oid, driver = data.get("dlv_order"), data.get("dlv_driver")
    if not oid or not driver:
        await msg.answer("Jarayon eskirgan. «🚚 Yetkazishlar nazorati» dan qaytadan boshlang.")
        return
    try:
        o = await services.orders.deliver(actor_id, oid, driver=driver, price=price)
    except ServiceError as e:
        await msg.answer(f"❌ {h(e)}")
        return
    await state.clear()
    pickup = driver == SELF_PICKUP_DRIVER
    extra = (f"💸 Chegirma: {h(o['delivery_price'])} → hisoblangan: {fmt_money(o['net'])}" if pickup
             else f"💵 Dostavka: {h(o['delivery_price'])}")
    await msg.answer(f"✅ Holat yangilandi: <b>{h(o['status'])}</b>\n🆔 <code>{h(oid)}</code>\n🚚 {h(driver)}\n{extra}",
                     reply_markup=kb.main_menu(role))
    await events.order_delivered(oid, o, actor_id)


# ================= HISOBOTLAR =================
@router.message(F.text.in_({kb.B_DELIVERY_REPORT, kb.B_HISTORY}))
async def report_start(message: Message, state: FSMContext):
    await state.set_state(Report.month)
    await state.update_data(kind="report" if message.text == kb.B_DELIVERY_REPORT else "history")
    await message.answer("Qaysi oy?", reply_markup=kb.grid(last_months(6), 2))


@router.message(Report.month)
async def report_show(message: Message, state: FSMContext, services, role):
    month = (message.text or "").strip()
    if month not in last_months(24):
        await message.answer("Iltimos, tugmadan oy tanlang.")
        return
    kind = (await state.get_data()).get("kind")
    await state.clear()
    rows = await services.reports.deliveries(month)
    if not rows:
        await message.answer(f"{month} oyida yetkazib berishlar topilmadi.", reply_markup=kb.main_menu(role))
        return
    lines = [f"{'📊' if kind == 'report' else '🕰'} <b>{month} — yetkazib berishlar ({len(rows)} ta)</b>\n"]
    for r in rows:
        lines.append(f"📅 {format_date(r.get('timestamp'))} · 🧑 {h(r.get('client'))}\n"
                     f"📦 {h(r.get('product_id'))} ({h(r.get('amount', 1))} ta) · 🚚 {h(r.get('driver'))} ({h(r.get('price'))})")
        if kind == "report":
            lines.append(f"🆔 <code>{h(r.get('order_id'))}</code> · buyurtma: {format_date(r.get('order_created'))}")
        if has_comment(r.get("comment")):
            lines.append(f"📝 {h(r.get('comment'))}")
        lines.append("")
    t = services.reports.delivery_totals(rows)
    lines.append(f"📈 <b>JAMI:</b> {t['total']['count']} ta yetkazish · {t['total']['items']} ta mebel · "
                 f"{fmt_money(t['total']['sum'])}")
    for d in t["drivers"]:
        lines.append(f"  🚚 {h(d['driver'])}: {d['count']} ta · {fmt_money(d['sum'])}")
    for chunk in chunk_text("\n".join(lines)):
        await message.answer(chunk)
    await message.answer("Tayyor.", reply_markup=kb.main_menu(role))
