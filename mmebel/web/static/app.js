/* MMebel panel — Telegram Mini App (admin, omborchi, xodim).
   Xavfsizlik: barcha ma'lumotlar DOM ga faqat textContent orqali yoziladi (innerHTML yo'q).
   Har bir API so'rovi Telegram imzosi (initData) bilan yuboriladi; server rolni o'zi aniqlaydi. */
"use strict";

const tg = window.Telegram && window.Telegram.WebApp;
const S = { me: null, tab: null, ordersScope: "active", ordersQuery: "", stockQuery: "", moneySeg: "debts",
  moreSeg: "deliveries", month: null };

/* ---------- DOM yordamchilari ---------- */
function el(tag, attrs, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
    else if (k === "style") n.style.cssText = v;
    else n.setAttribute(k, v === true ? "" : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.appendChild(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return n;
}
const $ = (id) => document.getElementById(id);
function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }

/* ---------- formatlash ---------- */
function money(v) {
  const n = Number(v || 0);
  const r = Math.round(n * 100) / 100;
  const s = Number.isInteger(r) ? r.toLocaleString("ru-RU") : r.toLocaleString("ru-RU", { minimumFractionDigits: 2 });
  return s.replace(/,/g, ".") + "$";
}
function parseDate(s) {
  if (!s) return null;
  s = String(s);
  let m = s.match(/^(\d{2})\.(\d{2})\.(\d{4})/);
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(+m[1], +m[2] - 1, +m[3]);
  return null;
}
const MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"];
const DAYS = ["yakshanba", "dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba"];
function fdate(s) {
  const d = parseDate(s);
  if (!d) return s || "—";
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`;
}
function humanDay(s) {
  const d = parseDate(s);
  if (!d) return "Muddatsiz";
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = Math.round((d - today) / 86400000);
  const base = `${d.getDate()} ${MONTHS[d.getMonth()]}, ${DAYS[d.getDay()]}`;
  if (diff === 0) return `Bugun — ${base}`;
  if (diff === 1) return `Ertaga — ${base}`;
  if (diff < 0) return `${base} · ${-diff} kun kechikdi`;
  return base;
}
function isoToday(offset = 0) {
  const d = new Date(); d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function toIso(s) { const d = parseDate(s); return d ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}` : ""; }
const ACTIVE = ["Tayyorlanmoqda", "Tayyor bo'ldi", "Yuborildi"];
function edgeClass(st) {
  if (st === "Tayyorlanmoqda") return "e-prep";
  if (st === "Tayyor bo'ldi" || st === "Yuborildi") return "e-ready";
  if (st === "Bekor qilindi") return "e-cancel";
  return "e-done";
}

/* ---------- tizim ---------- */
function haptic(kind) { try { tg && tg.HapticFeedback.notificationOccurred(kind); } catch (_) { /* yo'q */ } }
let toastTimer;
function toast(msg, err) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const t = el("div", { class: "toast" + (err ? " err" : ""), role: "status" }, msg);
  document.body.appendChild(t);
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.remove(), err ? 4500 : 2500);
  haptic(err ? "error" : "success");
}
function confirmDlg(text) {
  return new Promise((resolve) => {
    if (tg && tg.showConfirm && tg.isVersionAtLeast && tg.isVersionAtLeast("6.2")) tg.showConfirm(text, (ok) => resolve(!!ok));
    else resolve(window.confirm(text));
  });
}

async function api(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: { "Authorization": "tma " + (tg ? tg.initData : ""), "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* bo'sh javob */ }
  if (!res.ok) throw new Error(data.error || `Xato (${res.status})`);
  return data;
}
async function act(btn, fn, okMsg) {
  if (btn) btn.disabled = true;
  try { const r = await fn(); if (okMsg) toast(okMsg); return r; }
  catch (e) { toast(e.message, true); return null; }
  finally { if (btn) btn.disabled = false; }
}

/* ---------- sheet (pastdan chiquvchi oyna) ---------- */
let sheetStack = [];
function sheet(build) {
  const box = el("div", { class: "sheet", role: "dialog", "aria-modal": "true" }, el("div", { class: "grab" }));
  const scrim = el("div", { class: "scrim", on: { click: (e) => { if (e.target === scrim) close(); } } }, box);
  function close() { scrim.remove(); sheetStack = sheetStack.filter((s) => s !== close); syncBack(); }
  box.appendChild(build(close));
  document.body.appendChild(scrim);
  sheetStack.push(close);
  syncBack();
  const first = box.querySelector("input,select,textarea");
  if (first && first.dataset.autofocus !== undefined) first.focus();
  return close;
}
function syncBack() {
  if (!tg || !tg.BackButton) return;
  if (sheetStack.length) tg.BackButton.show(); else tg.BackButton.hide();
}
if (tg && tg.BackButton) tg.BackButton.onClick(() => { const c = sheetStack[sheetStack.length - 1]; if (c) c(); });

function field(label, input) { return el("label", { class: "field" }, el("span", {}, label), input); }
function chips(values, current, onPick, fmt) {
  const wrap = el("div", { class: "chips" });
  values.forEach((v) => {
    const b = el("button", { type: "button", "aria-pressed": String(v === current) }, fmt ? fmt(v) : v);
    b.addEventListener("click", () => {
      wrap.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", "false"));
      b.setAttribute("aria-pressed", "true");
      onPick(v);
    });
    wrap.appendChild(b);
  });
  return wrap;
}
function seg(options, current, onPick) {
  return el("div", { class: "seg", role: "tablist" }, options.map(([key, label]) =>
    el("button", { type: "button", role: "tab", "aria-pressed": String(key === current), on: { click: () => onPick(key) } }, label)));
}
function empty(text) { return el("div", { class: "empty" }, text); }
function loading() { return el("div", { class: "empty" }, "Yuklanmoqda…"); }

/* ---------- tablar ---------- */
const TABS = {
  admin: [["home", "🏠", "Asosiy"], ["orders", "📋", "Buyurtmalar"], ["stock", "📦", "Ombor"], ["money", "💳", "Moliya"], ["more", "☰", "Boshqa"]],
  omborchi: [["home", "🏠", "Asosiy"], ["orders", "📋", "Buyurtmalar"], ["stock", "📦", "Ombor"], ["deliveries", "🚚", "Yetkazish"]],
  xodim: [["plan", "🔨", "Ishlab chiqarish"], ["orders", "📋", "Buyurtmalar"]],
};
const TITLES = { home: "Asosiy", orders: "Buyurtmalar", stock: "Ombor", money: "Moliya", more: "Boshqa",
  deliveries: "Yetkazishlar", plan: "Ishlab chiqarish" };

function renderTabs() {
  const nav = clear($("tabs"));
  TABS[S.me.role].forEach(([key, ic, label]) => {
    nav.appendChild(el("button", { type: "button", "aria-current": S.tab === key ? "page" : null,
      on: { click: () => go(key) } }, el("span", { class: "ic", "aria-hidden": "true" }, ic), label));
  });
  nav.classList.remove("hidden");
}
function go(tab) {
  S.tab = tab;
  renderTabs();
  $("title").textContent = TITLES[tab];
  clear($("toolbar"));
  document.querySelectorAll(".fab").forEach((f) => f.remove());
  const view = clear($("view"));
  view.appendChild(loading());
  window.scrollTo(0, 0);
  const fn = { home: viewHome, orders: viewOrders, stock: viewStock, money: viewMoney, more: viewMore,
    deliveries: viewDeliveries, plan: viewPlan }[tab];
  fn().catch((e) => { clear(view).appendChild(empty(e.message)); });
}
function refresh() { go(S.tab); }
function fab(label, onClick) {
  document.querySelectorAll(".fab").forEach((f) => f.remove());
  document.body.appendChild(el("button", { class: "btn fab", type: "button", on: { click: onClick } }, label));
}

/* ================= ASOSIY ================= */
async function viewHome() {
  const isAdmin = S.me.role === "admin";
  const [d, pay] = await Promise.all([api("GET", "/api/dashboard"), isAdmin ? api("GET", "/api/payments") : null]);
  const view = clear($("view"));
  const stat = (num, label, onClick, cls) => el("button", { class: "stat " + (cls || ""), type: "button", on: { click: onClick } },
    el("b", {}, num), el("span", {}, label));
  const toOrders = (scope) => () => { S.ordersScope = scope; go("orders"); };
  view.appendChild(el("div", { class: "stats" },
    stat(d.overdue, "Muddati o'tgan", toOrders("overdue"), d.overdue ? "late" : ""),
    stat(d.due_today, "Bugun topshirish", toOrders("active")),
    stat(d.preparing, "Tayyorlanmoqda", toOrders("active")),
    stat(d.ready, "Tayyor, yetkazilmagan", toOrders("active")),
    stat(d.due_tomorrow, "Ertaga topshirish", toOrders("active")),
    stat(d.delivered_month, "Shu oy yetkazildi", toOrders("done")),
    isAdmin ? stat(money(d.revenue_month), `Shu oy buyurtmalar (${d.orders_month} ta)`, () => { S.moreSeg = "sales"; go("more"); }, "wide") : null,
    stat(d.stock_total, `Omborda jami (${d.products} xil)`, () => go("stock"), "wide"),
  ));
  if (isAdmin) {
    view.appendChild(el("div", { class: "section-title" }, pay.items.length ? `Tasdiqlanmagan to'lovlar (${pay.items.length})` : "Tasdiqlanmagan to'lov yo'q"));
    if (pay.items.length) view.appendChild(paymentsList(pay.items));
    fab("＋ Yangi buyurtma", newOrderSheet);
  }
}

/* ================= BUYURTMALAR ================= */
async function viewOrders() {
  const role = S.me.role;
  const tb = $("toolbar");
  if (role !== "xodim") {
    tb.appendChild(seg([["active", "Faol"], ["overdue", "Muddati o'tgan"], ["done", "Yetkazilgan"], ["cancelled", "Bekor"]],
      S.ordersScope, (k) => { S.ordersScope = k; refresh(); }));
  }
  const search = el("input", { class: "search", type: "search", placeholder: "Qidirish: diller, mebel, ID", value: S.ordersQuery });
  tb.appendChild(search);
  const scope = role === "xodim" ? "active" : S.ordersScope;
  const data = await api("GET", `/api/orders?scope=${scope}`);
  const view = clear($("view"));
  const box = el("div");
  view.appendChild(box);
  const draw = () => {
    const q = search.value.trim().toLowerCase();
    S.ordersQuery = search.value;
    const items = data.items.filter((o) => !q || `${o.client_name} ${o.product_id} ${o.id} ${o.comment || ""}`.toLowerCase().includes(q));
    clear(box);
    if (!items.length) { box.appendChild(empty(q ? "Hech narsa topilmadi." : "Bu ro'yxatda buyurtma yo'q.")); return; }
    if (scope === "active" || scope === "overdue") {
      let lastDay = null;
      items.forEach((o) => {
        const day = fdate(o.due_date);
        if (day !== lastDay) {
          box.appendChild(el("div", { class: "day" + (o.overdue ? " late" : "") }, humanDay(o.due_date)));
          lastDay = day;
        }
        box.appendChild(orderCard(o));
      });
    } else {
      items.forEach((o) => box.appendChild(orderCard(o, true)));
    }
    if (data.total > data.items.length) box.appendChild(el("p", { class: "muted small" }, `Oxirgi ${data.items.length} ta ko'rsatildi.`));
  };
  search.addEventListener("input", draw);
  draw();
  if (role === "admin") fab("＋ Yangi buyurtma", newOrderSheet);
}

function orderCard(o, showStatus) {
  return el("button", { type: "button", class: `order ${edgeClass(o.status)}${o.overdue ? " late" : ""}`, on: { click: () => orderSheet(o.id) } },
    el("div", {}, el("span", { class: "code" }, o.product_id), el("span", { class: "qty" }, `× ${o.amount}`),
      o.status !== "Tayyorlanmoqda" || showStatus ? el("span", { style: "margin-left:8px" }, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status)) : null),
    el("div", { class: "line2" }, el("span", { class: "client" }, o.client_name || "—"),
      el("span", { class: "due" }, showStatus ? fdate(o.delivered_at || o.created_at) : fdate(o.due_date))),
    o.comment && !["yoq", "yo'q", "-"].includes(String(o.comment).toLowerCase()) ? el("div", { class: "note" }, "📝 " + o.comment) : null,
  );
}

async function orderSheet(id) {
  let o;
  try { o = await api("GET", `/api/orders/${encodeURIComponent(id)}`); } catch (e) { toast(e.message, true); return; }
  const role = S.me.role;
  sheet((close) => {
    const isActive = ACTIVE.includes(o.status);
    const kv = el("dl", { class: "kv" },
      el("dt", {}, "Diller"), el("dd", {}, o.client_name || "—"),
      el("dt", {}, "Soni"), el("dd", {}, `${o.amount} ta`),
      el("dt", {}, "Muddat"), el("dd", { class: o.overdue ? "pos" : "" }, `${fdate(o.due_date)}${o.overdue ? " (kechikkan)" : ""}`),
      el("dt", {}, "Holati"), el("dd", {}, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status)),
      o.comment ? [el("dt", {}, "Izoh"), el("dd", {}, o.comment)] : null,
      role === "admin" && o.total_price ? [el("dt", {}, "Narxi"), el("dd", {}, `${money(o.price)} × ${o.amount} = ${money(o.total_price)}`)] : null,
      o.driver ? [el("dt", {}, "Haydovchi"), el("dd", {}, `${o.driver}${o.delivery_price ? " · " + o.delivery_price : ""}`)] : null,
      o.delivered_at ? [el("dt", {}, "Yetkazilgan"), el("dd", {}, fdate(o.delivered_at))] : null,
      el("dt", {}, "Yaratilgan"), el("dd", {}, fdate(o.created_at)),
      el("dt", {}, "ID"), el("dd", { class: "small muted" }, o.id),
    );
    const actions = el("div", { class: "actions" });
    const done = () => { close(); refresh(); };
    if (isActive && (role === "admin" || role === "omborchi")) {
      if (o.status !== "Tayyor bo'ldi") {
        actions.appendChild(el("button", { class: "btn", type: "button", on: { click: (e) =>
          act(e.target, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/ready`), "Tayyor bo'ldi deb belgilandi").then((r) => r && done()) } }, "✅ Tayyor bo'ldi"));
      } else {
        actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: (e) =>
          act(e.target, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/unready`), "Tayyorlanmoqda holatiga qaytarildi").then((r) => r && done()) } }, "↩️ Hali tayyor emas"));
      }
      actions.appendChild(el("div", { class: "actions two", style: "margin-top:0" },
        el("button", { class: "btn", type: "button", on: { click: () => deliverSheet(o, false, done) } }, "🚚 Yetkazildi"),
        el("button", { class: "btn", type: "button", on: { click: () => deliverSheet(o, true, done) } }, "🏠 O'zi olib ketdi")));
      if (role === "admin") actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => editOrderSheet(o, done) } }, "✏️ O'zgartirish"));
      actions.appendChild(el("button", { class: "btn danger", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(`${o.product_id} × ${o.amount} (${o.client_name}) bekor qilinsinmi? Ombordan ayirilgani qaytariladi.`))) return;
        const r = await act(e.target, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/cancel`), "Buyurtma bekor qilindi");
        if (r) done();
      } } }, "Buyurtmani bekor qilish"));
    }
    return el("div", {}, el("div", { class: "code-big" }, `${o.product_id} × ${o.amount}`), kv, actions);
  });
}

function deliverSheet(o, pickup, onDone) {
  const m = S.me.meta;
  let driver = pickup ? m.self_pickup : null;
  let price = null;
  sheet((close) => {
    const customDriver = el("input", { type: "text", maxlength: "40", placeholder: "Boshqa haydovchi ismi" });
    const priceInput = el("input", { type: "number", inputmode: "decimal", min: "0", step: "0.5", placeholder: "Summa, $" });
    const presets = pickup ? m.pickup_discounts : m.delivery_prices;
    const btn = el("button", { class: "btn", type: "button" }, pickup ? "Olib ketildi deb saqlash" : "Yetkazildi deb saqlash");
    btn.addEventListener("click", async () => {
      const d = pickup ? driver : (customDriver.value.trim() || driver);
      const p = priceInput.value !== "" ? Number(priceInput.value) : price;
      if (!d) { toast("Haydovchini tanlang.", true); return; }
      if (p === null || isNaN(p) || p < 0) { toast(pickup ? "Chegirma summasini tanlang." : "Dostavka narxini tanlang.", true); return; }
      const r = await act(btn, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/deliver`, { driver: d, price: p }),
        pickup ? "Olib ketildi" : "Yetkazildi");
      if (r) { close(); onDone(); }
    });
    return el("div", {},
      el("h2", {}, pickup ? "Diller o'zi olib ketdi" : "Biz yetkazib berdik"),
      el("p", { class: "muted small" }, `${o.product_id} × ${o.amount} · ${o.client_name}`),
      pickup ? null : field("Haydovchi", el("div", {}, chips(m.drivers, null, (v) => { driver = v; customDriver.value = ""; }), customDriver)),
      field(pickup ? "Chegirma ($) — qarzdan ayiriladi" : "Dostavka narxi ($) — haydovchi balansiga yoziladi",
        el("div", {}, chips(presets, null, (v) => { price = Number(v); priceInput.value = ""; }, (v) => `${v}$`), priceInput)),
      el("div", { class: "actions" }, btn));
  });
}

function editOrderSheet(o, onDone) {
  sheet((close) => {
    const amount = el("input", { type: "number", min: "1", max: "10000", value: o.amount, inputmode: "numeric" });
    const due = el("input", { type: "date", value: toIso(o.due_date), min: isoToday() });
    const comment = el("textarea", { maxlength: "500" }, o.comment || "");
    const btn = el("button", { class: "btn", type: "button" }, "O'zgarishlarni saqlash");
    btn.addEventListener("click", async () => {
      const body = {};
      if (Number(amount.value) !== Number(o.amount)) body.amount = Number(amount.value);
      if (due.value && due.value !== toIso(o.due_date)) body.due_date = due.value;
      if (comment.value !== (o.comment || "")) body.comment = comment.value;
      if (!Object.keys(body).length) { close(); return; }
      const r = await act(btn, () => api("PATCH", `/api/orders/${encodeURIComponent(o.id)}`, body), "Saqlandi. Dillerga xabar yuborildi.");
      if (r) { close(); onDone(); }
    });
    return el("div", {}, el("h2", {}, `${o.product_id} — o'zgartirish`),
      field("Soni", amount), field("Muddat", due), field("Izoh", comment),
      el("p", { class: "muted small" }, "Soni o'zgarsa, ombor qoldig'i avtomatik to'g'rilanadi."),
      el("div", { class: "actions" }, btn));
  });
}

function newOrderSheet() {
  const m = S.me.meta;
  sheet((close) => {
    const clientSel = el("select", {}, el("option", { value: "" }, "— Dillerni tanlang —"),
      m.clients.map((c) => el("option", { value: c }, c)), el("option", { value: "__new" }, "+ Yangi diller"));
    const newClient = el("input", { type: "text", maxlength: "60", placeholder: "Yangi diller nomi", class: "hidden" });
    clientSel.addEventListener("change", () => newClient.classList.toggle("hidden", clientSel.value !== "__new"));
    const product = el("input", { type: "text", list: "models-dl", maxlength: "40", placeholder: "Masalan: BF 07" });
    const dl = el("datalist", { id: "models-dl" }, m.models.map((x) => el("option", { value: x })));
    const amount = el("input", { type: "number", min: "1", max: "10000", value: "1", inputmode: "numeric" });
    const price = el("input", { type: "number", min: "0", step: "0.5", inputmode: "decimal", placeholder: "Bo'sh qoldirsangiz — ombordagi narx" });
    const due = el("input", { type: "date", value: isoToday(2), min: isoToday() });
    const comment = el("textarea", { maxlength: "500", placeholder: "Masalan: rangi oq, eshigi oynali" });
    const btn = el("button", { class: "btn", type: "button" }, "Buyurtmani yaratish");
    btn.addEventListener("click", async () => {
      const isNew = clientSel.value === "__new";
      const client = isNew ? newClient.value.trim() : clientSel.value;
      if (!client) { toast("Dillerni tanlang.", true); return; }
      if (!product.value.trim()) { toast("Mebelni kiriting.", true); return; }
      const body = { client_name: client, product: product.value.trim(), amount: Number(amount.value), due_date: due.value,
        comment: comment.value, new_client: isNew };
      if (price.value !== "") body.price = Number(price.value);
      const r = await act(btn, () => api("POST", "/api/orders", body), "Buyurtma yaratildi");
      if (r) { close(); S.ordersScope = "active"; go("orders"); }
    });
    return el("div", {}, el("h2", {}, "Yangi buyurtma"),
      field("Diller", el("div", {}, clientSel, newClient)), field("Mebel", el("div", {}, product, dl)),
      el("div", { class: "actions two", style: "margin-top:0" }, field("Soni", amount), field("Muddat", due)),
      field("1 dona narxi ($)", price), field("Izoh", comment), el("div", { class: "actions" }, btn));
  });
}

/* ================= ISHLAB CHIQARISH (xodim) ================= */
async function viewPlan() {
  const [plan, d] = await Promise.all([api("GET", "/api/production"), api("GET", "/api/dashboard")]);
  const view = clear($("view"));
  view.appendChild(el("div", { class: "stats" },
    el("div", { class: "stat" + (d.overdue ? " late" : "") }, el("b", {}, d.overdue), el("span", {}, "Muddati o'tgan")),
    el("div", { class: "stat" }, el("b", {}, d.due_today), el("span", {}, "Bugun topshirish"))));
  view.appendChild(el("div", { class: "section-title" }, "Tayyorlanishi kerak — modellar bo'yicha"));
  if (!plan.items.length) { view.appendChild(empty("Hozircha tayyorlanadigan buyurtma yo'q.")); return; }
  plan.items.forEach((p) => view.appendChild(el("div", { class: "plan" },
    el("div", { class: "code" }, p.product_id), el("div", { class: "count" }, `${p.count} ta`),
    el("div", { class: "meta" }, `${p.orders} ta buyurtma · eng yaqin muddat ${p.nearest || "—"}`,
      p.overdue ? el("span", { class: "pos" }, ` · ${p.overdue} ta kechikkan`) : null))));
}

/* ================= OMBOR ================= */
async function viewStock() {
  const role = S.me.role;
  const search = el("input", { class: "search", type: "search", placeholder: "Qidirish: mebel nomi", value: S.stockQuery });
  $("toolbar").appendChild(search);
  const data = await api("GET", "/api/products");
  const view = clear($("view"));
  const list = el("div", { class: "list" });
  view.appendChild(list);
  const draw = () => {
    S.stockQuery = search.value;
    const q = search.value.trim().toLowerCase();
    const items = data.items.filter((p) => !q || `${p.name} ${p.model} ${p.id}`.toLowerCase().includes(q));
    clear(list);
    if (!items.length) { list.appendChild(empty("Mebel topilmadi.")); return; }
    items.forEach((p) => list.appendChild(el("button", { class: "row", type: "button", on: { click: () => productSheet(p) } },
      el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, p.name), el("div", { class: "sub" }, [p.model, role === "admin" && p.price ? money(p.price) : null].filter(Boolean).join(" · ") || " ")),
      el("div", { class: "end" }, el("b", { class: p.qty > 0 ? "" : "muted" }, `${p.qty} ta`)))));
  };
  search.addEventListener("input", draw);
  draw();
  fab("＋ Mebel qo'shish", () => productForm(null));
}

function productSheet(p) {
  const role = S.me.role;
  sheet((close) => {
    const qty = el("input", { type: "number", min: "0", max: "100000", value: p.qty, inputmode: "numeric" });
    const step = (d) => { qty.value = Math.max(0, Number(qty.value || 0) + d); };
    const saveQty = el("button", { class: "btn", type: "button" }, "Qoldiqni saqlash");
    saveQty.addEventListener("click", async () => {
      const r = await act(saveQty, () => api("PUT", `/api/products/${encodeURIComponent(p.id)}/qty`, { qty: Number(qty.value) }), "Qoldiq yangilandi");
      if (r) { close(); refresh(); }
    });
    const parts = [el("h2", {}, p.name), el("p", { class: "muted small" }, p.model || " "),
      field("Ombordagi soni", el("div", { class: "actions", style: "grid-template-columns:auto 1fr auto;margin-top:0" },
        el("button", { class: "btn ghost", type: "button", "aria-label": "Bittaga kamaytirish", on: { click: () => step(-1) } }, "−"),
        qty, el("button", { class: "btn ghost", type: "button", "aria-label": "Bittaga oshirish", on: { click: () => step(1) } }, "+"))),
      el("div", { class: "actions" }, saveQty)];
    if (role === "admin") {
      const price = el("input", { type: "number", min: "0", step: "0.5", value: p.price || "", inputmode: "decimal" });
      const savePrice = el("button", { class: "btn ghost", type: "button" }, "Narxni saqlash");
      savePrice.addEventListener("click", async () => {
        const r = await act(savePrice, () => api("PUT", `/api/products/${encodeURIComponent(p.id)}/price`, { price: Number(price.value) }), "Narx saqlandi");
        if (r) { close(); refresh(); }
      });
      const del = el("button", { class: "btn danger", type: "button" }, "Mebelni o'chirish");
      del.addEventListener("click", async () => {
        if (!(await confirmDlg(`${p.name} ombordan butunlay o'chirilsinmi?`))) return;
        const r = await act(del, () => api("DELETE", `/api/products/${encodeURIComponent(p.id)}`), "O'chirildi");
        if (r) { close(); refresh(); }
      });
      parts.push(field("1 dona narxi ($)", price), el("div", { class: "actions" }, savePrice,
        el("button", { class: "btn ghost", type: "button", on: { click: () => { close(); productForm(p); } } }, "Ma'lumotlarni tahrirlash"), del));
    }
    return el("div", {}, parts);
  });
}

function productForm(p) {
  const role = S.me.role;
  sheet((close) => {
    const name = el("input", { type: "text", list: "models-dl2", maxlength: "60", value: p ? p.name : "", placeholder: "Masalan: BF 07", readonly: p ? true : null });
    const dl = el("datalist", { id: "models-dl2" }, S.me.meta.models.map((x) => el("option", { value: x })));
    const model = el("input", { type: "text", maxlength: "60", value: p ? p.model : "", placeholder: "Masalan: Spalniy" });
    const qty = el("input", { type: "number", min: "0", value: p ? p.qty : "0", inputmode: "numeric" });
    const price = el("input", { type: "number", min: "0", step: "0.5", value: p && p.price ? p.price : "", inputmode: "decimal" });
    const image = el("input", { type: "url", maxlength: "500", value: p ? p.image : "", placeholder: "https://…" });
    const btn = el("button", { class: "btn", type: "button" }, "Saqlash");
    btn.addEventListener("click", async () => {
      if (!name.value.trim()) { toast("Mebel nomini kiriting.", true); return; }
      const body = { name: name.value.trim(), model: model.value, qty: Number(qty.value || 0), image: image.value.trim() };
      if (role === "admin" && price.value !== "") body.price = Number(price.value);
      const r = await act(btn, () => api("POST", "/api/products", body), "Mebel saqlandi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, p ? "Mebelni tahrirlash" : "Yangi mebel"),
      field("Nomi", el("div", {}, name, dl)), field("Modeli / turi", model), field("Omborda soni", qty),
      role === "admin" ? field("1 dona narxi ($)", price) : null, field("Rasm manzili (ixtiyoriy)", image),
      el("div", { class: "actions" }, btn));
  });
}

/* ================= YETKAZISHLAR ================= */
async function viewDeliveries(target) {
  const months = S.me.meta.months;
  S.month = S.month || months[0];
  const holder = target || $("view");
  const tb = target ? null : $("toolbar");
  const picker = seg(months.slice(0, 6).map((m) => [m, m]), S.month, (m) => { S.month = m; target ? viewMoreSection() : refresh(); });
  if (tb) tb.appendChild(picker);
  const data = await api("GET", `/api/deliveries?month=${S.month}`);
  clear(holder);
  if (target) holder.appendChild(picker);
  const t = data.totals.total;
  holder.appendChild(el("div", { class: "stats", style: "margin-top:8px" },
    el("div", { class: "stat" }, el("b", {}, t.count), el("span", {}, "Yetkazish")),
    el("div", { class: "stat" }, el("b", {}, t.items), el("span", {}, "Mebel")),
    el("div", { class: "stat wide" }, el("b", {}, money(t.sum)), el("span", {}, "Dostavka va chegirmalar jami"))));
  if (data.totals.drivers.length) {
    holder.appendChild(el("div", { class: "section-title" }, "Haydovchilar"));
    holder.appendChild(el("div", { class: "list" }, data.totals.drivers.map((d) => el("div", { class: "row" },
      el("div", { class: "grow" }, d.driver), el("div", { class: "end" }, `${d.count} ta · ${money(d.sum)}`)))));
  }
  holder.appendChild(el("div", { class: "section-title" }, "Ro'yxat"));
  if (!data.items.length) { holder.appendChild(empty("Bu oyda yetkazish yo'q.")); return; }
  holder.appendChild(el("div", { class: "list" }, data.items.map((r) => el("div", { class: "row" },
    el("div", { class: "grow" }, el("div", {}, el("b", {}, r.product_id), ` × ${r.amount || 1} — ${r.client || "—"}`),
      el("div", { class: "sub" }, `${r.driver || "—"} · ${r.price || "0"}${r.comment ? " · " + r.comment : ""}`)),
    el("div", { class: "end small muted" }, fdate(r.timestamp))))));
}

/* ================= MOLIYA (admin) ================= */
async function viewMoney() {
  $("toolbar").appendChild(seg([["debts", "Qarzlar"], ["payments", "To'lovlar"], ["drivers", "Haydovchilar"]], S.moneySeg,
    (k) => { S.moneySeg = k; refresh(); }));
  const view = clear($("view"));
  if (S.moneySeg === "debts") {
    const data = await api("GET", "/api/debts");
    const total = data.items.filter((r) => r.debt > 0).reduce((s, r) => s + r.debt, 0);
    view.appendChild(el("div", { class: "stats" }, el("div", { class: "stat wide" }, el("b", {}, money(total)), el("span", {}, "Dillerlarning jami qarzi"))));
    view.appendChild(el("div", { class: "section-title" }, "Dillerlar"));
    const shown = data.items.filter((r) => r.debt !== 0 || r.unsettled || r.pending);
    if (!shown.length) view.appendChild(empty("Hech bir dillerda qarz yoki faol buyurtma yo'q."));
    view.appendChild(el("div", { class: "list" }, shown.map((r) => el("button", { class: "row", type: "button", on: { click: () => accountSheet(r.client) } },
      el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, r.client),
        el("div", { class: "sub" }, `${r.unsettled} ta to'lanmagan · ${r.pending} ta tayyorlanmoqda`)),
      el("div", { class: "end " + (r.debt > 0 ? "pos" : r.debt < 0 ? "neg" : "muted") }, money(r.debt))))));
  } else if (S.moneySeg === "payments") {
    const data = await api("GET", "/api/payments");
    view.appendChild(data.items.length ? paymentsList(data.items) : empty("Tasdiqlanmagan to'lov yo'q."));
  } else {
    const data = await api("GET", "/api/drivers");
    view.appendChild(el("p", { class: "muted small", style: "margin:6px 4px" }, "Musbat balans — biz haydovchiga qarzdormiz. Yetkazish haqi avtomatik qo'shiladi."));
    view.appendChild(el("div", { class: "list" }, data.items.map((d) => el("button", { class: "row", type: "button", on: { click: () => driverSheet(d.driver) } },
      el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, d.driver), el("div", { class: "sub" }, `${data.month}: ${d.month_count} ta · ${money(d.month_sum)}`)),
      el("div", { class: "end" }, el("b", {}, money(d.balance)))))));
  }
}

function paymentsList(items) {
  return el("div", { class: "list" }, items.map((p) => {
    const row = el("div", { class: "row", style: "flex-wrap:wrap" },
      el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, `${p.client_name} — ${money(p.amount)}`),
        el("div", { class: "sub" }, `${p.diller_name} · ${fdate(p.timestamp)}`)));
    const resolve = (approve) => async (e) => {
      if (!(await confirmDlg(`${p.client_name}: ${money(p.amount)} ${approve ? "tasdiqlansinmi" : "rad etilsinmi"}?`))) return;
      const r = await act(e.target, () => api("POST", `/api/payments/${encodeURIComponent(p.pay_id)}/resolve`, { approve }),
        approve ? "To'lov tasdiqlandi" : "To'lov rad etildi");
      if (r) refresh();
    };
    row.appendChild(el("div", { class: "actions two", style: "width:100%;margin-top:6px" },
      el("button", { class: "btn", type: "button", on: { click: resolve(true) } }, "Tasdiqlash"),
      el("button", { class: "btn danger", type: "button", on: { click: resolve(false) } }, "Rad etish")));
    return row;
  }));
}

async function accountSheet(client) {
  let a;
  try { a = await api("GET", `/api/accounts/${encodeURIComponent(client)}`); } catch (e) { toast(e.message, true); return; }
  sheet((close) => {
    const reopen = () => { close(); accountSheet(client); };
    const box = el("div", {}, el("h2", {}, client),
      el("div", { class: "code-big " + (a.debt > 0 ? "pos" : a.debt < 0 ? "neg" : "") }, money(a.debt)),
      el("p", { class: "muted small" }, a.debt < 0 ? "Diller oldindan to'lagan (ortiqcha to'lov)." :
        a.partial_total ? `Qisman to'lovlar hisobga olingan: −${money(a.partial_total)}` : "Joriy qarz"));
    const payBtn = el("button", { class: "btn", type: "button", on: { click: () => partialSheet(client, null, reopen) } }, "💵 To'lov qabul qilish");
    const actions = el("div", { class: "actions" }, payBtn);
    if (a.unsettled.length) {
      actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(`${client}: ${a.unsettled.length} ta buyurtma va ${money(a.debt)} qarz to'liq to'landi deb belgilansinmi?`))) return;
        const r = await act(e.target, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/settle_all`), "Hammasi hisob-kitob qilindi");
        if (r) { reopen(); }
      } } }, "💳 Barchasi to'landi"));
    }
    box.appendChild(actions);
    box.appendChild(el("div", { class: "section-title" }, `To'lanmagan (yetkazilgan) — ${a.unsettled.length} ta`));
    if (!a.unsettled.length) box.appendChild(empty("Hammasi to'langan."));
    else box.appendChild(el("div", { class: "list" }, a.unsettled.map((r) => {
      const left = Math.max(0, r.net - r.paid_partial);
      const row = el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("div", {}, el("b", {}, r.product_id), ` × ${r.amount}`),
          el("div", { class: "sub" }, `${fdate(r.delivered_at)} · ${money(r.gross)}${r.discount ? " − " + money(r.discount) + " chegirma" : ""}${r.paid_partial ? " − " + money(r.paid_partial) + " to'langan" : ""}`)),
        el("div", { class: "end" }, el("b", {}, money(left))));
      row.appendChild(el("div", { class: "actions two", style: "width:100%;margin-top:6px" },
        el("button", { class: "btn", type: "button", on: { click: async (e) => {
          const res = await act(e.target, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/settle`, { order_id: r.order_id }), "To'landi deb belgilandi");
          if (res) reopen();
        } } }, "To'landi"),
        el("button", { class: "btn ghost", type: "button", on: { click: () => partialSheet(client, r, reopen) } }, "Qisman")));
      return row;
    })));
    if (a.pending.length) {
      box.appendChild(el("div", { class: "section-title" }, `Tayyorlanmoqda (qarzga kirmagan) — ${a.pending.length} ta`));
      box.appendChild(el("div", { class: "list" }, a.pending.map((r) => el("div", { class: "row" },
        el("div", { class: "grow" }, el("b", {}, r.product_id), ` × ${r.amount}`, el("div", { class: "sub" }, `${r.status} · ${fdate(r.due_date)}`)),
        el("div", { class: "end" }, money(r.gross))))));
    }
    box.appendChild(el("div", { class: "section-title" }, "Hisob-kitob tarixi"));
    if (!a.history.length) box.appendChild(empty("Tarix bo'sh."));
    else box.appendChild(el("div", { class: "list" }, a.history.slice(0, 60).map((h) => el("div", { class: "row" },
      el("div", { class: "grow" }, h.accounting_type === "toliq" ? `✅ ${h.product_id || ""} × ${h.amount || ""}` : `💰 Qisman to'lov${h.product_id ? " · " + h.product_id : ""}`,
        el("div", { class: "sub" }, `${fdate(h.accounting_date)}${h.note ? " · " + h.note : ""}${h.settled ? " · yopilgan" : ""}`)),
      el("div", { class: "end" }, money(h.accounting_type === "toliq" ? h.total_price : h.partial_payment))))));
    return box;
  });
}

function partialSheet(client, row, onDone) {
  sheet((close) => {
    const amount = el("input", { type: "number", min: "0.01", step: "0.01", inputmode: "decimal", placeholder: "Summa, $", "data-autofocus": "" });
    const note = el("input", { type: "text", maxlength: "200", placeholder: "Izoh (ixtiyoriy)" });
    const btn = el("button", { class: "btn", type: "button" }, "To'lovni saqlash");
    btn.addEventListener("click", async () => {
      const v = Number(amount.value);
      if (!v || v <= 0) { toast("Summani kiriting.", true); return; }
      const r = await act(btn, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/partial`,
        { amount: v, order_id: row ? row.order_id : null, note: note.value }), "To'lov saqlandi");
      if (r) { close(); onDone(); }
    });
    return el("div", {}, el("h2", {}, "To'lov qabul qilish"),
      el("p", { class: "muted small" }, row ? `${client} · ${row.product_id} × ${row.amount}` : `${client} · umumiy to'lov (qarzdan ayiriladi)`),
      field("Summa ($)", amount), field("Izoh", note), el("div", { class: "actions" }, btn));
  });
}

async function driverSheet(name) {
  let d;
  try { d = await api("GET", `/api/drivers/${encodeURIComponent(name)}`); } catch (e) { toast(e.message, true); return; }
  sheet((close) => {
    const amount = el("input", { type: "number", min: "0.01", step: "0.5", inputmode: "decimal", placeholder: "Summa, $" });
    const pay = (direction, label) => async (e) => {
      const v = Number(amount.value);
      if (!v || v <= 0) { toast("Summani kiriting.", true); return; }
      const r = await act(e.target, () => api("POST", `/api/drivers/${encodeURIComponent(name)}/payment`, { amount: v, direction }), label);
      if (r) { close(); driverSheet(name); }
    };
    const months = Object.entries(d.deliveries);
    return el("div", {}, el("h2", {}, name), el("div", { class: "code-big" }, money(d.balance)),
      el("p", { class: "muted small" }, "Balans: musbat — biz haydovchiga qarzdormiz."),
      field("Summa ($)", amount),
      el("div", { class: "actions two" },
        el("button", { class: "btn", type: "button", on: { click: pay("give", "Pul berildi") } }, "Pul berdik"),
        el("button", { class: "btn ghost", type: "button", on: { click: pay("receive", "Pul qaytardi") } }, "Pul qaytardi")),
      el("div", { class: "section-title" }, "Moliya tarixi"),
      d.history.length ? el("div", { class: "list" }, d.history.slice(0, 50).map((h) => el("div", { class: "row" },
        el("div", { class: "grow" }, h.note || h.type, el("div", { class: "sub" }, fdate(h.timestamp))),
        el("div", { class: "end " + (h.type === "Chiqim" ? "pos" : "neg") }, (h.type === "Chiqim" ? "−" : "+") + money(h.amount))))) : empty("Tarix bo'sh."),
      el("div", { class: "section-title" }, "Yetkazishlar"),
      months.length ? el("div", { class: "list" }, months.map(([m, items]) => el("div", { class: "row" },
        el("div", { class: "grow" }, m), el("div", { class: "end" }, `${items.length} ta`)))) : empty("Yetkazish yo'q."));
  });
}

/* ================= BOSHQA (admin) ================= */
async function viewMore() {
  $("toolbar").appendChild(seg([["deliveries", "Yetkazishlar"], ["sales", "Statistika"], ["users", "Foydalanuvchilar"],
    ["settings", "Sozlamalar"], ["audit", "Jurnal"]], S.moreSeg, (k) => { S.moreSeg = k; refresh(); }));
  await viewMoreSection();
}
async function viewMoreSection() {
  const view = clear($("view"));
  view.appendChild(loading());
  const holder = el("div");
  if (S.moreSeg === "deliveries") { await viewDeliveries(holder); }
  else if (S.moreSeg === "sales") {
    const data = await api("GET", "/api/sales");
    if (!data.items.length) holder.appendChild(empty("Statistika uchun ma'lumot yo'q."));
    data.items.forEach((m) => {
      const max = Math.max(1, ...m.items.map((i) => i.count));
      holder.appendChild(el("div", { class: "section-title" }, `${m.month} — ${m.total} ta · ${money(m.revenue)}`));
      holder.appendChild(el("div", { class: "list" }, m.items.slice(0, 10).map((i) => el("div", { class: "row" },
        el("div", { class: "grow" }, el("b", {}, i.product_id), el("div", { class: "bar" }, el("i", { style: `width:${Math.round(i.count / max * 100)}%` }))),
        el("div", { class: "end" }, `${i.count} ta`)))));
    });
  } else if (S.moreSeg === "users") { await usersSection(holder); }
  else if (S.moreSeg === "settings") { await settingsSection(holder); }
  else {
    const data = await api("GET", "/api/audit");
    holder.appendChild(data.items.length ? el("div", { class: "list" }, data.items.map((a) => el("div", { class: "row" },
      el("div", { class: "grow" }, a.action, el("div", { class: "sub" }, [a.order_id, a.product_id, a.user_id ? "ID " + a.user_id : null, a.role].filter(Boolean).join(" · ") || " ")),
      el("div", { class: "end small muted" }, `${fdate(a.at)}\n${a.by || ""}`)))) : empty("Jurnal bo'sh."));
  }
  clear(view).appendChild(holder);
}

async function usersSection(holder) {
  const data = await api("GET", "/api/users");
  const roles = S.me.meta.roles;
  holder.appendChild(el("p", { class: "muted small", style: "margin:6px 4px" },
    "Yangi xodim botga /start yozsa, shu ro'yxatda paydo bo'ladi. Yoki uning Telegram ID raqamini (/id buyrug'i) kiriting."));
  holder.appendChild(el("div", { class: "actions" }, el("button", { class: "btn", type: "button", on: { click: () => userSheet(null) } }, "＋ ID orqali rol berish")));
  const groups = {};
  data.items.forEach((u) => { (groups[u.role] = groups[u.role] || []).push(u); });
  Object.keys(roles).forEach((r) => {
    if (!groups[r]) return;
    holder.appendChild(el("div", { class: "section-title" }, `${roles[r]} — ${groups[r].length}`));
    holder.appendChild(el("div", { class: "list" }, groups[r].slice(0, r === "mijoz" ? 40 : 500).map((u) => el("button", { class: "row", type: "button", on: { click: () => userSheet(u) } },
      el("div", { class: "grow" }, el("div", {}, u.name || "Ismsiz", u.owner ? " ⭐" : ""),
        el("div", { class: "sub" }, [u.username ? "@" + u.username : null, "ID " + u.id, u.client_name].filter(Boolean).join(" · "))),
      el("div", { class: "end small muted" }, fdate(u.last_seen))))));
  });
}

function userSheet(u) {
  const roles = S.me.meta.roles;
  sheet((close) => {
    const id = el("input", { type: "text", inputmode: "numeric", maxlength: "15", value: u ? u.id : "", readonly: u ? true : null, placeholder: "Masalan: 123456789" });
    const role = el("select", {}, Object.entries(roles).map(([k, v]) => el("option", { value: k, selected: u && u.role === k ? true : null }, v)));
    const client = el("select", {}, el("option", { value: "" }, "— Kompaniyani tanlang —"),
      S.me.meta.clients.map((c) => el("option", { value: c, selected: u && u.client_name === c ? true : null }, c)));
    const clientField = field("Diller kompaniyasi", client);
    const sync = () => clientField.classList.toggle("hidden", role.value !== "diller");
    role.addEventListener("change", sync); sync();
    const btn = el("button", { class: "btn", type: "button" }, "Rolni saqlash");
    btn.addEventListener("click", async () => {
      const r = await act(btn, () => api("POST", "/api/users", { id: id.value.trim(), role: role.value, client_name: client.value }), "Rol saqlandi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, u ? (u.name || "Foydalanuvchi") : "Rol berish"),
      field("Telegram ID", id), field("Rol", role), clientField,
      el("p", { class: "muted small" }, "Yangi rol foydalanuvchi keyingi xabar yozganda kuchga kiradi (30 soniyagacha)."),
      el("div", { class: "actions" }, btn));
  });
}

async function settingsSection(holder) {
  const s = await api("GET", "/api/settings");
  const block = (key, title, hint) => {
    const ta = el("textarea", { rows: "8" }, (s[key] || []).join("\n"));
    const btn = el("button", { class: "btn ghost", type: "button" }, "Saqlash");
    btn.addEventListener("click", async () => {
      const items = ta.value.split("\n").map((x) => x.trim()).filter(Boolean);
      const r = await act(btn, () => api("PUT", `/api/settings/${key}`, { items }), `${title}: saqlandi`);
      if (r) { S.me = await api("GET", "/api/me"); }
    });
    return el("div", {}, el("div", { class: "section-title" }, title), el("p", { class: "muted small", style: "margin:0 4px 6px" }, hint),
      ta, el("div", { class: "actions" }, btn));
  };
  holder.appendChild(block("clients", "Dillerlar ro'yxati", "Har qatorda bitta nom. Botdagi tanlov tugmalari shu ro'yxatdan olinadi."));
  holder.appendChild(block("drivers", "Haydovchilar", "Har qatorda bitta ism."));
  holder.appendChild(block("models", "Mebel modellari", "Botdagi tanlov tugmalari tartibi."));
}

/* ================= ishga tushirish ================= */
async function boot() {
  if (tg) { tg.ready(); tg.expand(); }
  if (!tg || !tg.initData) {
    clear($("view")).appendChild(el("div", { class: "gate" }, el("h1", {}, "Panel Telegram ichida ochiladi"),
      el("p", { class: "muted" }, "Botga kiring va «🖥 Panel» tugmasini bosing.")));
    $("who").textContent = "";
    return;
  }
  try {
    S.me = await api("GET", "/api/me");
  } catch (e) {
    clear($("view")).appendChild(el("div", { class: "gate" }, el("h1", {}, "Kirish imkoni yo'q"), el("p", { class: "muted" }, e.message)));
    $("who").textContent = "";
    return;
  }
  $("who").textContent = `${S.me.name || "Foydalanuvchi"} · ${S.me.role_label}`;
  go(TABS[S.me.role][0][0]);
}
boot();
