"""Diller funksiyalari."""
from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ...constants import (
    ACTIVE_STATUSES,
    DELIVERED_STATUSES,
    ROLE_DILLER,
    ST_CANCELLED,
    ST_PREPARING,
    ST_READY,
)
from ...services import ServiceError
from ...services.finance import order_client
from ...utils import chunk_text, fmt_money, format_date, h, parse_positive_int, product_key, to_int
from .. import keyboards as kb
from ..middlewares import Role
from ..texts import icon

router = Router(name="diller")
router.message.filter(Role(ROLE_DILLER))
router.callback_query.filter(Role(ROLE_DILLER))


class DOrder(StatesGroup):
    product = State()
    amount = State()
    due = State()


class DPay(StatesGroup):
    amount = State()


async def client_of(services, user) -> str:
    name = await services.users.client_name_for(user.id)
    if name:
        return name
    raw = user.full_name or user.username or str(user.id)
    return re.sub(r"[.$#\[\]/]", " ", raw).strip()[:60] or str(user.id)


@router.message(F.text == kb.B_D_PHOTOS)
async def photos(message: Message, services):
    url = (await services.catalog.settings())["price_channel"]
    await message.answer(f"📸 Rasmlar va narxlar kanali:\n👉 <a href=\"{h(url)}\">Kanalga o'tish</a>")


# ---------- zakaz berish ----------
@router.message(F.text == kb.B_D_ORDER)
async def order_start(message: Message, state: FSMContext, services):
    products = await services.inventory.all()
    items_map: dict[str, str] = {}
    buttons = []
    for model in await services.catalog.models():
        soni = to_int((products.get(product_key(model)) or {}).get("soni"))
        text = f"{model} ✅ {soni} ta" if soni > 0 else model
        items_map[text] = model
        buttons.append(text)
    await state.set_state(DOrder.product)
    await state.update_data(items_map=items_map)
    await message.answer("📦 Qaysi mebelni olmoqchisiz?\n✅ — omborda bor, qolganlari oldindan zakaz:",
                         reply_markup=kb.grid(buttons, 3))


@router.message(DOrder.product)
async def order_product(message: Message, state: FSMContext, services):
    data = await state.get_data()
    model = data.get("items_map", {}).get(message.text or "")
    if not model:
        await message.answer("Iltimos, ro'yxatdan tanlang.")
        return
    p = await services.inventory.get(model)
    soni = to_int((p or {}).get("soni"))
    await state.update_data(model=model, stock=soni)
    info = f"📦 Omborda: <b>{soni} ta</b>" if soni > 0 else "⚠️ Hozir omborda yo'q — oldindan zakaz qabul qilinadi."
    await message.answer(f"✅ <b>{h(model)}</b> tanlandi.\n{info}\n\nNechta olmoqchisiz? (raqam)",
                         reply_markup=kb.back_kb())
    await state.set_state(DOrder.amount)


@router.message(DOrder.amount)
async def order_amount(message: Message, state: FSMContext):
    qty = parse_positive_int(message.text, max_value=1000)
    if not qty:
        await message.answer("❌ 1 dan 1000 gacha butun son kiriting (masalan: 2).")
        return
    data = await state.get_data()
    await state.update_data(amount=qty)
    await message.answer("📅 Qaysi sanaga kerak? Tugmadan tanlang yoki yozing (KK.OO.YYYY):",
                         reply_markup=kb.dates_kb(2 if qty > data.get("stock", 0) else 0))
    await state.set_state(DOrder.due)


@router.message(DOrder.due)
async def order_due(message: Message, state: FSMContext, services, events):
    data = await state.get_data()
    client = await client_of(services, message.from_user)
    try:
        o = await services.orders.create(
            message.from_user.id, client_name=client, product=data["model"], amount=data["amount"],
            due_date=message.text or "", source="diller", client_tg_id=message.from_user.id,
        )
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    price = f"\n💰 {fmt_money(o['price'])} × {o['amount']} = <b>{fmt_money(o['total_price'])}</b>" if o["price"] else ""
    await message.answer(f"✅ Zakaz qabul qilindi!\n🆔 <code>{o['order_id']}</code>\n"
                         f"📦 {h(o['product_id'])} — {o['amount']} ta\n📅 Muddat: {o['due_date']}{price}",
                         reply_markup=kb.main_menu(ROLE_DILLER))
    await events.order_created(o, message.from_user.id, by_diller=True)


# ---------- tarix va holat ----------
@router.message(F.text == kb.B_D_HISTORY)
async def history(message: Message, services):
    rows = [(k, v) for k, v in await services.orders.for_diller(message.from_user.id, None) if v["_own"]]
    active = [(k, v) for k, v in rows if v.get("status") in ACTIVE_STATUSES]
    done = [(k, v) for k, v in rows if v.get("status") in DELIVERED_STATUSES or v.get("status") == "Hisob kitob qilindi"]
    if not active and not done:
        await message.answer("Hozircha buyurtma yo'q.")
        return
    lines = ["📋 <b>Siz bergan buyurtmalar:</b>\n"]
    if active:
        lines.append(f"⏳ <b>Tayyorlanayotgan — {len(active)} ta:</b>")
        for _, o in active:
            lines.append(f"  {icon(o.get('status'))} {h(o.get('product_id'))} — {h(o.get('amount'))} ta · "
                         f"📅 {format_date(o.get('due_date'))} · {h(o.get('status'))}")
        lines.append("")
    if done:
        lines.append(f"✅ <b>Olingan — {len(done)} ta:</b>")
        for _, o in done[:25]:
            lines.append(f"  📦 {h(o.get('product_id'))} — {h(o.get('amount'))} ta · "
                         f"{format_date(o.get('delivered_at') or o.get('due_date'))}")
    for chunk in chunk_text("\n".join(lines)):
        await message.answer(chunk)


@router.message(F.text == kb.B_D_STATUS)
async def status(message: Message, services):
    client = await services.users.client_name_for(message.from_user.id)
    rows = await services.orders.for_diller(message.from_user.id, client)
    if not rows:
        await message.answer("Hozircha buyurtma yo'q.")
        return
    pending = [(k, v) for k, v in rows if v.get("status") in ACTIVE_STATUSES]
    delivered = [(k, v) for k, v in rows if v.get("status") in DELIVERED_STATUSES or v.get("status") == "Hisob kitob qilindi"]
    cancelled = [(k, v) for k, v in rows if v.get("status") == ST_CANCELLED]
    lines = ["📊 <b>Barcha buyurtmalaringiz</b>", "<i>(👤 siz bergansiz · 🏷 admin yaratgan)</i>\n"]
    if pending:
        lines.append(f"⏳ <b>Jarayonda — {len(pending)} ta:</b>")
        for _, o in pending:
            src = "👤" if o["_own"] else "🏷"
            total = f" · 💰 {fmt_money(o.get('total_price'))}" if o.get("total_price") else ""
            lines.append(f"  {src} {icon(o.get('status'))} <b>{h(o.get('product_id'))}</b> — {h(o.get('amount'))} ta"
                         f" · 📅 {format_date(o.get('due_date'))}{total}")
        lines.append("")
    if delivered:
        lines.append(f"✅ <b>Yetkazilgan — {len(delivered)} ta:</b>")
        for _, o in delivered[:30]:
            src = "👤" if o["_own"] else "🏷"
            drv = f" · 🚚 {h(o.get('driver'))}" if o.get("driver") else ""
            lines.append(f"  {src} 📦 <b>{h(o.get('product_id'))}</b> — {h(o.get('amount'))} ta · "
                         f"{fmt_money(o.get('total_price') or 0)} · {format_date(o.get('delivered_at'))}{drv}")
        if len(delivered) > 30:
            lines.append(f"  <i>...va yana {len(delivered) - 30} ta</i>")
        lines.append("")
    if cancelled:
        lines.append(f"❌ <b>Bekor qilingan — {len(cancelled)} ta</b>")
    if client:
        acc = await services.finance.account(client)
        lines.append(f"\n💳 Joriy qarz: <b>{fmt_money(acc.debt)}</b>")
    for chunk in chunk_text("\n".join(lines)):
        await message.answer(chunk)


# ---------- bekor qilish ----------
@router.message(F.text == kb.B_D_CANCEL)
async def cancel_start(message: Message, services):
    rows = [(k, v) for k, v in await services.orders.for_diller(message.from_user.id, None)
            if v["_own"] and v.get("status") == ST_PREPARING and v.get("source", "diller") == "diller"]
    if not rows:
        await message.answer("❌ Bekor qilish mumkin bo'lgan zakaz yo'q.\n"
                             "<i>Faqat siz bergan va «Tayyorlanmoqda» holatidagi zakazlar bekor qilinadi.</i>")
        return
    buttons = [[(f"🚫 {o.get('product_id')} — {o.get('amount')} ta · {format_date(o.get('due_date'))}",
                 f"dc:{k}")] for k, o in rows[:30]]
    await message.answer("Qaysi zakazni bekor qilmoqchisiz?", reply_markup=kb.inline(buttons + [[("Yopish", "close")]]))


@router.callback_query(F.data.startswith("dc:"))
async def cancel_pick(cb: CallbackQuery, services):
    oid = cb.data[3:]
    try:
        o = await services.orders.get(oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.edit_text(
        f"⚠️ <b>{h(o.get('product_id'))}</b> — {h(o.get('amount'))} ta zakazni bekor qilasizmi?\n"
        f"📅 Muddat: {format_date(o.get('due_date'))}",
        reply_markup=kb.inline([[("✅ Ha, bekor qil", f"dcy:{oid}"), ("🔙 Yo'q", "close")]]))
    await cb.answer()


@router.callback_query(F.data.startswith("dcy:"))
async def cancel_confirm(cb: CallbackQuery, services, events):
    oid = cb.data[4:]
    try:
        o = await services.orders.cancel(cb.from_user.id, oid, only_preparing=True, owner_tg_id=cb.from_user.id)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    await cb.message.edit_text(f"✅ Zakaz bekor qilindi: <b>{h(o.get('product_id'))}</b> — {h(o.get('amount'))} ta")
    await cb.answer()
    await events.order_cancelled(oid, o, cb.from_user.id, by_diller=True)


# ---------- to'lov xabarnomasi ----------
@router.message(F.text == kb.B_D_PAYMENT)
async def pay_start(message: Message, state: FSMContext):
    await state.set_state(DPay.amount)
    await message.answer("💵 <b>To'lov summasini kiriting</b> ($)\nMasalan: <code>450</code>\n\n"
                         "<i>Admin tasdiqlagandan keyin qarzingizdan ayiriladi.</i>", reply_markup=kb.back_kb())


@router.message(DPay.amount)
async def pay_amount(message: Message, state: FSMContext, services, notifier):
    client = await client_of(services, message.from_user)
    try:
        pay = await services.finance.create_pending_payment(
            message.from_user.id, message.from_user.full_name or str(message.from_user.id), client, message.text)
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}")
        return
    await state.clear()
    await message.answer(f"✅ To'lov xabaringiz adminga yuborildi!\n💵 Summa: <b>{fmt_money(pay['amount'])}</b>\n\n"
                         "Admin tasdiqlagach qarzingizdan ayiriladi.", reply_markup=kb.main_menu(ROLE_DILLER))
    await notifier.to_admins(
        f"💵 <b>Diller to'lov bildirdi!</b>\n\n🧑 {h(pay['diller_name'])} ({h(client)})\n"
        f"💰 Summa: <b>{fmt_money(pay['amount'])}</b>\n📅 {pay['timestamp']}\n\nTasdiqlaysizmi?",
        reply_markup=kb.inline([[("✅ Tasdiqlash", f"pay_confirm:{pay['pay_id']}"),
                                 ("❌ Rad etish", f"pay_reject:{pay['pay_id']}")]]),
    )


# ---------- admin o'zgartirishini tasdiqlash ----------
@router.callback_query(F.data.startswith("diller_confirm:") | F.data.startswith("diller_reject:"))
async def change_answer(cb: CallbackQuery, services, notifier):
    action, oid = cb.data.split(":", 1)
    try:
        o = await services.orders.get(oid)
    except ServiceError as e:
        await cb.answer(str(e), show_alert=True)
        return
    client = await services.users.client_name_for(cb.from_user.id)
    if not client or client.strip().lower() != order_client(o).lower():
        await cb.answer("Bu buyurtma sizga tegishli emas.", show_alert=True)
        return
    ok = action == "diller_confirm"
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(("✅ O'zgarish tasdiqlandi." if ok else "❌ O'zgarish rad etildi.") +
                            f"\n🆔 <code>{h(oid)}</code>\nAdmin xabardor qilindi.")
    await cb.answer()
    await notifier.to_admins(
        f"{'✅' if ok else '❌'} Diller ({h(client)}) o'zgarishni <b>{'TASDIQLADI' if ok else 'RAD ETDI'}</b>\n"
        f"🆔 <code>{h(oid)}</code> · {h(o.get('product_id'))}" + ("" if ok else "\nIltimos, diller bilan bog'laning!")
    )


__all__ = ["router", "ST_READY"]
