"""Xabar matnlari (HTML)."""
from __future__ import annotations

from collections import OrderedDict
from datetime import date

from ..constants import ACTIVE_STATUSES, ST_CANCELLED, ST_PREPARING, ST_READY, ST_SENT
from ..utils import fmt_money, format_date, h, has_comment, human_date, is_overdue, parse_date

STATUS_ICONS = {
    ST_PREPARING: "🔧",
    ST_READY: "✅",
    ST_SENT: "🚚",
    "Biz yetkazib berdik": "📦",
    "Dillerni o'zi olib ketdi": "🏠",
    "Mijozni o'zi olib ketdi": "🏠",
    "Hisob kitob qilindi": "💳",
    ST_CANCELLED: "❌",
}


def icon(status: str) -> str:
    return STATUS_ICONS.get(status, "•")


def order_card(oid: str, o: dict, *, show_price: bool = False, title: str = "") -> str:
    lines = [f"<b>{h(title)}</b>"] if title else []
    lines += [
        f"🆔 <code>{h(oid)}</code>",
        f"🧑 Diller: {h(o.get('client_name') or o.get('client') or '—')}",
        f"📦 Mebel: <b>{h(o.get('product_id', '—'))}</b> — {h(o.get('amount', 1))} ta",
        f"📅 Muddat: {h(format_date(o.get('due_date')))}",
    ]
    if show_price and (o.get("total_price") or o.get("price")):
        lines.append(f"💰 Narxi: {fmt_money(o.get('price', 0))} × {h(o.get('amount', 1))} = "
                     f"<b>{fmt_money(o.get('total_price', 0))}</b>")
    if has_comment(o.get("comment")):
        lines.append(f"📝 Izoh: {h(o.get('comment'))}")
    st = o.get("status", "")
    overdue = " ⚠️ <b>muddati o'tgan</b>" if is_overdue(o.get("due_date"), st, ACTIVE_STATUSES) else ""
    lines.append(f"📌 Holati: {icon(st)} {h(st)}{overdue}")
    if o.get("driver"):
        lines.append(f"🚚 {h(o.get('driver'))} ({h(o.get('delivery_price', ''))})")
    return "\n".join(lines)


def grouped_by_due(rows: list[tuple[str, dict]], *, show_status: bool = True) -> str:
    groups: "OrderedDict[str, list]" = OrderedDict()
    for oid, o in sorted(rows, key=lambda kv: parse_date(kv[1].get("due_date")) or date.max):
        groups.setdefault(format_date(o.get("due_date")), []).append((oid, o))
    parts = []
    for d, items in groups.items():
        overdue = is_overdue(d, ST_PREPARING, ACTIVE_STATUSES)
        parts.append(f"{'🔴' if overdue else '🗓'} <b>{h(human_date(d))}</b>")
        for oid, o in items:
            line = f"{icon(o.get('status', ''))} <b>{h(o.get('product_id', ''))}</b> × {h(o.get('amount', 1))}" \
                   f" — {h(o.get('client_name', ''))}"
            if show_status and o.get("status") != ST_PREPARING:
                line += f" <i>({h(o.get('status', ''))})</i>"
            parts.append(line)
            if has_comment(o.get("comment")):
                parts.append(f"   📝 {h(o.get('comment'))}")
            parts.append(f"   🆔 <code>{h(oid)}</code>")
        parts.append("")
    return "\n".join(parts).strip()


def short_btn(oid: str, o: dict) -> str:
    return f"{icon(o.get('status', ''))} {o.get('product_id', '')} ×{o.get('amount', 1)} · " \
           f"{str(o.get('client_name', ''))[:14]} · {format_date(o.get('due_date'))[:5]}"
