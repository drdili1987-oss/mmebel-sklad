"""Biznes hodisalari bo'yicha xabarnomalar — bot ham, panel ham shu yerdan foydalanadi."""
from __future__ import annotations

from .bot import keyboards as kb
from .bot.texts import order_card
from .constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM, SELF_PICKUP_DRIVER
from .services.finance import order_client
from .utils import fmt_money, format_date, h

FIELD_LABELS = {"amount": "Soni", "due_date": "Muddati", "comment": "Izohi"}


class Events:
    def __init__(self, notifier):
        self.n = notifier

    async def order_created(self, o: dict, actor_id: int, *, by_diller: bool = False) -> None:
        oid = o["order_id"]
        if by_diller:
            stock = (f"📦 Ombordan ayirildi: {o['deducted_qty']} ta" if o.get("deducted_qty")
                     else "⚠️ Omborda yo'q — ishlab chiqarish kerak")
            await self.n.to_staff(order_card(oid, o, title="🔔 Yangi zakaz (dillerdan)!") + f"\n{stock}")
            return
        await self.n.to_staff(order_card(oid, o, title="🔔 Yangi buyurtma!"), exclude=actor_id)
        await self.n.to_client(order_client(o), order_card(oid, o, show_price=True,
                                                           title="🎉 Sizga yangi buyurtma shakllantirildi!"))

    async def order_ready(self, oid: str, o: dict, actor_id: int) -> None:
        text = (f"✅ <b>Mahsulot tayyor bo'ldi!</b>\n🆔 <code>{h(oid)}</code>\n🧑 {h(order_client(o))}\n"
                f"📦 {h(o.get('product_id'))} — {h(o.get('amount'))} ta")
        await self.n.to_roles([ROLE_ADMIN, ROLE_XODIM, ROLE_OMBORCHI], text, exclude=actor_id)
        await self.n.to_client(order_client(o), f"🎉 <b>Buyurtmangiz tayyor bo'ldi!</b>\n\n📦 <b>{h(o.get('product_id'))}"
                               f"</b> — {h(o.get('amount'))} ta\n📅 Muddat: {format_date(o.get('due_date'))}\n\n"
                               "Yetkazib berish haqida tez orada xabar beramiz.")

    async def order_cancelled(self, oid: str, o: dict, actor_id: int, *, by_diller: bool = False) -> None:
        who = "diller tomonidan" if by_diller else "xodim tomonidan"
        text = (f"❌ <b>Buyurtma bekor qilindi ({who})</b>\n🆔 <code>{h(oid)}</code>\n📦 {h(o.get('product_id'))} — "
                f"{h(o.get('amount'))} ta\n🧑 {h(order_client(o))}\n↩️ Omborga qaytdi: {o.get('returned_qty', 0)} ta")
        await self.n.to_staff(text, exclude=actor_id)
        if not by_diller:
            await self.n.to_client(order_client(o), f"❌ <b>Buyurtmangiz bekor qilindi</b>\n🆔 <code>{h(oid)}</code>\n"
                                   f"📦 {h(o.get('product_id'))} — {h(o.get('amount'))} ta\n\n"
                                   "Batafsil ma'lumot uchun admin bilan bog'laning.")

    async def order_delivered(self, oid: str, o: dict, actor_id: int) -> None:
        driver = o.get("driver", "")
        pickup = driver == SELF_PICKUP_DRIVER
        extra = (f"💸 Chegirma: {h(o['delivery_price'])} → hisoblangan: {fmt_money(o['net'])}" if pickup
                 else f"💵 Dostavka: {h(o['delivery_price'])}")
        client = order_client(o)
        await self.n.to_admins(
            f"📦 <b>Buyurtma {'olib ketildi' if pickup else 'yetkazildi'}</b>\n🆔 <code>{h(oid)}</code>\n🧑 {h(client)}\n"
            f"📦 {h(o.get('product_id'))} — {h(o.get('amount'))} ta\n🚚 {h(driver)} · {extra}\n"
            f"💳 Diller qarzi: {fmt_money(o['debt'])}", exclude=actor_id)
        await self.n.to_client(client, f"🚚 <b>Mebelingiz {'olib ketildi' if pickup else 'yetkazib berildi'}!</b>\n\n"
                               f"📦 <b>{h(o.get('product_id'))}</b> — {h(o.get('amount'))} ta\n"
                               f"💵 Mebel narxi: {fmt_money(o['gross'])}\n"
                               + (f"💸 Chegirma: {h(o['delivery_price'])}\n" if pickup else
                                  f"🧑 Haydovchi: {h(driver)}\n💰 Dostavka: {h(o['delivery_price'])}\n")
                               + f"🆔 <code>{h(oid)}</code>")

    async def order_edited(self, oid: str, o: dict, actor_id: int) -> None:
        changes = o.get("_changes") or {}
        if not changes:
            return
        diff = "\n".join(f"🔄 {FIELD_LABELS.get(k, k)}: <b>{h(v)}</b>" for k, v in changes.items())
        await self.n.to_staff(f"✏️ <b>Buyurtma o'zgartirildi</b>\n🆔 <code>{h(oid)}</code>\n📦 {h(o.get('product_id'))}"
                              f" · 🧑 {h(order_client(o))}\n{diff}", exclude=actor_id)
        await self.n.to_client(
            order_client(o),
            order_card(oid, o, show_price=True, title="⚠️ Buyurtmangizda o'zgartirish!") + f"\n{diff}\n\n❓ Siz uchun qabulmi?",
            reply_markup=kb.inline([[("✅ Tasdiqlash", f"diller_confirm:{oid}"), ("❌ Rad etish", f"diller_reject:{oid}")]]),
        )

    async def payment_requested(self, pay: dict) -> None:
        """Diller to'lov bildirdi — adminlarga tasdiqlash tugmalari bilan."""
        await self.n.to_admins(
            f"💵 <b>Diller to'lov bildirdi!</b>\n\n🧑 {h(pay['diller_name'])} ({h(pay['client_name'])})\n"
            f"💰 Summa: <b>{fmt_money(pay['amount'])}</b>\n📅 {pay['timestamp']}\n\nTasdiqlaysizmi?",
            reply_markup=kb.inline([[("✅ Tasdiqlash", f"pay_confirm:{pay['pay_id']}"),
                                     ("❌ Rad etish", f"pay_reject:{pay['pay_id']}")]]),
        )

    async def payment_resolved(self, pay: dict, approve: bool, debt, actor_id: int) -> None:
        if approve:
            msg = f"✅ <b>To'lovingiz tasdiqlandi!</b>\n💵 {fmt_money(pay['amount'])}\n💳 Yangi qarz: <b>{fmt_money(debt)}</b>"
        else:
            msg = f"❌ <b>To'lovingiz rad etildi.</b>\n💵 {fmt_money(pay['amount'])}\nIltimos, admin bilan bog'laning."
        if pay.get("diller_tg_id"):
            await self.n.send(int(pay["diller_tg_id"]), msg)
        await self.n.to_admins(f"ℹ️ To'lov {h(pay.get('pay_id'))} {'tasdiqlandi' if approve else 'rad etildi'} "
                               f"({h(pay['client_name'])}, {fmt_money(pay['amount'])})", exclude=actor_id)
