"""Statuslar, rollar va boshlang'ich (seed) ma'lumotlar."""
from __future__ import annotations

# --- Rollar ---
ROLE_ADMIN = "admin"
ROLE_OMBORCHI = "omborchi"
ROLE_XODIM = "xodim"
ROLE_DILLER = "diller"
ROLE_MIJOZ = "mijoz"

STAFF_ROLES = (ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM)
ALL_ROLES = (ROLE_ADMIN, ROLE_OMBORCHI, ROLE_XODIM, ROLE_DILLER, ROLE_MIJOZ)
PANEL_ROLES = STAFF_ROLES

ROLE_LABELS = {
    ROLE_ADMIN: "Admin",
    ROLE_OMBORCHI: "Omborchi",
    ROLE_XODIM: "Xodim",
    ROLE_DILLER: "Diller",
    ROLE_MIJOZ: "Mijoz",
}

# Eski bazadagi sinonimlar
ROLE_ALIASES = {"ishchi": ROLE_XODIM}

# --- Buyurtma statuslari (bazadagi qiymatlar o'zgarmaydi) ---
ST_PREPARING = "Tayyorlanmoqda"
ST_READY = "Tayyor bo'ldi"
ST_SENT = "Yuborildi"  # eski status
ST_DELIVERED = "Biz yetkazib berdik"
ST_PICKED_UP = "Dillerni o'zi olib ketdi"
ST_PICKED_UP_LEGACY = "Mijozni o'zi olib ketdi"
ST_SETTLED = "Hisob kitob qilindi"
ST_CANCELLED = "Bekor qilindi"

ACTIVE_STATUSES = frozenset({ST_PREPARING, ST_READY, ST_SENT})
DELIVERED_STATUSES = frozenset({ST_DELIVERED, ST_PICKED_UP, ST_PICKED_UP_LEGACY})
TERMINAL_STATUSES = frozenset({ST_SETTLED, ST_CANCELLED})
# Qarzga KIRMAYDIGAN statuslar (qolgan hammasi qarzga kiradi — eski mantiq bilan bir xil)
DEBT_EXCLUDED_STATUSES = frozenset({ST_PREPARING, ST_READY, ST_CANCELLED, ST_SETTLED})

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    ST_PREPARING: frozenset({ST_READY, ST_DELIVERED, ST_PICKED_UP, ST_CANCELLED}),
    ST_READY: frozenset({ST_PREPARING, ST_DELIVERED, ST_PICKED_UP, ST_CANCELLED}),
    ST_SENT: frozenset({ST_READY, ST_DELIVERED, ST_PICKED_UP, ST_CANCELLED}),
}

SELF_PICKUP_DRIVER = "O'zi olib ketdi"

# --- Boshlang'ich ma'lumotlar (faqat bazada yo'q bo'lsa yoziladi) ---
DEFAULT_CLIENTS = [
    "Comfort", "Iskandar", "Grand plaza", "Baxrom Uchtepa",
    "Baxrom 9703", "Bahodir aka🚛", "Bahodir aka Andijon", "Akrom aka",
    "Zoʻr mebel", "Umid", "Akmal aka", "Doʻkon 707", "Farxod Jomiy",
    "Munosib Mebel", "Ideal Max", "Muxtor aka", "Elyor", "Anor Mebel", "Best Decor",
]

DEFAULT_DRIVERS = ["Dilmurod", "Bahodir aka", "Javxar", "Baxrom"]

DEFAULT_MODELS = [
    "BF 06", "BF 07", "BF 09",
    "BF 12", "BF 14", "BF 15", "BF 18",
    "BF 244", "BF 264", "BF 274", "BF 294",
    "BF 246", "BF 266", "BF 276", "BF 296",
    "BF 2461", "BF 2661", "BF 2761", "BF 2961",
    "BF SH 2461", "BF SH 2661", "BF SH 2761", "BF SH 2961",
    "BF 32", "BF 33", "BF 34", "BF 35", "BF 37", "BF 38", "BF 39",
    "BF 321", "BF 331", "BF 341", "BF 351", "BF 371", "BF 381", "BF 391",
    "BF 44", "BF 45",
    "BF 544", "BF 574", "BF 594",
    "BF 54-41", "BF 57-41", "BF 59-41",
    "BF 63", "BF 64", "BF 65", "BF 68",
    "BF 707", "BF 708", "BF 709",
    "BF 762", "BF 752", "BF 772", "KR 792",
    "BF 713", "BF 753", "BF 763",
    "BF 87", "BF 773",
    "D 100", "D 106", "D 109",
    "D 50", "D 59",
    "D 003", "D 004", "D 006", "D 005",
]

DEFAULT_DELIVERY_PRICES = [3.5, 6, 8]
DEFAULT_PICKUP_DISCOUNTS = [0, 6, 8, 10]
DEFAULT_PRICE_CHANNEL = "https://t.me/+6yKALewduspiZDBi"

# Eski kodda qattiq yozilgan foydalanuvchilar — bir martalik migratsiyada bazaga ko'chiriladi.
LEGACY_ROLE_IDS: dict[str, str] = {
    "883589794": ROLE_OMBORCHI,
    "6298036669": ROLE_XODIM,
    "1349256808": ROLE_XODIM,
    "7062569902": ROLE_XODIM,
    "7941658592": ROLE_XODIM,
    "1724350130": ROLE_XODIM,
    "698145797": ROLE_XODIM,
    "5063420475": ROLE_XODIM,
}

LEGACY_DILLERS: dict[str, list[int]] = {
    "Munosib Mebel": [261261387],
    "Zoʻr mebel": [8043160151, 8897559819, 15541688],
    "Ideal Max": [953905880, 8310083751],
    "Iskandar": [1052843333],
    "Umid": [1270440064],
    "Elyor": [1268839562],
    "Anor Mebel": [1062031662, 531650486],
}
