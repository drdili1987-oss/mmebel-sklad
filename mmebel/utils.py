"""Umumiy yordamchi funksiyalar: sana, pul, matn, kalitlar."""
from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta

from .config import TASHKENT_TZ

UZ_MONTHS = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentyabr", 10: "oktyabr", 11: "noyabr", 12: "dekabr",
}
UZ_WEEKDAYS = {
    0: "dushanba", 1: "seshanba", 2: "chorshanba", 3: "payshanba",
    4: "juma", 5: "shanba", 6: "yakshanba",
}

_NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_FORBIDDEN_KEY_CHARS = set(".$#[]/")


# ---------- vaqt ----------
def now() -> datetime:
    return datetime.now(TASHKENT_TZ)


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def month_key(dt: datetime | None = None) -> str:
    return (dt or now()).strftime("%Y-%m")


def last_months(count: int = 6) -> list[str]:
    cur = now()
    out = []
    y, m = cur.year, cur.month
    for _ in range(count):
        out.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return out


def parse_date(value) -> date | None:
    """'DD.MM.YYYY', 'YYYY-MM-DD' yoki 'YYYY-MM-DD HH:MM:SS' ni date ga o'giradi."""
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d.%m.%y"):
        try:
            return datetime.strptime(s if fmt != "%Y-%m-%d" else s[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def format_date(value) -> str:
    d = parse_date(value)
    return d.strftime("%d.%m.%Y") if d else (str(value) if value else "—")


def human_date(value) -> str:
    d = parse_date(value)
    if not d:
        return str(value or "—")
    return f"{d.day} {UZ_MONTHS[d.month]}, {UZ_WEEKDAYS[d.weekday()]}"


def normalize_due_date(text: str, *, allow_past: bool = False) -> str | None:
    """Foydalanuvchi kiritgan sanani tekshiradi va 'DD.MM.YYYY' qaytaradi.

    Noto'g'ri format yoki (allow_past=False bo'lsa) o'tgan sana uchun None.
    """
    if not text:
        return None
    s = text.strip().replace("/", ".").replace("-", ".")
    parts = s.split(".")
    if len(parts) == 3 and len(parts[0]) == 4:  # YYYY.MM.DD
        parts = [parts[2], parts[1], parts[0]]
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    dd, mm, yy = (int(p) for p in parts)
    if yy < 100:
        yy += 2000
    try:
        d = date(yy, mm, dd)
    except ValueError:
        return None
    today = now().date()
    if not allow_past and d < today:
        return None
    if d > today + timedelta(days=366):
        return None
    return d.strftime("%d.%m.%Y")


def is_overdue(due_date, status: str, active_statuses) -> bool:
    if status not in active_statuses:
        return False
    d = parse_date(due_date)
    return bool(d and d < now().date())


# ---------- sonlar ----------
def parse_number(value, default: float | None = None) -> float | None:
    """'340$', '3.5$', '1 200', '450,5' kabi qiymatlardan son ajratadi."""
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).replace("so'm", "").replace("$", "").replace(" ", "").replace(" ", "")
    m = _NUM_RE.search(s)
    if not m:
        return default
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return default


def parse_positive_int(value, *, max_value: int = 100_000) -> int | None:
    s = str(value or "").strip()
    if not s.isdigit():
        return None
    n = int(s)
    return n if 0 < n <= max_value else None


def to_int(value, default: int = 0) -> int:
    n = parse_number(value)
    return int(round(n)) if n is not None else default


def money(value) -> float:
    n = parse_number(value, 0.0) or 0.0
    return round(n, 2)


def fmt_money(value, currency: str = "$") -> str:
    n = money(value)
    if abs(n - round(n)) < 0.005:
        s = f"{int(round(n)):,}".replace(",", " ")
    else:
        s = f"{n:,.2f}".replace(",", " ")
    return f"{s}{currency}"


# ---------- matn ----------
def h(value) -> str:
    """Telegram HTML uchun xavfsiz matn."""
    return html.escape(str(value if value is not None else ""), quote=False)


def clean_text(value, max_len: int = 500) -> str:
    s = str(value or "").replace("\x00", "").strip()
    return s[:max_len]


def has_comment(value) -> bool:
    return bool(value) and str(value).strip().lower() not in ("", "yoq", "yo'q", "yoʻq", "-")


def product_key(name: str) -> str:
    """'BF 54-41' -> 'BF5441' (eski kod bilan bir xil kalit)."""
    return str(name or "").replace(" ", "").replace("-", "").upper()


def is_valid_key(name: str) -> bool:
    """Firebase kaliti sifatida ishlatish mumkinmi (. $ # [ ] / taqiqlangan)."""
    s = str(name or "").strip()
    return bool(s) and len(s) <= 120 and not (set(s) & _FORBIDDEN_KEY_CHARS)


def chunk_text(text: str, limit: int = 3900) -> list[str]:
    """Matnni qatorlar bo'yicha bo'laklaydi (HTML teglarni buzmaslik uchun)."""
    chunks: list[str] = []
    cur = ""
    for line in text.split("\n"):
        while len(line) > limit:  # juda uzun qator
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks or [""]


def iter_records(node):
    """Firebase tugunini (dict yoki list) (key, dict) juftliklariga aylantiradi."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, dict):
                yield str(k), v
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, dict):
                yield str(i), v
