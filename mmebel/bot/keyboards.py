"""Klaviaturalar va tugma matnlari."""
from __future__ import annotations

from datetime import timedelta

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from ..constants import ROLE_ADMIN, ROLE_DILLER, ROLE_OMBORCHI, ROLE_XODIM
from ..utils import now

BACK = "Bosh menyu"
OTHER_CLIENT = "Boshqa (Yangi diller)"
OTHER_MODEL = "Boshqa (Qo'lda kiritish)"
SKIP = "⏩ O'tkazib yuborish"
NO_IMAGE = "⏩ Rasmsiz saqlash"

# Asosiy menyu tugmalari
B_STOCK = "📦 Mavjud mebellar"
B_STOCK_PUBLIC = "🛍 Sotuvdagi mebellar"
B_NEW_ORDER = "📝 Yangi buyurtma"
B_ORDER_CTRL = "📋 Buyurtmalar nazorati"
B_ACCOUNTS = "📊 Hisob kitoblar"
B_DRIVERS = "🚚 Haydovchilar hisoboti"
B_DEBTS = "💰 Dillerlar qarzi"
B_HISTORY = "🕰 Yetkazish tarixi"
B_SALES = "📈 Sotuv statistikasi"
B_STOCK_UPDATE = "🔄 Omborni yangilash"
B_DELIVERY_CTRL = "🚚 Yetkazishlar nazorati"
B_DELIVERY_REPORT = "📊 Dostavka hisoboti"
B_ACTIVE = "🔨 Faol buyurtmalar"
B_PANEL = "🖥 Panel"
B_D_ORDER = "📝 Zakaz berish"
B_D_HISTORY = "📋 Buyurtmalar tarixi"
B_D_CANCEL = "❌ Zakazni bekor qilish"
B_D_STATUS = "📊 Buyurtmalar holati"
B_D_PAYMENT = "📥 Kirim-Chiqim"
B_D_PHOTOS = "📸 Rasmlar va narxlar"
B_QTY_UPDATE = "📦 Ombor sonini yangilash"
B_NEW_PRODUCT = "➕ Yangi mebel"

MAIN_MENU_BUTTONS = {
    BACK, B_STOCK, B_STOCK_PUBLIC, B_NEW_ORDER, B_ORDER_CTRL, B_ACCOUNTS, B_DRIVERS, B_DEBTS,
    B_HISTORY, B_SALES, B_STOCK_UPDATE, B_DELIVERY_CTRL, B_DELIVERY_REPORT, B_ACTIVE, B_PANEL,
    B_D_ORDER, B_D_HISTORY, B_D_CANCEL, B_D_STATUS, B_D_PAYMENT, B_D_PHOTOS, B_QTY_UPDATE, B_NEW_PRODUCT,
}


def _kb(rows: list[list[str]]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t) for t in r] for r in rows],
                               resize_keyboard=True)


def main_menu(role: str) -> ReplyKeyboardMarkup:
    if role == ROLE_ADMIN:
        rows = [[B_STOCK, B_NEW_ORDER], [B_ORDER_CTRL, B_ACCOUNTS], [B_DRIVERS, B_DEBTS],
                [B_HISTORY, B_SALES], [B_DELIVERY_CTRL, B_STOCK_UPDATE], [B_PANEL]]
    elif role == ROLE_OMBORCHI:
        rows = [[B_STOCK_UPDATE, B_DELIVERY_CTRL], [B_STOCK, B_DELIVERY_REPORT], [B_HISTORY, B_PANEL]]
    elif role == ROLE_XODIM:
        rows = [[B_ACTIVE], [B_PANEL]]
    elif role == ROLE_DILLER:
        rows = [[B_STOCK_PUBLIC, B_D_ORDER], [B_D_HISTORY, B_D_CANCEL], [B_D_STATUS, B_D_PAYMENT], [B_D_PHOTOS]]
    else:
        rows = [[B_STOCK_PUBLIC]]
    return _kb(rows)


def back_kb() -> ReplyKeyboardMarkup:
    return _kb([[BACK]])


def grid(items: list[str], cols: int = 3, extra: list[str] | None = None) -> ReplyKeyboardMarkup:
    rows = [items[i:i + cols] for i in range(0, len(items), cols)]
    for e in extra or []:
        rows.append([e])
    rows.append([BACK])
    return _kb(rows)


def dates_kb(start_day: int = 0, days: int = 15) -> ReplyKeyboardMarkup:
    today = now()
    items = [(today + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(start_day, start_day + days)]
    return grid(items, 3)


def panel_inline(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🖥 Panelni ochish",
                                                                       web_app=WebAppInfo(url=url))]])


def inline(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in r]
                                                 for r in rows if r])


def paged(items: list[tuple[str, str]], page: int, prefix: str, per_page: int = 8,
          extra: list[list[tuple[str, str]]] | None = None) -> InlineKeyboardMarkup:
    """items: (matn, callback_data). Sahifalash tugmalari `{prefix}:p:{n}`."""
    pages = max(1, (len(items) + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    rows = [[it] for it in items[page * per_page:(page + 1) * per_page]]
    if pages > 1:
        nav = []
        if page > 0:
            nav.append(("◀️", f"{prefix}:p:{page - 1}"))
        nav.append((f"{page + 1}/{pages}", "noop"))
        if page < pages - 1:
            nav.append(("▶️", f"{prefix}:p:{page + 1}"))
        rows.append(nav)
    rows.extend(extra or [])
    return inline(rows)
