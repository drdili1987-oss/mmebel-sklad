from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, MenuButtonDefault, MenuButtonWebApp, Message, WebAppInfo

from ...constants import PANEL_ROLES, ROLE_ADMIN, ROLE_LABELS
from ...utils import chunk_text, fmt_money, h, to_int
from .. import keyboards as kb

router = Router(name="common")
log = logging.getLogger(__name__)


async def sync_menu_button(bot, chat_id: int, role: str, settings) -> None:
    """Xodimlarda chap pastki "Panel" tugmasi bo'ladi (WebApp initData shu orqali keladi)."""
    try:
        if role in PANEL_ROLES and settings.panel_url:
            await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonWebApp(
                text="Panel", web_app=WebAppInfo(url=settings.panel_url)))
        else:
            await bot.set_chat_menu_button(chat_id=chat_id, menu_button=MenuButtonDefault())
    except Exception as e:  # noqa: BLE001
        log.debug("menu button: %s", e)


@router.message(CommandStart(deep_link=True, magic=F.args.startswith("login_")))
async def app_login(message: Message, command: CommandObject, state: FSMContext, role: str, services):
    """Mobil ilovaga kirishni tasdiqlash (ilova ochgan bot havolasi)."""
    from ...services import ServiceError
    await state.clear()
    code = (command.args or "")[6:]
    allowed = role in PANEL_ROLES
    try:
        await services.sessions.approve(code, message.from_user.id, approve=allowed)
    except ServiceError as e:
        await message.answer(f"❌ {h(e)}", reply_markup=kb.main_menu(role))
        return
    if allowed:
        await message.answer(f"✅ <b>Ilovaga kirish tasdiqlandi.</b>\nRol: {ROLE_LABELS.get(role, role)}\n\n"
                             "Ilovaga qayting — bir necha soniyada ochiladi.", reply_markup=kb.main_menu(role))
    else:
        await message.answer("⛔ Ilova faqat admin, omborchi va xodimlar uchun.\n"
                             f"Sizning ID: <code>{message.from_user.id}</code> — rol olish uchun adminga yuboring.",
                             reply_markup=kb.main_menu(role))


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, role: str, settings):
    await state.clear()
    await sync_menu_button(message.bot, message.chat.id, role, settings)
    await message.answer(
        f"Assalomu alaykum, {h(message.from_user.first_name)}!\nRolingiz: <b>{ROLE_LABELS.get(role, role)}</b>",
        reply_markup=kb.main_menu(role),
    )


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"Sizning Telegram ID: <code>{message.from_user.id}</code>\n"
                         "Rol berish uchun shu raqamni adminga yuboring.")


@router.message(F.text == kb.BACK)
async def go_home(message: Message, state: FSMContext, role: str):
    await state.clear()
    await message.answer("Asosiy menyu.", reply_markup=kb.main_menu(role))


@router.message(F.text == kb.B_PANEL)
async def open_panel(message: Message, role: str, settings):
    if role not in PANEL_ROLES:
        await message.answer("⛔ Panel faqat xodimlar uchun.", reply_markup=kb.main_menu(role))
        return
    if not settings.panel_url:
        await message.answer("Panel manzili sozlanmagan (PUBLIC_URL).")
        return
    await sync_menu_button(message.bot, message.chat.id, role, settings)
    await message.answer("Panelni ochish uchun tugmani bosing:", reply_markup=kb.panel_inline(settings.panel_url))


@router.message(F.text.in_({kb.B_STOCK, kb.B_STOCK_PUBLIC}))
async def view_stock(message: Message, role: str, services):
    products = await services.inventory.all()
    rows = [(pid, p) for pid, p in products.items() if to_int(p.get("soni")) > 0]
    if not rows:
        await message.answer("Omborda hozircha mebel yo'q.", reply_markup=kb.main_menu(role))
        return
    rows.sort(key=lambda kv: kv[1].get("nomi", kv[0]))
    lines = [f"📦 <b>Omborda mavjud ({len(rows)} xil):</b>\n"]
    for pid, p in rows:
        line = f"🪑 <b>{h(p.get('nomi', pid))}</b>"
        if p.get("modeli"):
            line += f" ({h(p.get('modeli'))})"
        line += f" — <b>{to_int(p.get('soni'))} ta</b>"
        if role == ROLE_ADMIN and p.get("narxi") not in (None, ""):
            line += f" · {fmt_money(p.get('narxi'))}"
        lines.append(line)
    for chunk in chunk_text("\n".join(lines)):
        await message.answer(chunk, reply_markup=kb.main_menu(role))


@router.callback_query(F.data == "noop")
async def noop(cb: CallbackQuery):
    await cb.answer()


@router.callback_query(F.data == "close")
async def close_cb(cb: CallbackQuery):
    try:
        await cb.message.delete()
    except Exception:  # noqa: BLE001
        await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()


def fallback_router() -> Router:
    r = Router(name="fallback")

    @r.message(StateFilter(None))
    async def unknown(message: Message, role: str):
        await message.answer("Tushunarsiz buyruq. Iltimos, pastdagi tugmalardan foydalaning.",
                             reply_markup=kb.main_menu(role))

    @r.message()
    async def unknown_in_state(message: Message):
        await message.answer("Iltimos, so'ralgan qiymatni kiriting yoki «Bosh menyu» ni bosing.")

    @r.callback_query()
    async def stale_cb(cb: CallbackQuery):
        await cb.answer("Bu tugma eskirgan yoki sizga ruxsat yo'q.", show_alert=True)

    return r
