"""Hisob-kitoblar tarixi (admin o'zini tekshirishi uchun): ro'yxat + PDF.

PDF: 1) umumiy ro'yxat — qachon bosilgan, qaysi sana oralig'i, nechta mebel, narxi, olingan pul, kim bosgan;
2) har bir hisob-kitobning mebellari (tartib raqami bo'yicha, har varoqda ~20 qator, pastida shu varoq jami).
Eski hisob-kitoblarda sana oralig'i saqlanmagan — «noma'lum» deb belgilanadi.
"""
from __future__ import annotations

import io

from ..utils import format_date, money
from .delivered_report import ROWS_PER_PAGE, _name, _usd, delivered_rows, register_fonts, serial_key

KIND_LABEL = {"davr": "Sana bo'yicha", "hammasi": "Barchasi", "eski": "Eski (oraliq noma'lum)"}


def _stamp(at: str) -> str:
    return f"{format_date(at)} {str(at)[11:16]}".strip() if at else "—"


def _range(b: dict) -> str:
    if b.get("from") and b.get("to"):
        return f"{format_date(b['from'])} – {format_date(b['to'])}"
    return "noma'lum"


async def settlement_report(services, client: str) -> list[dict]:
    """Hisob-kitoblar + har birining mebellari (rows) va ularning jami."""
    batches = await services.finance.settlement_batches(client)
    all_rows = {r["order_id"]: r for r in await delivered_rows(services, client=client, unsettled_only=False)}
    users = await services.store.get("users") or {}
    for b in batches:
        rows = [all_rows[i] for i in b["order_ids"] if i in all_rows]
        rows.sort(key=lambda r: (r["serial"] == "", serial_key(r["serial"]), r["delivered_at"]))
        b["rows"] = rows
        b["price_total"] = money(sum(r["price"] for r in rows))
        b["collected_total"] = money(sum(r["collected"] for r in rows))
        u = users.get(b["by"]) if isinstance(users, dict) else None
        b["by_name"] = (u or {}).get("name") or (u or {}).get("full_name") or b["by"] or "—"
        b["kind_label"] = KIND_LABEL.get(b["kind"], b["kind"] or "—")
        b["at_label"] = _stamp(b["at"])
        b["range_label"] = _range(b)
    return batches


def as_pdf(client: str, batches: list[dict]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    register_fonts()
    W, H = A4
    margin = 15 * mm
    row_h = 10.5 * mm
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle(f"Hisob-kitoblar tarixi — {client}")
    state = {"page": 0}

    def header(title: str, subtitle: str) -> float:
        state["page"] += 1
        c.setFont("DejaVu-Bold", 15)
        c.drawString(margin, H - margin - 6 * mm, title)
        c.setFont("DejaVu", 10)
        c.setFillColor(colors.HexColor("#555555"))
        c.drawString(margin, H - margin - 13 * mm, subtitle)
        c.drawRightString(W - margin, H - margin - 13 * mm, f"{state['page']}-varoq")
        c.setFillColor(colors.black)
        return H - margin - 24 * mm

    def draw_table(y: float, cols, rows, size: int = 11) -> float:
        total_w = sum(w for _, w, _ in cols)
        c.setFillColor(colors.HexColor("#e8efe4"))
        c.rect(margin, y - row_h, total_w, row_h, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.setFont("DejaVu-Bold", size)
        x = margin
        for label, w, al in cols:
            (c.drawRightString(x + w - 3 * mm, y - row_h + 3.4 * mm, label) if al == "r"
             else c.drawString(x + 3 * mm, y - row_h + 3.4 * mm, label))
            x += w
        y -= row_h
        c.setFont("DejaVu", size)
        for vals in rows:
            x = margin
            for (_, w, al), text in zip(cols, vals, strict=True):
                text = str(text)
                while c.stringWidth(text, "DejaVu", size) > w - 6 * mm and len(text) > 2:
                    text = text[:-2] + "…"
                (c.drawRightString(x + w - 3 * mm, y - row_h + 3.4 * mm, text) if al == "r"
                 else c.drawString(x + 3 * mm, y - row_h + 3.4 * mm, text))
                x += w
            c.setStrokeColor(colors.HexColor("#cccccc"))
            c.line(margin, y - row_h, margin + total_w, y - row_h)
            y -= row_h
        return y

    # 1) umumiy ro'yxat
    sum_cols = [("Bosilgan", 38 * mm, "l"), ("Sana oralig'i", 48 * mm, "l"), ("Soni", 12 * mm, "r"),
                ("Narxi jami", 24 * mm, "r"), ("Dillerdan olingan", 34 * mm, "r"), ("Kim", 24 * mm, "l")]
    per = 22
    chunks = [batches[i:i + per] for i in range(0, len(batches), per)] or [[]]
    for chunk in chunks:
        y = header("Hisob-kitoblar tarixi", f"{client} · jami {len(batches)} ta hisob-kitob")
        if not chunk:
            c.setFont("DejaVu", 12)
            c.drawString(margin, y - 8 * mm, "Hali hisob-kitob qilinmagan.")
        else:
            draw_table(y, sum_cols, [
                [b["at_label"], b["range_label"], b["count"], _usd(b["price_total"]) if b["rows"] else "—",
                 _usd(b["received"]) if b["received"] is not None else "—", b["by_name"]] for b in chunk], size=9)
        c.showPage()

    # 2) har bir hisob-kitob mebellari
    cols = [("Tartib raqam", 34 * mm, "l"), ("Mebel nomi", 64 * mm, "l"), ("Narxi", 36 * mm, "r"),
            ("Mijozdan olingan", 46 * mm, "r")]
    for b in batches:
        title = f"Hisob-kitob: {b['range_label']}"
        sub = f"{client} · bosilgan {b['at_label']} · {b['kind_label']} · {b['count']} ta"
        pages = [b["rows"][i:i + ROWS_PER_PAGE] for i in range(0, len(b["rows"]), ROWS_PER_PAGE)] or [[]]
        for chunk in pages:
            y = header(title, sub)
            if not chunk:
                c.setFont("DejaVu", 11)
                c.drawString(margin, y - 8 * mm, "Mebellar ro'yxati topilmadi (buyurtmalar o'chirilgan yoki saqlanmagan).")
                c.showPage()
                continue
            y = draw_table(y, cols, [[r["serial"] or "—", _name(r), _usd(r["price"]), _usd(r["collected"])]
                                     for r in chunk], size=12)
            y -= 3 * mm
            c.setStrokeColor(colors.black)
            c.line(margin, y, margin + sum(w for _, w, _ in cols), y)
            c.setFont("DejaVu-Bold", 12)
            x_price = margin + cols[0][1] + cols[1][1]
            c.drawString(margin + 3 * mm, y - 7 * mm, f"Varoq jami ({len(chunk)} ta mebel):")
            c.drawRightString(x_price + cols[2][1] - 3 * mm, y - 7 * mm, _usd(sum(r["price"] for r in chunk)))
            c.drawRightString(x_price + cols[2][1] + cols[3][1] - 3 * mm, y - 7 * mm,
                              _usd(sum(r["collected"] for r in chunk)))
            c.showPage()
    c.save()
    return out.getvalue()


__all__ = ["settlement_report", "as_pdf"]
