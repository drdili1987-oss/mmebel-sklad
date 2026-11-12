"""Biznes hodisalari bo'yicha xabarnomalar — bot ham, panel ham shu yerdan foydalanadi."""
from __future__ import annotations

from .bot import keyboards as kb
from .bot.texts import order_card
from .constants import ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM, SELF_PICKUP_DRIVER
from .services.finance import order_client
from .utils import fmt_money, format_date, h, product_label

FIELD_LABELS = {"amount": "Soni", "due_date": "Muddati", "comment": "Izohi", "changed": "O'zgarishli"}


class Events:
    def __init__(self, notifier):
        self.n = notifier

    async def order_created(self, o: dict, actor_id: int, *, by_diller: bool = False) -> None:
        oid = o["order_id"]
        if by_diller:
            stock = (f"📦 Ombordan ayirildi: {o['deducted_qty']} ta" if o.get("deducted_qty")
                     else "⚠️ Omborda yo'q — ishlab chiqarish kerak")
            await self.n.to_staff(order_card(oid, o, title="🔔 Yangi zakaz (dillerdan)!") + f"\n{stock}",
                                  sound="new", mark=(oid, "new"))
            return
        await self.n.to_staff(order_card(oid, o, title="🔔 Yangi buyurtma!"), exclude=actor_id, sound="new",
                              mark=(oid, "new"))
        await self.n.to_client(order_client(o), order_card(oid, o, show_price=True,
                                                           title="🎉 Sizga yangi buyurtma shakllantirildi!"),
                               sound="new", mark=(oid, "new"))

    async def order_ready(self, oid: str, o: dict, actor_id: int) -> None:
        text = (f"✅ <b>Mahsulot tayyor bo'ldi!</b>\n🆔 <code>{h(oid)}</code>\n🧑 {h(order_client(o))}\n"
                f"📦 {h(product_label(o))} — {h(o.get('amount'))} ta")
        await self.n.to_roles([ROLE_ADMIN, ROLE_XODIM, ROLE_OMBORCHI], text, exclude=actor_id, sound="ready",
                              mark=(oid, "ready"))
        await self.n.to_client(order_client(o), f"🎉 <b>Buyurtmangiz tayyor bo'ldi!</b>\n\n📦 <b>{h(product_label(o))}"
                               f"</b> — {h(o.get('amount'))} ta\n📅 Muddat: {format_date(o.get('due_date'))}\n\n"
                               "Yetkazib berish haqida tez orada xabar beramiz.", sound="ready",
                               mark=(oid, "ready"))

    async def order_cancelled(self, oid: str, o: dict, actor_id: int, *, by_diller: bool = False) -> None:
        who = "diller tomonidan" if by_diller else "xodim tomonidan"
        text = (f"❌ <b>Buyurtma bekor qilindi ({who})</b>\n🆔 <code>{h(oid)}</code>\n📦 {h(product_label(o))} — "
                f"{h(o.get('amount'))} ta\n🧑 {h(order_client(o))}\n↩️ Omborga qaytdi: {o.get('returned_qty', 0)} ta")
        await self.n.to_staff(text, exclude=actor_id, sound="cancel", mark=(oid, "cancel"))
        if not by_diller:
            await self.n.to_client(order_client(o), f"❌ <b>Buyurtmangiz bekor qilindi</b>\n🆔 <code>{h(oid)}</code>\n"
                                   f"📦 {h(product_label(o))} — {h(o.get('amount'))} ta\n\n"
                                   "Batafsil ma'lumot uchun admin bilan bog'laning.", sound="cancel",
                                   mark=(oid, "cancel"))

    async def order_delivered(self, oid: str, o: dict, actor_id: int) -> None:
        driver = o.get("driver", "")
        pickup = driver == SELF_PICKUP_DRIVER
        extra = (f"💸 Chegirma: {h(o['delivery_price'])} → hisoblangan: {fmt_money(o['net'])}" if pickup
                 else f"💵 Dostavka: {h(o['delivery_price'])}")
        client = order_client(o)
        await self.n.to_admins(
            f"📦 <b>Buyurtma {'olib ketildi' if pickup else 'yetkazildi'}</b>\n🆔 <code>{h(oid)}</code>\n🧑 {h(client)}\n"
            f"📦 {h(product_label(o))} — {h(o.get('amount'))} ta\n🚚 {h(driver)} · {extra}\n"
            f"💳 Diller qarzi: {fmt_money(o['debt'])}", exclude=actor_id, mark=(oid, "deliver"))
        await self.n.to_client(client, f"🚚 <b>Mebelingiz {'olib ketildi' if pickup else 'yetkazib berildi'}!</b>\n\n"
                               f"📦 <b>{h(product_label(o))}</b> — {h(o.get('amount'))} ta\n"
                               f"💵 Mebel narxi: {fmt_money(o['gross'])}\n"
                               + (f"💸 Chegirma: {h(o['delivery_price'])}\n" if pickup else
                                  f"🧑 Haydovchi: {h(driver)}\n💰 Dostavka: {h(o['delivery_price'])}\n")
                               + f"🆔 <code>{h(oid)}</code>", mark=(oid, "deliver"))

    async def order_edited(self, oid: str, o: dict, actor_id: int) -> None:
        changes = o.get("_changes") or {}
        if not changes:
            return
        diff = "\n".join(f"🔄 {FIELD_LABELS.get(k, k)}: <b>{h(v)}</b>" for k, v in changes.items())
        await self.n.to_staff(f"✏️ <b>Buyurtma o'zgartirildi</b>\n🆔 <code>{h(oid)}</code>\n📦 {h(product_label(o))}"
                              f" · 🧑 {h(order_client(o))}\n{diff}", exclude=actor_id, mark=(oid, "edit"))
        client_changes = {k: v for k, v in changes.items() if k != "changed"}  # ichki belgi dillerga tegishli emas
        if not client_changes:
            return
        diff = "\n".join(f"🔄 {FIELD_LABELS.get(k, k)}: <b>{h(v)}</b>" for k, v in client_changes.items())
        await self.n.to_client(
            order_client(o),
            order_card(oid, o, show_price=True, title="⚠️ Buyurtmangizda o'zgartirish!") + f"\n{diff}\n\n❓ Siz uchun qabulmi?",
            reply_markup=kb.inline([[("✅ Tasdiqlash", f"diller_confirm:{oid}"), ("❌ Rad etish", f"diller_reject:{oid}")]]),
            mark=(oid, "edit"),
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

    # ---------- mebel yig'uvchilar ----------
    async def order_assigned(self, oid: str, o: dict, actor_id: int) -> None:
        w = o.get("_worker") or {}
        serial = f"№{h(o['serial'])} · " if o.get("serial") else ""
        collect = f"\n💵 Mijozdan olinadigan qoldiq: <b>{fmt_money(o['collect'])}</b>" if o.get("collect") else ""
        text = (f"🧰 <b>Sizga yig'ish uchun mebel yuborildi</b>\n{serial}📦 {h(product_label(o))} — {h(o.get('amount'))} ta\n"
                f"🧑 {h(order_client(o))}" + (f"\n📝 {h(o['comment'])}" if o.get("comment") else "") + collect
                + "\n\nMijozga topshirgach, ilovada «Mebel mijozga topshirildi» tugmasini bosing.")
        if w.get("uid"):
            await self.n.to_ids([int(w["uid"])], text, sound="new", mark=(oid, "new"))
        await self.n.to_roles([ROLE_ADMIN, ROLE_OMBORCHI],
                              f"🧰 {serial}{h(product_label(o))} × {h(o.get('amount'))} ({h(order_client(o))}) — "
                              f"yig'ish uchun <b>{h(o.get('worker_name'))}</b> ga yuborildi", exclude=actor_id)

    async def order_handover(self, res: dict) -> None:
        o, w = res["order"], res["worker"]
        oid = res["order_id"]
        serial = f"№{h(o['serial'])} · " if o.get("serial") else ""
        method = "💳 karta" if res["method"] == "karta" else "💵 naqd"
        ok = "✅ Qoldiq to'g'ri olindi" if res["correct"] else "⚠️ Qoldiq to'liq olinmadi"
        expected = f" (kutilgan {fmt_money(res['expected'])})" if res.get("expected") else ""
        title = "📦 <b>Mebel mijozga topshirildi</b>" if res["kind"] == "handover" else "💵 <b>Mijozdan qo'shimcha to'lov</b>"
        text = (f"{title}\n{serial}📦 {h(product_label(o))} — {h(o.get('amount'))} ta\n🧑 {h(order_client(o))}\n"
                f"🧰 {h(w.get('name'))}\n{ok}: <b>{fmt_money(res['amount'])}</b> {method}{expected}"
                + (f"\n📝 {h(res['note'])}" if res.get("note") else "")
                + (f"\n💳 Diller qarzi: {fmt_money(o['debt'])}" if "debt" in o else ""))
        await self.n.to_roles([ROLE_ADMIN, ROLE_OMBORCHI], text, sound=None if res["correct"] else "cancel",
                              mark=(oid, "deliver"))
        if res.get("photos"):
            await self._send_photos(await self.n.users.ids_with_roles([ROLE_ADMIN]), res["photos"],
                                    f"📎 {serial}{product_label(o)} — {w.get('name')} ({res['method']})")

    async def _send_photos(self, ids, file_ids: list[str], caption: str) -> None:
        from aiogram.types import InputMediaPhoto
        media = [InputMediaPhoto(media=f, caption=caption if i == 0 else None) for i, f in enumerate(file_ids[:10])]
        for uid in dict.fromkeys(ids):
            try:
                await self.n.bot.send_media_group(int(uid), media)
            except Exception:  # noqa: BLE001 — rasm yuborilmasa ham asosiy xabar ketgan
                pass

    async def transfer_requested(self, t: dict) -> None:
        who = "Mebel yig'uvchi" if t.get("from_kind") == "worker" else "Omborchi"
        text = (f"💰 <b>{who} {h(t['from_name'])} sizga {fmt_money(t['amount'])} topshirdi.</b>\n"
                f"Pulni qabul qilgan bo'lsangiz — ilovada tasdiqlang (Asosiy → Kassa).")
        await self.n.to_roles([t["to_role"]], text, sound="new")

    async def transfer_resolved(self, t: dict) -> None:
        if not t.get("from_uid"):
            return
        if t["status"] == "approved":
            msg = f"✅ <b>Topshirish tasdiqlandi</b>\n{h(t.get('text', ''))}"
        else:
            msg = (f"❌ <b>Topshirish rad etildi</b> ({fmt_money(t['amount'])}).\n"
                   f"Rad etgan: {h(t.get('resolved_name', ''))}. Iltimos, bog'laning.")
        await self.n.send(int(t["from_uid"]), msg)
