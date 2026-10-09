/* Munosib Mebel — admin dashboard (katta ekran). Ma'lumotlar har 60 soniyada yangilanadi.
   Xavfsizlik: DOM faqat textContent orqali to'ldiriladi; kirish — panel bilan umumiy sessiya tokeni. */
"use strict";

const REFRESH_MS = 60000;
const SVGNS = "http://www.w3.org/2000/svg";
const MONTHS = ["yan", "fev", "mar", "apr", "may", "iyun", "iyul", "avg", "sen", "okt", "noy", "dek"];
let DATA = null;
let timer = null;

/* ---------- yordamchilar ---------- */
function el(tag, attrs, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
    else if (k === "style") n.style.cssText = v;
    else n.setAttribute(k, String(v));
  }
  for (const c of children.flat()) if (c !== null && c !== undefined && c !== false)
    n.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  return n;
}
function svg(tag, attrs) {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, String(v));
  return n;
}
function money(v, compact) {
  const n = Number(v || 0);
  if (compact && Math.abs(n) >= 1000) {
    const k = n / 1000;
    return (Math.abs(k) >= 10 || Number.isInteger(k) ? Math.round(k) : Math.round(k * 10) / 10).toString().replace(".", ",") + "K$";
  }
  return Math.round(n).toLocaleString("ru-RU").replace(/,/g, " ") + "$";
}
function int(v) { return Math.round(Number(v || 0)).toLocaleString("ru-RU"); }
function monthLabel(m) { const [y, mm] = m.split("-"); return `${MONTHS[+mm - 1]} ${y.slice(2)}`; }
function dayLabel(iso) { const [, mm, dd] = iso.split("-"); return `${+dd}.${mm}`; }
/** O'q uchun yaxlit qadam: 1/2/5 × 10^k; butun sonli qiymatlarda qadam >= 1. */
function niceScale(v, ticks, integer) {
  if (v <= 0) return { step: 1, max: ticks };
  const raw = v / ticks;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  let step = 10 * p;
  for (const m of [1, 2, 5, 10]) if (m * p >= raw) { step = m * p; break; }
  if (integer) step = Math.max(1, Math.ceil(step));
  const n = Math.max(2, Math.ceil(v / step));   // ortiqcha bo'sh joy qoldirmaslik uchun qadamlar soni moslashadi
  return { step, ticks: n, max: step * n };
}
function token() { try { return localStorage.getItem("mmebel_token") || ""; } catch (_) { return ""; } }

/* ---------- tooltip ---------- */
const tip = document.getElementById("tip");
function showTip(e, lines) {
  while (tip.firstChild) tip.removeChild(tip.firstChild);
  lines.forEach((l, i) => tip.appendChild(i === 0 ? el("b", {}, l) : el("div", {}, l)));
  tip.hidden = false;
  const r = tip.getBoundingClientRect();
  let x = e.clientX + 14, y = e.clientY - r.height - 10;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14;
  if (y < 8) y = e.clientY + 16;
  tip.style.left = x + "px"; tip.style.top = y + "px";
}
function hideTip() { tip.hidden = true; }

/* ---------- grafiklar ---------- */
/** Ustunli grafik: bitta seriya, bitta o'q. data: [{label, value, tip:[...]}] */
function columnChart(host, data, { height = 220, fmt = int, every = 1, integer = false } = {}) {
  const W = Math.max(280, host.clientWidth || 600), H = height;
  const m = { t: 18, r: 8, b: 26, l: 44 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const { max, ticks } = niceScale(Math.max(...data.map((d) => d.value), 0), 4, integer);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" });
  const ax = svg("g", { class: "axis" });
  for (let i = 0; i <= ticks; i++) {
    const v = (max / ticks) * i, y = m.t + ih - (v / max) * ih;
    if (i > 0) s.appendChild(svg("line", { class: "gridline", x1: m.l, x2: W - m.r, y1: y, y2: y }));
    const t = svg("text", { x: m.l - 8, y: y + 4, "text-anchor": "end" }); t.textContent = fmt(v, true); ax.appendChild(t);
  }
  s.appendChild(svg("line", { class: "baseline", x1: m.l, x2: W - m.r, y1: m.t + ih, y2: m.t + ih }));
  const slot = iw / data.length;
  const bw = Math.min(24, Math.max(4, slot - 2));          // ustun <= 24px, qo'shnilar orasida havo
  const maxIdx = data.reduce((bi, d, i) => (d.value > data[bi].value ? i : bi), 0);
  data.forEach((d, i) => {
    const x = m.l + slot * i + (slot - bw) / 2;
    const h = (d.value / max) * ih, y = m.t + ih - h;
    const r = Math.min(4, h);
    if (h > 0) {
      // yuqori uchi 4px yumaloq, asosda to'g'ri
      s.appendChild(svg("path", { class: "bar", d: `M${x},${m.t + ih} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${m.t + ih} Z` }));
    }
    if ((i === data.length - 1 || i === maxIdx) && d.value > 0) {   // tanlab qo'yilgan qiymat yorliqlari
      const t = svg("text", { class: "val", x: x + bw / 2, y: y - 6, "text-anchor": "middle" }); t.textContent = fmt(d.value, true); s.appendChild(t);
    }
    if (i % every === 0 || i === data.length - 1) {
      const t = svg("text", { x: x + bw / 2, y: H - 8, "text-anchor": "middle" }); t.textContent = d.label; ax.appendChild(t);
    }
    const hit = svg("rect", { class: "hit", x: m.l + slot * i, y: m.t, width: slot, height: ih });
    hit.addEventListener("mousemove", (e) => showTip(e, d.tip));
    hit.addEventListener("mouseleave", hideTip);
    s.appendChild(hit);
  });
  s.appendChild(ax);
  host.replaceChildren(s);
}

/** Gorizontal ustunlar ro'yxati (nom — chiziq — qiymat). Matn rangi doim matn tokeni. */
function hbars(host, rows, fmt = int) {
  const max = Math.max(...rows.map((r) => r.value), 1);
  host.replaceChildren(el("div", { class: "hbars" }, rows.map((r) =>
    el("div", { class: "hbar", on: { mousemove: (e) => showTip(e, [r.name, fmt(r.value)]), mouseleave: hideTip } },
      el("span", { class: "name" }, r.swatch ? el("span", { class: "sw " + r.swatch }) : null, r.name),
      el("span", { class: "track" }, el("span", { class: "fill", style: `width:${Math.max(1, (r.value / max) * 100)}%;${r.color ? "background:" + r.color : ""}` })),
      el("span", { class: "num" }, fmt(r.value))))));
}

function table(head, rows) {
  return el("table", { class: "list-tbl" },
    el("thead", {}, el("tr", {}, head.map((h, i) => el("th", { style: i === head.length - 1 ? "text-align:right" : "" }, h)))),
    el("tbody", {}, rows.map((r) => el("tr", {}, r))));
}

/* ---------- kartochkalar ---------- */
function card(span, title, sub, body, tableFn) {
  const bodyBox = el("div", { class: "chart" });
  let showTable = false;
  const toggle = tableFn ? el("button", { class: "tbl-toggle", type: "button" }, "Jadval") : null;
  const draw = () => {
    if (showTable) bodyBox.replaceChildren(tableFn());
    else body(bodyBox);
    if (toggle) toggle.textContent = showTable ? "Grafik" : "Jadval";
  };
  if (toggle) toggle.addEventListener("click", () => { showTable = !showTable; draw(); });
  const c = el("section", { class: `card ${span}` },
    el("div", { class: "card-head" }, el("div", {}, el("h2", {}, title), sub ? el("div", { class: "sub" }, sub) : null), toggle),
    bodyBox);
  c._draw = draw;
  return c;
}
function kpi(span, label, value, opts = {}) {
  const v = el("div", { class: "value" }, value);
  return el("section", { class: `card kpi ${span}${opts.alert ? " alert" : ""}` },
    el("div", { class: "label" }, label), opts.href ? el("a", { href: opts.href }, v) : v);
}

function render() {
  const d = DATA, s = d.stats;
  const grid = document.getElementById("grid");
  const cur = d.revenue[d.revenue.length - 1];
  const cards = [
    el("section", { class: "card hero span-4" },
      el("div", { class: "label" }, `Shu oy buyurtmalar summasi · ${monthLabel(cur.month)}`),
      el("div", { class: "value" }, money(cur.revenue)),
      el("div", { class: "note" }, `${int(cur.orders)} ta mebel buyurtma qilindi`)),
    kpi("span-2", "Faol buyurtmalar", int(s.active)),
    kpi("span-2", "Muddati o'tgan", int(s.overdue), { alert: s.overdue > 0 }),
    kpi("span-2", "Bugun topshirish", int(s.due_today)),
    kpi("span-2", `Dillerlar qarzi · ${s.debtors} ta`, money(s.debt_total, true)),
  ];
  const second = [
    kpi("span-3", "Tayyor, yetkazilmagan", int(s.ready)),
    kpi("span-3", "Shu oy yetkazildi", int(s.delivered_month)),
    kpi("span-3", `Omborda · ${s.products} xil`, int(s.stock_total) + " ta"),
    kpi("span-3", "Tasdiqlanmagan to'lovlar", int(s.pending_payments), { alert: s.pending_payments > 0 }),
  ];

  const revCard = card("span-8", "Oylik buyurtmalar summasi", "So'nggi 12 oy, bekor qilinganlarsiz",
    (h) => columnChart(h, d.revenue.map((r) => ({ label: monthLabel(r.month), value: r.revenue,
      tip: [monthLabel(r.month), money(r.revenue), `${int(r.orders)} ta mebel`] })), { fmt: money }),
    () => table(["Oy", "Mebel", "Summa"], d.revenue.slice().reverse().map((r) =>
      [el("td", {}, monthLabel(r.month)), el("td", { class: "n" }, int(r.orders)), el("td", { class: "n" }, money(r.revenue))])));

  const statusColors = { prep: "var(--st-prep-c)", ready: "var(--st-ready-c)", late: "var(--st-late-c)" };
  const stCard = card("span-4", "Faol buyurtmalar holati", `Jami ${int(s.active)} ta`,
    (h) => hbars(h, d.status.map((x) => ({ name: x.label, value: x.count, swatch: "st-" + x.key, color: statusColors[x.key] }))),
    null);

  const delCard = card("span-8", "Yetkazib berishlar", "So'nggi 30 kun, kunlar bo'yicha",
    (h) => columnChart(h, d.deliveries.map((x) => ({ label: dayLabel(x.date), value: x.count,
      tip: [dayLabel(x.date), `${int(x.count)} ta yetkazish`, `${int(x.items)} ta mebel`] })), { height: 200, every: 3, integer: true }),
    () => table(["Kun", "Yetkazish", "Mebel"], d.deliveries.slice().reverse().filter((x) => x.count).map((x) =>
      [el("td", {}, dayLabel(x.date)), el("td", { class: "n" }, int(x.count)), el("td", { class: "n" }, int(x.items))])));

  const topCard = card("span-4", "Eng ko'p buyurtma qilingan", "Shu oy, mebel soni",
    (h) => d.top_models.length ? hbars(h, d.top_models.map((x) => ({ name: x.product_id, value: x.count })))
      : h.replaceChildren(el("div", { class: "empty-s" }, "Shu oyda buyurtma yo'q.")), null);

  const debtCard = card("span-4", "Eng katta qarzlar", `${s.debtors} ta diller · jami ${money(s.debt_total)}`,
    (h) => d.debts.length ? hbars(h, d.debts.map((x) => ({ name: x.client, value: x.debt })), money)
      : h.replaceChildren(el("div", { class: "empty-s" }, "Qarzdor diller yo'q.")), null);

  const lateCard = el("section", { class: "card span-4" },
    el("div", { class: "card-head" }, el("div", {}, el("h2", {}, "Muddati o'tgan buyurtmalar"),
      el("div", { class: "sub" }, d.overdue.length ? `${d.overdue.length} ta — eng eskisi tepada` : "Kechikkan buyurtma yo'q"))),
    d.overdue.length ? table(["Mebel", "Diller", "Muddat"], d.overdue.map((o) => [
      el("td", { class: "code" }, `${o.product_id} ×${o.amount}`), el("td", {}, o.client), el("td", { class: "n late" }, o.due_date)]))
      : el("div", { class: "empty-s" }, "Hammasi o'z vaqtida."));

  const dueRows = [...d.due_today.map((o) => ({ ...o, when: "Bugun" })), ...d.tomorrow.map((o) => ({ ...o, when: "Ertaga" }))];
  const dueCard = el("section", { class: "card span-4" },
    el("div", { class: "card-head" }, el("div", {}, el("h2", {}, "Bugun va ertaga topshiriladi"),
      el("div", { class: "sub" }, `${d.due_today.length} ta bugun · ${d.tomorrow.length} ta ertaga`))),
    dueRows.length ? table(["Mebel", "Diller", "Qachon"], dueRows.map((o) => [
      el("td", { class: "code" }, `${o.product_id} ×${o.amount}`), el("td", {}, o.client),
      el("td", { class: "n" }, `${o.when} · ${o.status === "Tayyorlanmoqda" ? "tayyorlanmoqda" : "tayyor"}`)]))
      : el("div", { class: "empty-s" }, "Yaqin kunlarda topshiriladigan buyurtma yo'q."));

  const stockCard = el("section", { class: "card span-4" },
    el("div", { class: "card-head" }, el("div", {}, el("h2", {}, "Omborda tugayotganlar"), el("div", { class: "sub" }, "Qoldig'i 1 ta yoki undan kam"))),
    d.low_stock.length ? table(["Mebel", "Qoldiq"], d.low_stock.map((p) => [
      el("td", { class: "code" }, p.name), el("td", { class: "n" + (p.qty <= 0 ? " late" : "") }, `${p.qty} ta`)]))
      : el("div", { class: "empty-s" }, "Hamma mebel yetarli."));

  const recentCard = el("section", { class: "card span-8" },
    el("div", { class: "card-head" }, el("div", {}, el("h2", {}, "So'nggi yetkazishlar"))),
    d.recent.length ? table(["Sana", "Mebel", "Diller", "Haydovchi"], d.recent.map((r) => [
      el("td", {}, r.date), el("td", { class: "code" }, `${r.product_id} ×${r.amount}`), el("td", {}, r.client), el("td", { class: "n" }, r.driver)]))
      : el("div", { class: "empty-s" }, "Hali yetkazish yo'q."));

  const all = [...cards, ...second, revCard, stCard, delCard, topCard, debtCard, lateCard, dueCard, stockCard, recentCard];
  grid.replaceChildren(...all);
  all.forEach((c) => c._draw && c._draw());
  document.getElementById("updated").textContent = `Oxirgi yangilanish: ${d.generated_at} · har daqiqada avtomatik`;
}

/* ---------- ma'lumot ---------- */
function gate(title, text, action) {
  document.getElementById("grid").replaceChildren(el("section", { class: "card span-12 gate" },
    el("h1", {}, title), el("p", { class: "muted" }, text), action || null));
}
async function load() {
  const t = token();
  if (!t) { location.replace("/panel/?next=dashboard"); return; }
  try {
    const res = await fetch("/api/dashboard/full", { headers: { Authorization: "Bearer " + t } });
    if (res.status === 401) { location.replace("/panel/?next=dashboard"); return; }
    const data = await res.json().catch(() => ({}));
    if (res.status === 403) {
      const relogin = el("button", { class: "btn", type: "button", on: { click: async () => {
        try { await fetch("/api/logout", { method: "POST", headers: { Authorization: "Bearer " + t } }); } catch (_) { /* baribir */ }
        try { localStorage.removeItem("mmebel_token"); } catch (_) { /* yo'q */ }
        location.replace("/panel/?next=dashboard");
      } } }, "Boshqa akkaunt bilan kirish");
      gate("Ruxsat yo'q", "Dashboard faqat admin uchun. Siz admin bo'lmagan akkaunt bilan kirgansiz — Telegram'da admin akkauntni tanlab, qayta kiring.",
        el("div", { class: "actions two", style: "max-width:520px;margin:0 auto" }, relogin, el("a", { class: "btn ghost", href: "/panel/", style: "text-align:center;text-decoration:none" }, "Panelga qaytish")));
      return;
    }
    if (!res.ok) throw new Error(data.error || `Xato (${res.status})`);
    DATA = data;
    render();
  } catch (e) {
    document.getElementById("updated").textContent = `Yangilab bo'lmadi: ${e.message} · keyingi urinish 1 daqiqadan so'ng`;
    if (!DATA) gate("Ulanib bo'lmadi", e.message);
  }
}
function schedule() {
  clearInterval(timer);
  timer = setInterval(() => { if (!document.hidden) load(); }, REFRESH_MS);
}

document.getElementById("refresh").addEventListener("click", load);
document.getElementById("fullscreen").addEventListener("click", () => {
  document.body.classList.toggle("tv");
  if (!document.fullscreenElement && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
  else if (document.fullscreenElement) document.exitFullscreen();
});
document.addEventListener("visibilitychange", () => { if (!document.hidden) load(); });
let rt;
addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => DATA && render(), 200); });

load();
schedule();
