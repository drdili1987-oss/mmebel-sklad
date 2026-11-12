"""Yetkazilgan mebellar hisoboti: PDF (A4), CSV va nusxa olish uchun matn.

Saralash — tartib raqami bo'yicha (yetkazilgan sana bo'yicha EMAS). Har varoqda ~20 qator,
pastida faqat SHU VAROQDAGI narxlar va olingan summalar jami (yakuniy umumiy jami chiqarilmaydi).
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date
from pathlib import Path

from ..constants import DELIVERED_STATUSES, ST_SETTLED
from ..utils import iter_records, money, parse_date
from .finance import order_client, order_gross

ROWS_PER_PAGE = 20
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def serial_key(s: str):
    """'2' < '10' < '10a' — raqamli tartib raqamlar son sifatida saralanadi."""
    parts = re.split(r"(\d+)", str(s or "").strip().lower())
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in parts if p] or [(2, 0, "")]


async def delivered_rows(services, *, client: str, start: date | None = None, end: date | None = None,
                         unsettled_only: bool = False) -> list[dict]:
    store = services.store
    orders = dict(iter_records(await store.get("orders") or {}))
    if not unsettled_only:  # hisob-kitob qilinib, arxivga o'tganlari ham kerak bo'lishi mumkin
        for _, month in iter_records(await store.get("orders_archive") or {}):
            for oid, o in iter_records(month):
                orders.setdefault(oid, o)
    paid: dict[str, float] = {}
    for _, p in iter_records(await store.get("wpay") or {}):
        paid[p.get("order_id", "")] = money(paid.get(p.get("order_id", ""), 0) + (p.get("amount") or 0))
    target = client.strip().lower()
    rows = []
    for oid, o in orders.items():
        st = o.get("status", "")
        if order_client(o).lower() != target or not (st in DELIVERED_STATUSES or st == ST_SETTLED):
            continue
        if unsettled_only and st == ST_SETTLED:
            continue
        d = parse_date(o.get("delivered_at"))
        if (start and (not d or d < start)) or (end and (not d or d > end)):
            continue
        rows.append({
            "order_id": oid, "serial": str(o.get("serial", "") or ""), "product": o.get("product_id", ""),
            "variant": o.get("variant", ""), "amount": o.get("amount", 1), "price": order_gross(o),
            "collected": paid.get(oid, 0.0), "delivered_at": str(o.get("delivered_at", ""))[:10],
            "settled": st == ST_SETTLED, "worker": o.get("worker_name") or o.get("driver", ""),
        })
    rows.sort(key=lambda r: (r["serial"] == "", serial_key(r["serial"]), r["delivered_at"]))
    return rows


def _name(r: dict) -> str:
    name = r["product"] + (f" · {r['variant']}" if r.get("variant") else "")
    try:
        qty = int(float(r.get("amount") or 1))
    except (TypeError, ValueError):
        qty = 1
    return name + (f" × {qty}" if qty != 1 else "")


def _usd(v) -> str:
    v = money(v)
    return (f"{v:,.2f}".rstrip("0").rstrip(".").replace(",", " ")) + " $"


def as_text(rows: list[dict]) -> str:
    """Excel/Telegram'ga nusxa olish uchun (TAB bilan ajratilgan)."""
    lines = ["Tartib raqam\tMebel\tNarxi ($)\tMijozdan olingan ($)\tYetkazilgan"]
    lines += [f"{r['serial'] or '—'}\t{_name(r)}\t{r['price']:g}\t{r['collected']:g}\t{r['delivered_at']}" for r in rows]
    return "\n".join(lines)


def as_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")  # Excel (ru/uz lokal) ; ni ajratuvchi sifatida ochadi
    w.writerow(["Tartib raqam", "Mebel", "Narxi ($)", "Mijozdan olingan ($)", "Yetkazilgan", "Hisob-kitob", "Yig'uvchi"])
    for r in rows:
        w.writerow([r["serial"], _name(r), f"{r['price']:g}", f"{r['collected']:g}", r["delivered_at"],
                    "ha" if r["settled"] else "yo'q", r["worker"]])
    return "﻿".encode() + buf.getvalue().encode("utf-8")  # BOM — Excel UTF-8 ni to'g'ri o'qishi uchun


def as_pdf(rows: list[dict], *, title: str, subtitle: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))

    W, H = A4
    margin = 15 * mm
    cols = [("Tartib raqam", 34 * mm, "l"), ("Mebel nomi", 64 * mm, "l"), ("Narxi", 36 * mm, "r"),
            ("Mijozdan olingan", 46 * mm, "r")]
    row_h = 10.5 * mm
    head_top = H - margin
    table_top = head_top - 24 * mm
    pages = [rows[i:i + ROWS_PER_PAGE] for i in range(0, len(rows), ROWS_PER_PAGE)] or [[]]

    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle(title)
    for pno, chunk in enumerate(pages, 1):
        c.setFont("DejaVu-Bold", 15)
        c.drawString(margin, head_top - 6 * mm, title)
        c.setFont("DejaVu", 11)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(margin, head_top - 13 * mm, subtitle)
        c.drawRightString(W - margin, head_top - 13 * mm, f"{pno}-varoq / {len(pages)}")
        c.setFillColor(colors.black)

        y = table_top
        c.setFillColor(colors.HexColor("#e8efe4"))
        c.rect(margin, y - row_h, sum(w for _, w, _ in cols), row_h, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.setFont("DejaVu-Bold", 11)
        x = margin
        for label, w, al in cols:
            if al == "r":
                c.drawRightString(x + w - 3 * mm, y - row_h + 3.4 * mm, label)
            else:
                c.drawString(x + 3 * mm, y - row_h + 3.4 * mm, label)
            x += w
        y -= row_h
        c.setFont("DejaVu", 12)
        for r in chunk:
            vals = [r["serial"] or "—", _name(r), _usd(r["price"]), _usd(r["collected"])]
            x = margin
            for (_, w, al), v in zip(cols, vals, strict=True):
                text = v
                while c.stringWidth(text, "DejaVu", 12) > w - 6 * mm and len(text) > 2:
                    text = text[:-2] + "…"
                if al == "r":
                    c.drawRightString(x + w - 3 * mm, y - row_h + 3.4 * mm, text)
                else:
                    c.drawString(x + 3 * mm, y - row_h + 3.4 * mm, text)
                x += w
            c.setStrokeColor(colors.HexColor("#cccccc"))
            c.line(margin, y - row_h, margin + sum(w for _, w, _ in cols), y - row_h)
            y -= row_h
        # Varoq jami (faqat shu varoqdagi mebellar)
        y -= 3 * mm
        c.setStrokeColor(colors.black)
        c.line(margin, y, margin + sum(w for _, w, _ in cols), y)
        c.setFont("DejaVu-Bold", 12)
        price_sum = money(sum(r["price"] for r in chunk))
        paid_sum = money(sum(r["collected"] for r in chunk))
        x_price = margin + cols[0][1] + cols[1][1]
        c.drawString(margin + 3 * mm, y - 7 * mm, f"Varoq jami ({len(chunk)} ta mebel):")
        c.drawRightString(x_price + cols[2][1] - 3 * mm, y - 7 * mm, _usd(price_sum))
        c.drawRightString(x_price + cols[2][1] + cols[3][1] - 3 * mm, y - 7 * mm, _usd(paid_sum))
        c.showPage()
    c.save()
    return out.getvalue()


__all__ = ["delivered_rows", "as_pdf", "as_csv", "as_text", "serial_key", "ROWS_PER_PAGE"]
