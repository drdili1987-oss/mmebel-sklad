"""Admin funksiyalari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ...constants import ROLE_ADMIN, ST_READY
from ...services import ServiceError
from ...utils import (
    chunk_text,
    fmt_money,
    format_date,
    h,
    has_comment,
    is_valid_key,
    month_key,
    normalize_due_date,
    parse_number,
    parse_positive_int,
    product_key,
)
from .. import keyboards as kb
from ..middlewares import Role
from ..texts import grouped_by_due, order_card, short_btn

router = Router(name="admin")
router.message.filter(Role(ROLE_ADMIN))
router.callback_query.filter(Role(ROLE_ADMIN))

from ...events import FIELD_LABELS


class AOrder(StatesGroup):
    client = State()
    custom_client = State()
    product = State()
    custom_product = State()
    price = State()
    amount = State()
    due = State()
    comment = State()


class AEdit(StatesGroup):
    value = State()


class AAcc(StatesGroup):
    client = State()
    partial = State()


class ADriver(StatesGroup):
    amount = State()


# ================= YANGI BUYURTMA =================
@router.message(F.text == kb.B_NEW_ORDER)
async def no_start(message: Message, state: FSMContext, services):
    await state.set_state(AOrder.client)
    await message.answer("Dillerni tanlang yoki «Boshqa» ni bosing:",
                         reply_markup=kb.grid(await services.catalog.clients(), 2, extra=[kb.OTHER_CLIENT]))


@router.message(AOrder.client)
async def no_client(message: Message, state: FSMContext, services):
    if message.text == kb.OTHER_CLIENT:
        await state.set_state(AOrder.custom_client)
        await message.answer("Yangi diller nomini kiriting:", reply_markup=kb.back_kb())
        return
    if message.text not in await services.catalog.clients():
        await message.answer("Ro'yxatdan tanlang yoki «Boshqa» ni bosing.")
        return
    await _ask_product(message, state, services, message.text)


@router.message(AOrder.custom_client)
async def no_custom_client(message: Message, state: FSMContext, services):
    name = (message.text or "").strip()
    if not is_valid_key(name) or len(name) > 60:
        await message.answer("❌ Nom bo'sh bo'lmasin va . $ # [ ] / belgilarisiz bo'lsin.")
        return
    await services.catalog.add_client_if_missing(name)
    await _ask_product(message, state, services, name)


async def _ask_product(message: Message, state: FSMContext, services, client: str):
    await state.update_data(client=client)
    await state.set_state(AOrder.product)
    await message.answer(f"🧑 {h(client)}\nQaysi mebel? Tanlang yoki yozing:",
                         reply_markup=kb.grid(await services.catalog.models(), 3, extra=[kb.OTHER_MODEL]))


@router.message(AOrder.product)
async def no_product(message: Message, state: FSMContext, services):
    if message.text == kb.OTHER_MODEL:
        await state.set_state(AOrder.custom_product)
        await message.answer("Mebel nomini kiriting:", reply_markup=kb.back_kb())
        return
    await _set_product(message, state, services, message.text or "")


@router.message(AOrder.custom_product)
async def no_custom_product(message: Message, state: FSMContext, services):
    await _set_product(message, state, services, message.text or "", force_price=True)


async def _set_product(message: Message, state: FSMContext, services, name: str, force_price: bool = False):
    name = (name or "").strip()[:60]
    pid = product_key(name)
    if not pid or not any(c.isalnum() for c in pid):
        await message.answer("❌ Mebel nomini kiriting (masalan: Shkaf 4 eshik, oq rang).")
        return
    p = await services.inventory.get(pid)
    price = services.inventory.unit_price(p)
    await state.update_data(product=name.strip(), custom_price=None)
    if force_price or not price:
        await state.set_state(AOrder.price)
        await message.answer("Bu mebelning narxi bazada yo'q. 1 dona narxini kiriting ($):", reply_markup=kb.back_kb())
        return
    stock = int(parse_number(p.get("soni"), 0) or 0)
    await state.set_state(AOrder.amount)
    await message.answer(f"📦 {h(name)} — narxi {fmt_money(price)}, omborda {stock} ta.\nNechta?",
                         reply_markup=kb.back_kb())


@router.message(AOrder.price)
async def no_price(message: Message, state: FSMContext):
    p = parse_number(message.text)
    if p is None or p < 0:
        await message.answer("❌ Narxni raqam bilan kiriting (masalan: 340).")
        return
    await state.update_data(custom_price=p)
    await state.set_state(AOrder.amount)
    await message.answer("Nechta?", reply_markup=kb.back_kb())


@router.message(AOrder.amount)
async def no_amount(message: Message, state: FSMContext):
    qty = parse_positive_int(message.text, max_value=10_000)
    if not qty:
        await message.answer("❌ Butun musbat son kiriting (masalan: 2).")
        return
    await state.update_data(amount=qty)
    await state.set_state(AOrder.due)
    await message.answer("📅 Qaysi sanaga tayyor bo'lishi kerak? (KK.OO.YYYY)", reply_markup=kb.dates_kb())


@router.message(AOrder.due)
async def no_due(message: Message, state: FSMContext):
    due = normalize_due_date(message.text or "")
    if not due:
        await message.answer("❌ Sana noto'g'ri yoki o'tib ketgan. Format: KK.OO.YYYY")
        return
    await state.update_data(due=due)
    await state.set_state(AOrder.comment)
    await message.answer("📝 Izoh (o'zgartirish kerak bo'lsa yozing):", reply_markup=kb.grid([kb.SKIP], 1))


@router.message(AOrder.comment)
async def no_finish(message: Message, state: FSMContext, services, events):
    data = await state.get_data()
    comment = "" if message.text == kb.SKIP else (message.text or "")
    try:
        o = await services.orders.create(message.from_user.id, client_name=data["client"], product=data["product"],
                                         amount=data["amount"], due_date=data["due"], comment=comment,
                                         source="admin", custom_price=data.get("custom_price"))
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    await message.answer(order_card(o["order_id"], o, show_price=True, title="✅ Buyurtma qabul qilindi!") +
                         f"\n📦 Ombordan ayirildi: {o['deducted_qty']} ta", reply_markup=kb.main_menu(ROLE_ADMIN))
    await events.order_created(o, message.from_user.id)


# ================= BUYURTMALAR NAZORATI =================
@router.message(F.text == kb.B_ORDER_CTRL)
async def oc_start(message: Message, services):
    rows = await services.orders.active()
    if not rows:
        await message.answer("Faol buyurtmalar yo'q.")
        return
    for chunk in chunk_text(f"📋 <b>Faol buyurtmalar ({len(rows)} ta):</b>\n\n" + grouped_by_due(rows)):
        await message.answer(chunk)
    await message.answer("Qaysi buyurtmani boshqarasiz?",
                         reply_markup=kb.paged([(short_btn(k, v), f"ac:{k}") for k, v in rows], 0, "ac"))


@router.callback_query(F.data.startswith("ac:p:"))
async def oc_page(cb: CallbackQuery, services):
    rows = await services.orders.active()
    await cb.message.edit_reply_markup(reply_markup=kb.paged([(short_btn(k, v), f"ac:{k}") for k, v in rows],
                                                             int(cb.data.split(":")[2]), "ac"))
    await cb.answer()


@router.callback_query(F.data.startswith("ac:"))
async def oc_pick(cb: CallbackQuery, services):
    oid = cb.data[3:]
    try:
        o = await services.orders.get(oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    created = f"\n📆 Yaratilgan: {format_date(o.get('created_at'))}" if o.get("created_at") else ""
    await cb.message.answer(order_card(oid, o, show_price=True) + created + "\n\nNima qilasiz?", reply_markup=kb.inline([
        [("📊 Soni", f"ae:amount:{oid}"), ("📅 Muddat", f"ae:due_date:{oid}"), ("📝 Izoh", f"ae:comment:{oid}")],
        [("❌ Bekor qilish", f"dx:{oid}"), ("🔙 Yopish", "close")],
    ]))
    await cb.answer()


@router.callback_query(F.data.startswith("ae:"))
async def oc_edit(cb: CallbackQuery, state: FSMContext):
    _, field, oid = cb.data.split(":", 2)
    await state.set_state(AEdit.value)
    await state.update_data(edit_order=oid, edit_field=field)
    prompts = {"amount": ("Yangi sonni kiriting:", kb.back_kb()),
               "due_date": ("Yangi muddatni tanlang yoki yozing:", kb.dates_kb()),
               "comment": ("Yangi izohni kiriting:", kb.back_kb())}
    text, markup = prompts[field]
    await cb.message.answer(text, reply_markup=markup)
    await cb.answer()


@router.message(AEdit.value)
async def oc_edit_value(message: Message, state: FSMContext, services, events):
    data = await state.get_data()
    oid, field = data["edit_order"], data["edit_field"]
    try:
        o = await services.orders.edit(message.from_user.id, oid, **{field: message.text or ""})
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    if not o["_changes"]:
        await message.answer("O'zgarish yo'q.", reply_markup=kb.main_menu(ROLE_ADMIN))
        return
    new_val = o["_changes"][field]
    await message.answer(f"✅ <code>{h(oid)}</code> — {FIELD_LABELS[field]}: <b>{h(new_val)}</b>",
                         reply_markup=kb.main_menu(ROLE_ADMIN))
    await events.order_edited(oid, o, message.from_user.id)


# ================= QARZLAR VA HISOB-KITOB =================
@router.message(F.text == kb.B_DEBTS)
async def debts(message: Message, services):
    wait = await message.answer("⏳ Hisoblanmoqda...")
    rows = [r for r in await services.finance.all_debts() if r["debt"] != 0]
    await wait.delete()
    if not rows:
        await message.answer("✅ Hech bir dillerda qarz yo'q!")
        return
    lines = [f"💰 <b>Dillerlar qarzi ({len(rows)} ta)</b>\n"]
    for i, r in enumerate(rows, 1):
        mark = "" if r["debt"] > 0 else " <i>(ortiqcha to'lov)</i>"
        lines.append(f"{i}. 🧑 <b>{h(r['client'])}</b> — <code>{fmt_money(r['debt'])}</code>{mark}")
    lines.append(f"\n📊 <b>Jami qarz: {fmt_money(sum(r['debt'] for r in rows if r['debt'] > 0))}</b>")
    await message.answer("\n".join(lines))


@router.message(F.text == kb.B_ACCOUNTS)
async def acc_start(message: Message, state: FSMContext, services):
    await state.set_state(AAcc.client)
    await message.answer("Qaysi dillerning hisobini ochasiz?", reply_markup=kb.grid(await services.catalog.clients(), 2))


@router.message(AAcc.client)
async def acc_client(message: Message, state: FSMContext, services):
    client = (message.text or "").strip()
    if not is_valid_key(client):
        await message.answer("Ro'yxatdan tanlang.")
        return
    await state.update_data(acc_client=client)
    await state.set_state(None)
    await _show_account(message, services, client)


async def _show_account(message: Message, services, client: str, edit: bool = False):
    acc = await services.finance.account(client)
    lines = [f"🧑 <b>{h(client)}</b> — hisob-kitob", f"💳 Joriy qarz: <b>{fmt_money(acc.debt)}</b>"]
    if acc.partial_total:
        lines.append(f"<i>(shundan qisman to'lovlar: −{fmt_money(acc.partial_total)})</i>")
    if acc.pending:
        lines.append(f"\n⏳ <b>Tayyorlanmoqda (qarzga kirmagan) — {len(acc.pending)} ta:</b>")
        for r in acc.pending[:20]:
            lines.append(f"  {'✅' if r['status'] == ST_READY else '🔧'} {h(r['product_id'])} — "
                         f"{r['amount']} ta · {fmt_money(r['gross'])} · 📅 {format_date(r['due_date'])}")
    if acc.unsettled:
        lines.append(f"\n📦 <b>Olib ketilgan, to'lanmagan — {len(acc.unsettled)} ta.</b> Tanlang:")
    else:
        lines.append("\n✅ Hisob-kitob qilinadigan buyurtma yo'q.")
    buttons = [[(f"🚛 {r['product_id']} ×{r['amount']} · {fmt_money(r['net'])} · {format_date(r['delivered_at'])[:5]}",
                 f"as:{r['order_id']}")] for r in acc.unsettled[:25]]
    if len(acc.unsettled) > 25:
        lines.append("<i>Faqat oxirgi 25 tasi ko'rsatildi. To'liq ro'yxat — panelda.</i>")
    general = [("💵 To'lov qabul qilish", "asg"), ("📜 Tarix", "ash")]
    if acc.unsettled:
        buttons.append([("💳 Barchasini hisob-kitob qilish", "asa")])
    buttons.append(general)
    text = "\n".join(lines)
    markup = kb.inline(buttons)
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        for chunk in chunk_text(text)[:-1]:
            await message.answer(chunk)
        await message.answer(chunk_text(text)[-1], reply_markup=markup)


async def _client(state: FSMContext, cb: CallbackQuery) -> str | None:
    client = (await state.get_data()).get("acc_client")
    if not client:
        await cb.answer("Sessiya eskirgan, «📊 Hisob kitoblar» dan qaytadan oching.", show_alert=True)
    return client


@router.callback_query(F.data.startswith("as:"))
async def acc_order(cb: CallbackQuery, state: FSMContext, services):
    client = await _client(state, cb)
    if not client:
        return
    oid = cb.data[3:]
    acc = await services.finance.account(client, save=False)
    r = next((x for x in acc.unsettled if x["order_id"] == oid), None)
    if not r:
        await cb.answer("Bu buyurtma allaqachon yopilgan.", show_alert=True)
        return
    lines = [f"🚛 <b>{h(r['product_id'])}</b> — {r['amount']} ta", f"📅 Yetkazilgan: {format_date(r['delivered_at'])}",
             f"💰 Narxi: {fmt_money(r['gross'])}"]
    if r["discount"]:
        lines.append(f"💸 Chegirma (o'zi olib ketdi): −{fmt_money(r['discount'])}")
    if r["paid_partial"]:
        lines.append(f"💵 Qisman to'langan: −{fmt_money(r['paid_partial'])}")
    lines.append(f"✅ To'lanishi kerak: <b>{fmt_money(r['net'] - r['paid_partial'])}</b>")
    if has_comment(r["comment"]):
        lines.append(f"📝 {h(r['comment'])}")
    await cb.message.answer("\n".join(lines), reply_markup=kb.inline([
        [("✅ To'liq hisob-kitob qilindi", f"aso:{oid}")], [("💰 Qisman to'ladi", f"asp:{oid}")], [("🔙 Yopish", "close")]]))
    await cb.answer()


@router.callback_query(F.data.startswith("aso:"))
async def acc_settle(cb: CallbackQuery, state: FSMContext, services):
    client = await _client(state, cb)
    if not client:
        return
    try:
        res = await services.finance.settle_order(cb.from_user.id, client, cb.data[4:])
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.edit_text(f"✅ Hisob-kitob qilindi: <code>{h(res['order_id'])}</code>\n"
                               f"💵 Qabul qilindi: {fmt_money(res['received'])}\n💳 Yangi qarz: <b>{fmt_money(res['debt'])}</b>")
    await cb.answer("Saqlandi")
    await _show_account(cb.message, services, client)


@router.callback_query(F.data.startswith("asp:") | (F.data == "asg"))
async def acc_partial_ask(cb: CallbackQuery, state: FSMContext):
    if not await _client(state, cb):
        return
    oid = cb.data[4:] if cb.data.startswith("asp:") else ""
    await state.set_state(AAcc.partial)
    await state.update_data(partial_order=oid)
    await cb.message.answer("💰 Qancha to'ladi? ($, raqam):", reply_markup=kb.back_kb())
    await cb.answer()


@router.message(AAcc.partial)
async def acc_partial(message: Message, state: FSMContext, services):
    data = await state.get_data()
    client = data.get("acc_client")
    try:
        debt = await services.finance.partial_payment(message.from_user.id, client, message.text,
                                                      order_id=data.get("partial_order") or None)
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.set_state(None)
    await message.answer(f"✅ To'lov qabul qilindi: {fmt_money(parse_number(message.text))}\n"
                         f"💳 Yangi qarz: <b>{fmt_money(debt)}</b>", reply_markup=kb.main_menu(ROLE_ADMIN))
    await _show_account(message, services, client)


@router.callback_query(F.data == "asa")
async def acc_all_ask(cb: CallbackQuery, state: FSMContext, services):
    client = await _client(state, cb)
    if not client:
        return
    acc = await services.finance.account(client, save=False)
    await cb.message.answer(
        f"⚠️ <b>Diqqat!</b>\n🧑 {h(client)}\n📦 Buyurtmalar: <b>{len(acc.unsettled)} ta</b>\n"
        f"💳 Qarz: <b>{fmt_money(acc.debt)}</b>\n\nBarchasi to'landi deb belgilanadi. Davom etasizmi?",
        reply_markup=kb.inline([[("✅ Ha, barchasi to'landi", "asay"), ("❌ Yo'q", "close")]]))
    await cb.answer()


@router.callback_query(F.data == "asay")
async def acc_all(cb: CallbackQuery, state: FSMContext, services):
    client = await _client(state, cb)
    if not client:
        return
    res = await services.finance.settle_all(cb.from_user.id, client)
    await cb.message.edit_text(f"✅ <b>{h(client)}</b> — {res['settled']} ta buyurtma hisob-kitob qilindi.\n"
                               f"💵 Qabul qilindi: {fmt_money(res['received'])}\n💳 Qarz: <b>{fmt_money(res['debt'])}</b>")
    await cb.answer()


@router.callback_query(F.data == "ash")
async def acc_history(cb: CallbackQuery, state: FSMContext, services):
    client = await _client(state, cb)
    if not client:
        return
    rows = await services.finance.history(client)
    if not rows:
        await cb.answer("Tarix bo'sh.", show_alert=True)
        return
    lines = [f"📜 <b>{h(client)} — hisob-kitob tarixi</b>\n"]
    for r in rows[:60]:
        if r.get("accounting_type") == "toliq":
            lines.append(f"✅ {format_date(r.get('accounting_date'))} · <b>{h(r.get('product_id'))}</b> ×{h(r.get('amount'))}"
                         f" · {fmt_money(r.get('total_price') or 0)}")
        else:
            settled = " <i>(yopilgan)</i>" if r.get("settled") else ""
            lines.append(f"💰 {format_date(r.get('accounting_date'))} · qisman <b>{fmt_money(r.get('partial_payment'))}</b>"
                         f"{' · ' + h(r.get('product_id')) if r.get('product_id') else ''}{settled}")
    for chunk in chunk_text("\n".join(lines)):
        await cb.message.answer(chunk)
    await cb.answer()


# ================= TO'LOVLARNI TASDIQLASH =================
@router.callback_query(F.data.startswith("pay_confirm:") | F.data.startswith("pay_reject:"))
async def pay_resolve(cb: CallbackQuery, services, events):
    action, pay_id = cb.data.split(":", 1)
    approve = action == "pay_confirm"
    try:
        pay, debt = await services.finance.resolve_payment(cb.from_user.id, pay_id, approve)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        await cb.message.edit_reply_markup(reply_markup=None)
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    if approve:
        await cb.message.answer(f"✅ To'lov tasdiqlandi: {h(pay['client_name'])} — {fmt_money(pay['amount'])}\n"
                                f"💳 Yangi qarz: <b>{fmt_money(debt)}</b>")
    else:
        await cb.message.answer(f"❌ To'lov rad etildi: {h(pay['client_name'])} — {fmt_money(pay['amount'])}")
    await cb.answer()
    await events.payment_resolved(pay, approve, debt, cb.from_user.id)


# ================= HAYDOVCHILAR =================
@router.message(F.text == kb.B_DRIVERS)
async def drivers(message: Message, state: FSMContext, services):
    month = month_key()
    t = services.reports.delivery_totals(await services.reports.deliveries(month))
    balances = await services.finance.driver_balances()
    names = [b["driver"] for b in balances]
    await state.update_data(drivers=names)
    lines = [f"🚚 <b>Haydovchilar — {month}</b>\n"]
    stat = {d["driver"]: d for d in t["drivers"]}
    for b in balances:
        s = stat.get(b["driver"], {"count": 0, "sum": 0})
        lines.append(f"👨‍✈️ <b>{h(b['driver'])}</b>: {s['count']} ta yetkazish · {fmt_money(s['sum'])} · "
                     f"balans <b>{fmt_money(b['balance'])}</b>")
    self_pickup = stat.get("O'zi olib ketdi")
    if self_pickup:
        lines.append(f"🏠 O'zi olib ketgan: {self_pickup['count']} ta")
    rows = [[(f"👨‍✈️ {n}", f"drv:{i}")] for i, n in enumerate(names)]
    await message.answer("\n".join(lines), reply_markup=kb.inline(rows))


async def _driver(state: FSMContext, cb: CallbackQuery, idx: str) -> str | None:
    names = (await state.get_data()).get("drivers", [])
    try:
        return names[int(idx)]
    except (ValueError, IndexError):
        await cb.answer("Eskirgan tugma. «🚚 Haydovchilar hisoboti» ni qayta oching.", show_alert=True)
        return None


@router.callback_query(F.data.startswith("drv:"))
async def driver_card(cb: CallbackQuery, state: FSMContext, services):
    idx = cb.data[4:]
    name = await _driver(state, cb, idx)
    if not name:
        return
    bal = await services.finance.driver_balance(name)
    await cb.message.answer(
        f"👨‍✈️ <b>{h(name)}</b>\n💳 Balans: <b>{fmt_money(bal)}</b>\n"
        "<i>(musbat — biz haydovchiga qarzdormiz; yetkazish haqi avtomatik qo'shiladi)</i>",
        reply_markup=kb.inline([
            [("➕ Pul berildi (chiqim)", f"drg:{idx}"), ("➖ Pul qaytardi (kirim)", f"drc:{idx}")],
            [("📜 Moliya tarixi", f"drh:{idx}"), ("📊 Yetkazishlar", f"drd:{idx}")],
        ]))
    await cb.answer()


@router.callback_query(F.data.startswith("drg:") | F.data.startswith("drc:"))
async def driver_pay_ask(cb: CallbackQuery, state: FSMContext):
    name = await _driver(state, cb, cb.data[4:])
    if not name:
        return
    direction = "give" if cb.data.startswith("drg:") else "receive"
    await state.set_state(ADriver.amount)
    await state.update_data(drv_name=name, drv_dir=direction)
    await cb.message.answer(f"👨‍✈️ {h(name)} — summani kiriting ($):", reply_markup=kb.back_kb())
    await cb.answer()


@router.message(ADriver.amount)
async def driver_pay(message: Message, state: FSMContext, services):
    data = await state.get_data()
    try:
        bal = await services.finance.driver_payment(message.from_user.id, data["drv_name"], message.text, data["drv_dir"])
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.set_state(None)
    await message.answer(f"✅ Saqlandi. {h(data['drv_name'])} balansi: <b>{fmt_money(bal)}</b>",
                         reply_markup=kb.main_menu(ROLE_ADMIN))


@router.callback_query(F.data.startswith("drh:"))
async def driver_hist(cb: CallbackQuery, state: FSMContext, services):
    name = await _driver(state, cb, cb.data[4:])
    if not name:
        return
    rows = await services.finance.driver_history(name)
    if not rows:
        await cb.answer("Tarix bo'sh.", show_alert=True)
        return
    lines = [f"📜 <b>{h(name)} — moliya tarixi</b>\n"]
    for r in rows[:80]:
        lines.append(f"{'🔴' if r.get('type') == 'Chiqim' else '🟢'} {format_date(r.get('timestamp'))} · "
                     f"{h(r.get('type'))}: <b>{fmt_money(r.get('amount'))}</b> · {h(r.get('note', ''))}")
    for chunk in chunk_text("\n".join(lines)):
        await cb.message.answer(chunk)
    await cb.answer()


@router.callback_query(F.data.startswith("drd:"))
async def driver_deliveries(cb: CallbackQuery, state: FSMContext, services):
    name = await _driver(state, cb, cb.data[4:])
    if not name:
        return
    data = await services.reports.driver_deliveries(name)
    if not data:
        await cb.answer("Yetkazishlar topilmadi.", show_alert=True)
        return
    lines = [f"📊 <b>{h(name)} — yetkazishlar</b>\n"]
    for month, items in data.items():
        lines.append(f"📅 <b>{month}</b> — {len(items)} ta")
        for d in items:
            lines.append(f"  ▪️ {format_date(d.get('timestamp'))} · {h(d.get('client'))}: {h(d.get('product_id'))} ({h(d.get('price'))})")
        lines.append("")
    for chunk in chunk_text("\n".join(lines)):
        await cb.message.answer(chunk)
    await cb.answer()


# ================= STATISTIKA =================
@router.message(F.text == kb.B_SALES)
async def sales(message: Message, services):
    data = await services.reports.sales(6)
    if not data:
        await message.answer("Sotuvlar tarixi bo'sh.")
        return
    lines = ["📈 <b>Eng ko'p buyurtma qilingan mebellar</b>\n"]
    for m in data:
        lines.append(f"📅 <b>{m['month']}</b> — {m['total']} ta · {fmt_money(m['revenue'])}")
        for i, it in enumerate(m["items"][:15], 1):
            lines.append(f"  {i}. {h(it['product_id'])} — {it['count']} ta")
        lines.append("")
    for chunk in chunk_text("\n".join(lines)):
        await message.answer(chunk)


@router.message(Command("test_reminder"))
async def test_reminder(message: Message, scheduler):
    await message.answer("Eslatmalar hozir yuboriladi...")
    await scheduler.send_all_now()


@router.message(Command("backup"))
async def backup_now(message: Message, scheduler):
    await message.answer("⏳ Zaxira nusxa tayyorlanmoqda...")
    await scheduler.send_backup(only_to=message.from_user.id)
