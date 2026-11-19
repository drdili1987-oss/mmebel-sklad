/* MMebel panel — Telegram Mini App (admin, omborchi, xodim).
   Xavfsizlik: barcha ma'lumotlar DOM ga faqat textContent orqali yoziladi (innerHTML yo'q).
   Har bir API so'rovi Telegram imzosi (initData) bilan yuboriladi; server rolni o'zi aniqlaydi. */
"use strict";
/* Mebel nomi + variant (Matrasli/Kapotli). Variantsiz — bazoviy. */
const plabel = (o) => (o && o.variant ? `${o.product_id} · ${o.variant}` : (o && o.product_id) || "");

const tg = window.Telegram && window.Telegram.WebApp;
const IN_TELEGRAM = !!(tg && tg.initData);
const TOKEN_KEY = "mmebel_token";
function getToken() { try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (_) { return ""; } }
function setToken(t) { try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); } catch (_) { /* yo'q */ } }
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

class ApiError extends Error { constructor(msg, status) { super(msg); this.status = status; } }
async function api(method, path, body) {
  const auth = IN_TELEGRAM ? "tma " + tg.initData : (getToken() ? "Bearer " + getToken() : "");
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: { "Authorization": auth, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (_) {
    throw new ApiError("Internet aloqasi yo'q. Tarmoqni tekshirib, qayta urinib ko'ring.", 0);
  }
  let data = {};
  try { data = await res.json(); } catch (_) { /* bo'sh javob */ }
  if (res.status === 401 && !IN_TELEGRAM && !path.startsWith("/api/auth/")) {
    setToken("");
    showLogin("Sessiya tugagan. Qaytadan kiring.");
    throw new ApiError(data.error || "Sessiya tugagan.", 401);
  }
  if (!res.ok) throw new ApiError(data.error || `Xato (${res.status})`, res.status);
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
/* Android "orqaga" tugmasi: ochiq oyna bo'lsa yopadi (true), aks holda ilova o'zi hal qiladi */
window.mmebelBack = function () {
  const c = sheetStack[sheetStack.length - 1];
  if (c) { c(); return true; }
  if (S.me && S.tab !== TABS[S.me.role][0][0]) { go(TABS[S.me.role][0][0]); return true; }
  return false;
};
function syncBack() {
  if (!IN_TELEGRAM || !tg.BackButton) return;
  if (sheetStack.length) tg.BackButton.show(); else tg.BackButton.hide();
}
if (tg && tg.BackButton) tg.BackButton.onClick(() => { const c = sheetStack[sheetStack.length - 1]; if (c) c(); });

function field(label, input) { return el("label", { class: "field" }, el("span", {}, label), input); }

/* ---------- so'm («ming so'm») kiritish va dollar kursi ----------
   Mijozlardan pul so'mda olinadi: 48 534 yozilsa — 48 534 000 so'm. Server joriy kurs bilan $ ga o'giradi va qotiradi. */
let FX_RATE = null;
async function fxRate(force) {
  if (FX_RATE && !force) return FX_RATE;
  try { FX_RATE = (await api("GET", "/api/fx/convert?ming=1")).rate; } catch (e) { /* kurs olinmadi */ }
  return FX_RATE;
}
function uzs(v) { return Math.round(Number(v || 0)).toLocaleString("ru-RU") + " so'm"; }
function uzsInput(opts) {
  const o = opts || {};
  const input = el("input", { type: "number", min: "0", step: "any", inputmode: "decimal", placeholder: o.placeholder || "Ming so'mda. Masalan: 48 534", "data-autofocus": o.autofocus ? "" : null });
  if (o.value != null && o.value !== "") input.value = String(o.value);
  const hint = el("p", { class: "muted small", style: "margin:4px 2px 0" }, "");
  const upd = () => {
    const v = Number(input.value);
    if (input.value === "" || isNaN(v)) { hint.textContent = "Ming so'mda yozing: 48 534 = 48 534 000 so'm"; return; }
    const full = Math.round(v * 1000), r = FX_RATE;
    hint.textContent = r && S.me && S.me.role === "admin" ? `${uzs(full)} ≈ ${money(full / r)}  (kurs: 1$ = ${uzs(r)})` : uzs(full);
  };
  input.addEventListener("input", upd);
  upd();
  if (S.me && S.me.role === "admin") fxRate().then(upd);
  return { input, hint, node: el("div", {}, input, hint), value: () => (input.value === "" ? NaN : Number(input.value)) };
}

/* Eski to'lovlar: «48 534» $ deb yozilgan, aslida ming so'm. Admin belgilaydi, 12 000 kurs bilan o'tkaziladi. */
async function legacySheet() {
  let d;
  try { d = await api("GET", "/api/fx/legacy"); } catch (e) { toast(e.message, true); return; }
  sheet((close) => {
    const checks = [];
    const list = d.items.map((r) => {
      const cb = el("input", { type: "checkbox" });
      checks.push([cb, r.pay_id]);
      return el("label", { class: "row", style: "gap:10px;align-items:center" }, cb,
        el("div", { class: "grow" }, el("div", {}, r.serial ? `№${r.serial} · ` : "", el("b", {}, plabel(r)), ` — ${r.client}`),
          el("div", { class: "sub" }, `${fdate(r.ts)} · ${r.worker_name} · ${r.method}`)),
        el("div", { class: "end" }, el("b", {}, String(r.amount)), el("div", { class: "sub" }, `→ ${uzs(r.amount * 1000)} ≈ ${money(r.amount * 1000 / d.rate)}`)));
    });
    const btn = el("button", { class: "btn", type: "button" }, "Tanlanganlarni o'tkazish");
    btn.addEventListener("click", async () => {
      const ids = checks.filter(([cb]) => cb.checked).map(([, id]) => id);
      if (!ids.length) { toast("Kamida bittasini belgilang.", true); return; }
      if (!(await confirmDlg(`${ids.length} ta to'lov ming so'm deb hisoblanib, ${uzs(d.rate)} kurs bilan $ ga o'tkazilsinmi?`))) return;
      const r = await act(btn, () => api("POST", "/api/fx/legacy", { pay_ids: ids, rate: d.rate }), "O'tkazildi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "Eski to'lovlarni so'mga o'tkazish"),
      el("p", { class: "muted small" }, `Faqat summasi aslida ming so'mda yozilganlarni belgilang (masalan 48 534). Kurs: ${uzs(d.rate)}. Asl qiymat saqlanadi.`),
      d.items.length ? el("div", { class: "list" }, list) : empty("O'tkaziladigan eski to'lov yo'q."),
      d.items.length ? el("div", { class: "actions" }, btn) : null);
  });
}

/* Admin: dollar kursi. Yangisi kiritilguncha oxirgi kiritilgan kurs amal qiladi. */
async function fxSheet(onDone) {
  let info;
  try { info = await api("GET", "/api/fx"); } catch (e) { toast(e.message, true); return; }
  sheet((close) => {
    const rate = el("input", { type: "number", min: "1000", step: "any", inputmode: "decimal", placeholder: "1$ necha so'm? Masalan: 12 500", "data-autofocus": "" });
    if (info.is_set) rate.value = String(info.rate);
    const btn = el("button", { class: "btn", type: "button" }, "Kursni saqlash");
    btn.addEventListener("click", async () => {
      const v = Number(rate.value);
      if (!v || v < 1000) { toast("Kursni kiriting (masalan, 12500).", true); return; }
      const r = await act(btn, () => api("POST", "/api/fx", { rate: v }), "Kurs saqlandi");
      if (r) { FX_RATE = r.rate; close(); if (onDone) onDone(); }
    });
    return el("div", {}, el("h2", {}, "Dollar kursi"),
      el("p", {}, info.is_set ? ["Hozirgi kurs: ", el("b", {}, uzs(info.rate)), ` (${info.at})`] : "Kurs hali kiritilmagan — vaqtincha 12 000 ishlatiladi."),
      el("p", { class: "muted small" }, "Yangi kurs faqat shundan keyingi to'lovlarga ta'sir qiladi. Oldingi to'lovlar o'z kursida qotib qolgan."),
      field("Yangi kurs (1$ = so'm)", rate), el("div", { class: "actions" }, btn),
      el("div", { class: "actions" }, el("button", { class: "btn ghost", type: "button", on: { click: () => { close(); legacySheet(); } } },
        "🔧 Eski to'lovlarni so'mga o'tkazish")),
      info.log && info.log.length ? el("div", {}, el("div", { class: "section-title" }, "Kurs tarixi"),
        info.log.slice(0, 8).map((x) => el("div", { class: "sub", style: "padding:2px 4px" }, `${x.at} — ${uzs(x.rate)}`))) : null);
  });
}
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
  omborchi: [["home", "🏠", "Asosiy"], ["orders", "📋", "Buyurtmalar"], ["stock", "📦", "Ombor"], ["workers", "🧰", "Yig'uvchilar"], ["deliveries", "🚚", "Yetkazish"]],
  yiguvchi: [["w_home", "🧰", "Mebellarim"], ["w_cash", "💰", "Hisob-kitob"]],
  xodim: [["plan", "🔨", "Ishlab chiqarish"], ["orders", "📋", "Buyurtmalar"]],
  diller: [["d_home", "🏠", "Asosiy"], ["d_catalog", "🛍", "Katalog"], ["d_orders", "📋", "Buyurtmalarim"], ["d_account", "💳", "Hisob"]],
  mijoz: [["m_catalog", "🛍", "Sotuvda"]],
};
const TITLES = { home: "Asosiy", orders: "Buyurtmalar", stock: "Ombor", money: "Moliya", more: "Boshqa",
  deliveries: "Yetkazishlar", plan: "Ishlab chiqarish", workers: "Mebel yig'uvchilar",
  w_home: "Mebellarim", w_cash: "Hisob-kitob",
  d_home: "Asosiy", d_catalog: "Katalog", d_orders: "Buyurtmalarim", d_account: "Hisob", m_catalog: "Sotuvdagi mebellar" };

/* ---------- o'qilmagan buyurtma xabarlari: o'qilmaguncha ajralib turadi ---------- */
S.unread = {};
const UNREAD_LABELS = { new: "🆕 Yangi", ready: "✅ Tayyor bo'ldi", cancel: "❌ Bekor qilindi",
  edit: "✏️ O'zgartirildi", deliver: "🚚 Yetkazildi" };
const ORDERS_TAB = { admin: "orders", omborchi: "orders", xodim: "orders", diller: "d_orders", yiguvchi: "w_home" };
async function loadUnread() {
  if (!S.me || S.me.role === "mijoz") return;
  try { S.unread = (await api("GET", "/api/unread")).items || {}; } catch (_) { /* belgi muhim emas */ }
  renderTabs();
}
function markSeen(ids) {
  const list = (ids || Object.keys(S.unread)).filter((id) => S.unread[id]);
  if (!list.length) return;
  list.forEach((id) => delete S.unread[id]);
  renderTabs();
  api("POST", "/api/unread/seen", ids ? { ids: list } : { all: true }).catch(() => {});
}
function unreadTag(o) {
  const u = S.unread[o.id];
  return u ? el("span", { class: `newtag k-${u.kind}` }, UNREAD_LABELS[u.kind] || "🔔 Yangi xabar") : null;
}
/* Yangi xabarli buyurtmalar ro'yxat tepasida alohida turadi; o'qilgach odatiy joyiga qaytadi */
function unreadSection(items, card) {
  const mine = items.filter((o) => S.unread[o.id]);
  const total = Object.keys(S.unread).length;
  if (!total) return null;
  const btn = el("button", { class: "linkbtn", type: "button" }, "Hammasi o'qildi");
  btn.addEventListener("click", () => { markSeen(); refresh(); });
  const other = total - mine.length;
  return el("div", { class: "unread-section" },
    el("div", { class: "unread-head" }, el("b", {}, `🔔 Yangi xabarlar (${total})`), btn),
    mine.map((o) => card(o)),
    other ? el("p", { class: "muted small", style: "margin:2px 4px 0" },
      `${other} tasi boshqa bo'limda (masalan, «Bekor» yoki «Yetkazilgan»).`) : null);
}

function unreadLink(view, tab) {
  const n = Object.keys(S.unread).length;
  if (!n) return;
  view.appendChild(el("button", { class: "unread-banner", type: "button", on: { click: () => { S.ordersScope = "active"; go(tab); } } },
    el("b", {}, `🔔 ${n} ta yangi xabar`), el("span", {}, " — ko'rish uchun bosing")));
}

function renderTabs() {
  const nav = clear($("tabs"));
  const n = Object.keys(S.unread).length;
  TABS[S.me.role].forEach(([key, ic, label]) => {
    const badge = n && ORDERS_TAB[S.me.role] === key ? el("span", { class: "tab-badge", "aria-label": `${n} ta yangi` }, n > 99 ? "99+" : String(n)) : null;
    nav.appendChild(el("button", { type: "button", "aria-current": S.tab === key ? "page" : null,
      on: { click: () => go(key) } }, el("span", { class: "ic", "aria-hidden": "true" }, ic), badge, label));
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
    deliveries: viewDeliveries, plan: viewPlan, workers: viewWorkers, w_home: viewWHome, w_cash: viewWCash,
    d_home: viewDHome, d_catalog: viewDCatalog, d_orders: viewDOrders, d_account: viewDAccount, m_catalog: viewMCatalog }[tab];
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
  const [d, pay] = await Promise.all([api("GET", "/api/dashboard"), isAdmin ? api("GET", "/api/payments") : null, loadUnread()]);
  const view = clear($("view"));
  unreadLink(view, "orders");
  approvalsWidget(view);
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
    view.appendChild(el("div", { class: "actions" }, el("button", { class: "btn ghost", type: "button", on: { click: openDashboard } },
      "📊 Katta ekran dashboard")));
    view.appendChild(el("div", { class: "section-title" }, pay.items.length ? `Tasdiqlanmagan to'lovlar (${pay.items.length})` : "Tasdiqlanmagan to'lov yo'q"));
    if (pay.items.length) view.appendChild(paymentsList(pay.items));
    fab("＋ Yangi buyurtma", newOrderSheet);
  }
}
/* Bosh ekran: tugallanmagan / qaytgan mebellar va tasdiqlash kutayotganlar (qaytish, tahrir, pul topshirish) */
async function approvalsWidget(view) {
  let d;
  try { d = await api("GET", "/api/approvals"); } catch (_) { return; }
  const n = d.returns.length + d.edits.length + d.transfers.length;
  const box = el("div");
  if (d.defect_count) box.appendChild(el("button", { class: "unread-banner danger-banner", type: "button", on: { click: () => { S.ordersScope = "defect"; go("orders"); } } },
    el("b", {}, `⚠️ Tugallanmagan mebellar: ${d.defect_count} ta`), el("span", {}, " — qayta yig'uvchiga yuboring")));
  if (n) box.appendChild(el("button", { class: "unread-banner", type: "button", on: { click: () => approvalsSheet(d) } },
    el("b", {}, `🔔 Tasdiqlash kutilmoqda: ${n} ta`), el("span", {}, " — ko'rish uchun bosing")));
  if (d.returned_count) box.appendChild(el("button", { class: "unread-banner", type: "button", on: { click: () => { S.ordersScope = "returned"; go("orders"); } } },
    el("b", {}, `↩️ Qaytgan mebellar: ${d.returned_count} ta`)));
  view.prepend(box);
}
function approvalsSheet(d) {
  sheet((close) => {
    const done = () => { close(); refresh(); };
    const resolveBtns = (path, okText, askOk, askNo) => el("div", { class: "actions two", style: "width:100%;margin-top:6px" },
      el("button", { class: "btn", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(askOk))) return;
        if (await act(e.target, () => api("POST", path, { approve: true }), okText)) done();
      } } }, "✅ Tasdiqlash"),
      el("button", { class: "btn danger", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(askNo))) return;
        if (await act(e.target, () => api("POST", path, { approve: false }), "Rad etildi")) done();
      } } }, "Rad etish"));
    const lbl = (x) => `${x.serial ? "№" + x.serial + " · " : ""}${plabel(x)} · ${x.client}`;
    const box = el("div", {}, el("h2", {}, "Tasdiqlash kutilmoqda"));
    if (d.returns.length) {
      box.appendChild(el("div", { class: "section-title" }, "↩️ Skladga qaytdi"));
      box.appendChild(el("div", { class: "list" }, d.returns.map((x) => el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("b", {}, lbl(x)), el("div", { class: "sub" }, [`🧰 ${x.worker_name}`, fdate(x.at), x.note].filter(Boolean).join(" · "))),
        el("div", { class: "end" }, x.expense ? el("b", {}, `xarajat ${money(x.expense)}`) : "xarajatsiz"),
        resolveBtns(`/api/orders/${encodeURIComponent(x.order_id)}/return/resolve`, "Tasdiqlandi — «Qaytgan mebellar» ga tushdi",
          `Mebel skladga qaytganini tasdiqlaysizmi?${x.expense ? " Xarajat " + money(x.expense) + " sex hisobidan yoziladi." : ""}`, "Rad etilsinmi? Mebel yig'uvchida qoladi.")))));
    }
    if (d.edits.length) {
      box.appendChild(el("div", { class: "section-title" }, "✏️ Olingan summani tuzatish"));
      box.appendChild(el("div", { class: "list" }, d.edits.map((x) => el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("b", {}, lbl(x)), el("div", { class: "sub" }, [`🧰 ${x.worker_name}`, x.method === "karta" ? "💳 karta" : "💵 naqd", x.note].filter(Boolean).join(" · "))),
        el("div", { class: "end" }, `${money(x.old_amount)} → `, el("b", {}, money(x.new_amount))),
        resolveBtns(`/api/wpay/${encodeURIComponent(x.pay_id)}/edit/resolve`, "Tasdiqlandi — hisob yangilandi",
          `${money(x.old_amount)} → ${money(x.new_amount)} tasdiqlansinmi? Diller qarzi va yig'uvchi kassasi o'zgaradi.`, "Rad etilsinmi?")))));
    }
    if (d.transfers.length) {
      box.appendChild(el("div", { class: "section-title" }, "💰 Pul topshirish"));
      box.appendChild(el("div", { class: "list" }, d.transfers.map((t) => el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("b", {}, `${t.from_name} → ${t.to_role === "admin" ? "admin" : "omborchi"}`), el("div", { class: "sub" }, fdate(t.ts))),
        el("div", { class: "end" }, el("b", {}, money(t.amount))),
        (S.me.role === "admin" || t.to_role === S.me.role) ? resolveBtns(`/api/cash/transfers/${encodeURIComponent(t.id)}/resolve`, "Tasdiqlandi",
          `Siz ${t.from_name} dan ${money(t.amount)} oldingizmi? Tasdiqlaysizmi?`, `${t.from_name}: ${money(t.amount)} rad etilsinmi?`) : null))));
    }
    if (!d.returns.length && !d.edits.length && !d.transfers.length) box.appendChild(empty("Hammasi ko'rib chiqilgan."));
    return box;
  });
}

function openDashboard() {
  const url = location.origin + "/panel/dashboard";
  // Telegram ichida sessiya tokeni yo'q — dashboard brauzerda ochiladi (u yerda bir marta kirasiz)
  if (IN_TELEGRAM && tg.openLink) tg.openLink(url);
  else location.href = "/panel/dashboard";
}

/* ================= BUYURTMALAR ================= */
/* Buyurtmalar bo'limlari: admin/omborchida 6 ta, xodimda + Bugun / Ertaga / Indinga */
const ORDER_SCOPES = [["active", "Faol"], ["changed", "❗️O'zgarishli❗️"], ["overdue", "Muddati o'tgan"],
  ["ready", "Tayyor mebellar"], ["done", "Yetkazilgan"], ["cancelled", "Bekor qilingan"]];
/* Admin va omborchida qo'shimcha: «Yig'uvchida» (yig'ish uchun yuborilgan, hali topshirilmagan) */
const STAFF_ORDER_SCOPES = ORDER_SCOPES.slice(0, 4).concat([["assigned", "🧰 Yig'uvchida"], ["returned", "↩️ Qaytgan mebellar"],
  ["defect", "⚠️ Tugallanmagan"]], ORDER_SCOPES.slice(4));
const XODIM_DAY_SCOPES = [["today", "Bugun"], ["tomorrow", "Ertaga"], ["after", "Indinga"]];

async function viewOrders() {
  const role = S.me.role;
  const tb = $("toolbar");
  const scopes = role === "xodim" ? ORDER_SCOPES.concat(XODIM_DAY_SCOPES) : STAFF_ORDER_SCOPES;
  if (!scopes.some(([k]) => k === S.ordersScope)) S.ordersScope = "active";
  const segBox = el("div");
  tb.appendChild(segBox);
  const search = el("input", { class: "search", type: "search", placeholder: "Qidirish: tartib raqam, diller, mebel", value: S.ordersQuery });
  tb.appendChild(search);
  const [data] = await Promise.all([api("GET", `/api/orders?scope=${S.ordersScope}`), loadUnread()]);
  const scope = data.scope || S.ordersScope;
  const counts = data.counts || {};
  segBox.replaceWith(seg(scopes.map(([k, label]) => [k, counts[k] ? `${label} · ${counts[k]}` : label]),
    scope, (k) => { S.ordersScope = k; refresh(); }));
  const view = clear($("view"));
  const box = el("div");
  view.appendChild(box);
  const draw = () => {
    const q = search.value.trim().toLowerCase();
    S.ordersQuery = search.value;
    const found = data.items.filter((o) => !q || `${o.serial || ""} ${o.client_name} ${plabel(o)} ${o.id} ${o.worker_name || ""} ${o.comment || ""}`.toLowerCase().includes(q));
    clear(box);
    const dated = scope !== "done" && scope !== "cancelled";
    const sec = unreadSection(found, (o) => orderCard(o, !dated));
    if (sec) box.appendChild(sec);
    const items = found.filter((o) => !S.unread[o.id]);
    if (!items.length) { if (!sec) box.appendChild(empty(q ? "Hech narsa topilmadi." : "Bu ro'yxatda buyurtma yo'q.")); return; }
    if (dated) {
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
  const isNew = !!S.unread[o.id];
  return el("button", { type: "button", class: `order ${edgeClass(o.status)}${o.overdue ? " late" : ""}${isNew ? " unread" : ""}`,
    on: { click: (e) => { if (isNew) { markSeen([o.id]); e.currentTarget.classList.remove("unread"); e.currentTarget.querySelector(".newtag")?.remove(); } orderSheet(o.id); } } },
    unreadTag(o),
    o.changed ? el("span", { class: "chgtag" }, "❗️ O'zgarishli") : null,
    el("div", {}, o.serial ? el("span", { class: "serial" }, `№${o.serial}`) : null,
      el("span", { class: "code" }, plabel(o)), el("span", { class: "qty" }, `× ${o.amount}`),
      o.status !== "Tayyorlanmoqda" || showStatus ? el("span", { style: "margin-left:8px" }, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status)) : null),
    el("div", { class: "line2" }, el("span", { class: "client" }, o.client_name || "—"),
      el("span", { class: "due" }, showStatus ? fdate(o.delivered_at || o.created_at) : fdate(o.due_date))),
    o.comment && !["yoq", "yo'q", "-"].includes(String(o.comment).toLowerCase()) ? el("div", { class: "note" }, "📝 " + o.comment) : null,
    o.worker_name ? el("div", { class: "note" }, `🧰 ${o.worker_name}${o.ret && o.ret.status === "pending" ? " · ⏳ skladga qaytdi (tasdiq)" : o.handover && !(o.defect && o.defect.open) ? (o.handover.correct ? " · ✅ topshirdi" : " · ⚠️ qoldiq chala") : ACTIVE.includes(o.status) || (o.defect && o.defect.open) ? " · yig'ishda" : ""}`) : null,
    o.defect && o.defect.open ? el("div", { class: "note", style: "color:var(--st-late);font-weight:600" }, "⚠️ Tugallanmagan: " + o.defect.note) : null,
    o.returned && ACTIVE.includes(o.status) && !o.worker_id ? el("div", { class: "note" }, "↩️ Skladga qaytgan") : null,
  );
}

async function orderSheet(id) {
  let o;
  try { o = await api("GET", `/api/orders/${encodeURIComponent(id)}`); } catch (e) { toast(e.message, true); return; }
  const role = S.me.role;
  sheet((close) => {
    const isActive = ACTIVE.includes(o.status);
    const staff = role === "admin" || role === "omborchi";
    const kv = el("dl", { class: "kv" },
      o.serial ? [el("dt", {}, "Tartib raqam"), el("dd", {}, el("b", {}, `№${o.serial}`))] : null,
      el("dt", {}, "Diller"), el("dd", {}, o.client_name || "—"),
      el("dt", {}, "Soni"), el("dd", {}, `${o.amount} ta`),
      el("dt", {}, "Muddat"), el("dd", { class: o.overdue ? "pos" : "" }, `${fdate(o.due_date)}${o.overdue ? " (kechikkan)" : ""}`),
      el("dt", {}, "Holati"), el("dd", {}, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status)),
      o.changed ? [el("dt", {}, "Turi"), el("dd", {}, el("span", { class: "chgtag", style: "margin:0" }, "❗️ O'zgarishli mebel"))] : null,
      o.comment ? [el("dt", {}, "Izoh"), el("dd", {}, o.comment)] : null,
      role === "admin" && o.total_price ? [el("dt", {}, "Narxi"), el("dd", {}, `${money(o.price)} × ${o.amount} = ${money(o.total_price)}`)] : null,
      staff && o.collect != null ? [el("dt", {}, "Mijozdan qoldiq"), el("dd", {}, money(o.collect))] : null,
      o.worker_name && ACTIVE.includes(o.status) ? [el("dt", {}, "Yig'uvchi"), el("dd", {}, `🧰 ${o.worker_name}`)] : null,
      o.driver ? [el("dt", {}, o.worker_name ? "Yig'uvchi" : "Haydovchi"), el("dd", {}, `${o.driver}${o.delivery_price && o.delivery_price !== "0$" ? " · " + o.delivery_price : ""}`)] : null,
      o.delivered_at ? [el("dt", {}, "Yetkazilgan"), el("dd", {}, fdate(o.delivered_at))] : null,
      el("dt", {}, "Yaratilgan"), el("dd", {}, fdate(o.created_at)),
      el("dt", {}, "ID"), el("dd", { class: "small muted" }, o.id),
    );
    const actions = el("div", { class: "actions" });
    const done = () => { close(); refresh(); };
    const info = el("div");
    if (staff && o.ret && o.ret.status === "pending") {
      info.appendChild(el("div", { class: "unread-banner", style: "display:block" }, el("b", {}, `↩️ ${o.ret.worker_name}: skladga qaytdi — tasdiqlang`),
        el("div", { class: "small" }, [o.ret.expense ? "Xarajat " + money(o.ret.expense) : "Xarajat yo'q", o.ret.note].filter(Boolean).join(" · "))));
      const resolve = (approve) => async (e) => {
        if (!(await confirmDlg(approve ? "Skladga qaytganini tasdiqlaysizmi?" : "Rad etilsinmi? Mebel yig'uvchida qoladi."))) return;
        if (await act(e.target, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/return/resolve`, { approve }), approve ? "Tasdiqlandi" : "Rad etildi")) done();
      };
      actions.appendChild(el("div", { class: "actions two", style: "margin-top:0" },
        el("button", { class: "btn", type: "button", on: { click: resolve(true) } }, "✅ Tasdiqlash"),
        el("button", { class: "btn danger", type: "button", on: { click: resolve(false) } }, "Rad etish")));
    }
    if (staff && o.defect && (o.defect.open || (o.defect.history || []).length)) {
      info.appendChild(el("div", { class: "unread-banner" + (o.defect.open ? " danger-banner" : ""), style: "display:block" },
        el("b", {}, o.defect.open ? "⚠️ Tugallanmagan — kamchilik bor" : "✅ Kamchilik tuzatilgan"),
        (o.defect.history || []).map((h) => el("div", { class: "small", style: "margin-top:4px" }, `${fdate(h.at)} · ${h.worker_name}: ${h.note} (olindi ${money(h.amount)})`))));
      if (o.defect.open) actions.appendChild(el("button", { class: "btn", type: "button", on: { click: () => assignSheet(o, done) } },
        o.worker_id ? `🧰 ${o.worker_name} tuzatmoqda — almashtirish` : "🧰 Yig'uvchiga qayta yuborish"));
    }
    if (staff && o.returned && isActive && !o.worker_id) {
      info.appendChild(el("div", { class: "unread-banner", style: "display:block" }, el("b", {}, "↩️ Skladga qaytgan mebel"),
        el("div", { class: "small" }, o.ret ? [fdate(o.ret.resolved_at || o.ret.at), o.ret.worker_name, o.ret.note].filter(Boolean).join(" · ") : "")));
    }
    if (isActive && staff && !(o.ret && o.ret.status === "pending")) {
      actions.appendChild(el("button", { class: "btn", type: "button", on: { click: () => assignSheet(o, done) } },
        o.worker_id ? "🧰 Yig'uvchini almashtirish" : "🧰 Yig'ish uchun yuborildi"));
      if (o.worker_id) actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(`${o.worker_name} dan olib qo'yilsinmi?`))) return;
        const r = await act(e.target, () => api("DELETE", `/api/orders/${encodeURIComponent(o.id)}/assign`), "Yig'uvchidan olindi");
        if (r) done();
      } } }, "↩️ Yig'uvchidan olish"));
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
        if (!(await confirmDlg(`${plabel(o)} × ${o.amount} (${o.client_name}) bekor qilinsinmi? Ombordan ayirilgani qaytariladi.`))) return;
        const r = await act(e.target, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/cancel`), "Buyurtma bekor qilindi");
        if (r) done();
      } } }, "Buyurtmani bekor qilish"));
    } else if (role === "admin" && o.status !== "Bekor qilindi") {
      actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => editOrderSheet(o, done, true) } }, "✏️ Narx / tartib raqam / qoldiqni to'g'rilash"));
    }
    const pays = el("div");
    if (staff && (o.worker_id || o.handover) && !isActive) loadOrderPays(o.id, pays);
    return el("div", {}, el("div", { class: "code-big" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)} × ${o.amount}`), info, kv, pays, actions);
  });
}

/* Mijozdan olingan to'lovlar (yig'uvchi kiritgan) va karta skrinshotlari */
async function loadOrderPays(oid, holder) {
  let data;
  try { data = await api("GET", `/api/orders/${encodeURIComponent(oid)}/wpay`); } catch (_) { return; }
  if (!data.items.length) return;
  holder.appendChild(el("div", { class: "section-title" }, "Mijozdan olingan to'lov"));
  holder.appendChild(payList(data.items));
}
function payList(items, showOrder) {
  return el("div", { class: "list" }, items.map((p) => el("div", { class: "row", style: "flex-wrap:wrap" },
    el("div", { class: "grow" },
      el("div", {}, showOrder ? el("b", {}, `${p.serial ? "№" + p.serial + " · " : ""}${plabel(p)} — ${p.client}`) : el("b", {}, p.kind === "extra" ? "Qo'shimcha to'lov" : (p.correct ? "✅ Qoldiq to'g'ri olindi" : "⚠️ Qoldiq to'liq olinmadi"))),
      el("div", { class: "sub" }, [fdate(p.ts), p.method === "karta" ? "💳 karta" : "💵 naqd", p.expected ? `kutilgan ${money(p.expected)}` : null, p.note].filter(Boolean).join(" · "))),
    el("div", { class: "end" }, el("b", {}, money(p.amount))),
    p.photos ? el("div", { class: "thumbs", style: "width:100%" }, Array.from({ length: p.photos }, (_, i) => photoThumb(p.pay_id, i))) : null)));
}
/* Rasm avtorizatsiya bilan yuklanadi (img src ga token qo'yib bo'lmaydi) */
function photoThumb(pid, i) {
  const img = el("img", { class: "thumb", alt: `Rasm ${i + 1}`, loading: "lazy" });
  const auth = IN_TELEGRAM ? "tma " + tg.initData : (getToken() ? "Bearer " + getToken() : "");
  fetch(`/api/wphoto/${encodeURIComponent(pid)}/${i}`, { headers: { Authorization: auth } })
    .then((r) => (r.ok ? r.blob() : null)).then((b) => {
      if (!b) { img.alt = "Rasm ochilmadi"; return; }
      const url = URL.createObjectURL(b);
      img.src = url;
      img.addEventListener("click", () => sheet(() => el("div", {}, el("img", { src: url, class: "photo-full", alt: "" }))));
    }).catch(() => { img.alt = "Rasm ochilmadi"; });
  return img;
}

async function assignSheet(o, onDone) {
  let data;
  try { data = await api("GET", "/api/workers"); } catch (e) { toast(e.message, true); return; }
  const list = data.workers.filter((w) => w.active);
  sheet((close) => {
    let pick = o.worker_id || null;
    const fee = el("input", { type: "number", min: "0", step: "0.5", inputmode: "decimal", placeholder: "Ixtiyoriy, $" });
    const btn = el("button", { class: "btn", type: "button" }, "Yig'uvchiga yuborish");
    const rows = el("div", { class: "list pick" }, list.map((w) => {
      const b = el("button", { class: "row", type: "button", "aria-pressed": String(w.id === pick) },
        el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, w.name),
          el("div", { class: "sub" }, `${w.assigned} ta yig'ishda${w.linked ? "" : " · ⚠️ hali botga kirmagan"}`)),
        el("div", { class: "end" }, w.id === pick ? "✓" : ""));
      b.addEventListener("click", () => {
        pick = w.id;
        rows.querySelectorAll("button").forEach((x) => { x.setAttribute("aria-pressed", "false"); x.querySelector(".end").textContent = ""; });
        b.setAttribute("aria-pressed", "true"); b.querySelector(".end").textContent = "✓";
      });
      return b;
    }));
    btn.addEventListener("click", async () => {
      if (!pick) { toast("Yig'uvchini tanlang.", true); return; }
      const r = await act(btn, () => api("POST", `/api/orders/${encodeURIComponent(o.id)}/assign`,
        { worker_id: pick, fee: fee.value === "" ? null : Number(fee.value) }), "Yig'uvchiga yuborildi");
      if (r) { close(); onDone(); }
    });
    return el("div", {}, el("h2", {}, "Yig'ish uchun yuborish"),
      el("p", { class: "muted small" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)} × ${o.amount} · ${o.client_name}`),
      list.length ? rows : empty("Yig'uvchi yo'q. Avval «Yig'uvchilar» bo'limida profil oching."),
      field("Yetkazish haqi ($) — yig'uvchi balansiga yoziladi", fee),
      el("div", { class: "actions" }, btn));
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
      el("p", { class: "muted small" }, `${plabel(o)} × ${o.amount} · ${o.client_name}`),
      pickup ? null : field("Haydovchi", el("div", {}, chips(m.drivers, null, (v) => { driver = v; customDriver.value = ""; }), customDriver)),
      field(pickup ? "Chegirma ($) — qarzdan ayiriladi" : "Dostavka narxi ($) — haydovchi balansiga yoziladi",
        el("div", {}, chips(presets, null, (v) => { price = Number(v); priceInput.value = ""; }, (v) => `${v}$`), priceInput)),
      el("div", { class: "actions" }, btn));
  });
}

function editOrderSheet(o, onDone, metaOnly) {
  sheet((close) => {
    const serial = el("input", { type: "text", maxlength: "20", value: o.serial || "", placeholder: "Masalan: 001" });
    const collectU = uzsInput({ value: o.collect_uzs != null ? o.collect_uzs / 1000 : "", placeholder: "Bo'sh — belgilanmagan" });
    const collect = collectU.input;
    const oldCollect = o.collect_uzs != null ? o.collect_uzs / 1000 : null;
    // Admin: mebel nomi va narxi ham tahrirlanadi (xato bo'lsa buyurtmani bekor qilib qayta ochish shart emas)
    const product = el("input", { type: "text", maxlength: "60", value: o.product_id || "", list: "models-dl3", autocomplete: "off" });
    const dl = el("datalist", { id: "models-dl3" }, (S.me.meta.models || []).map((x) => el("option", { value: x })));
    const price = el("input", { type: "number", min: "0", step: "0.01", inputmode: "decimal", value: o.price != null ? o.price : "" });
    const amount = el("input", { type: "number", min: "1", max: "10000", value: o.amount, inputmode: "numeric" });
    const due = el("input", { type: "date", value: toIso(o.due_date), min: isoToday() });
    const comment = el("textarea", { maxlength: "500" }, o.comment || "");
    const chg = el("select", {}, el("option", { value: "0" }, "Yo'q (bazoviy)"), el("option", { value: "1" }, "❗️ Ha — o'zgarishli"));
    chg.value = o.changed ? "1" : "0";
    const btn = el("button", { class: "btn", type: "button" }, "O'zgarishlarni saqlash");
    btn.addEventListener("click", async () => {
      const body = {};
      if (serial.value.trim() !== (o.serial || "")) body.serial = serial.value.trim();
      const cv = collect.value === "" ? null : Number(collect.value);
      if (cv !== oldCollect && !(cv === null && o.collect == null)) body.collect = cv === null ? "" : cv;
      if (price.value !== "" && Number(price.value) !== Number(o.price)) body.price = Number(price.value);
      if (!metaOnly) {
        if (product.value.trim() && product.value.trim() !== o.product_id) body.product = product.value.trim();
        if (Number(amount.value) !== Number(o.amount)) body.amount = Number(amount.value);
        if (due.value && due.value !== toIso(o.due_date)) body.due_date = due.value;
        if (comment.value !== (o.comment || "")) body.comment = comment.value;
        if ((chg.value === "1") !== !!o.changed) body.changed = chg.value === "1";
      }
      if (!Object.keys(body).length) { close(); return; }
      const r = await act(btn, () => api("PATCH", `/api/orders/${encodeURIComponent(o.id)}`, body), "Saqlandi. Dillerga xabar yuborildi.");
      if (r) { close(); onDone(); }
    });
    return el("div", {}, el("h2", {}, `${plabel(o)} — o'zgartirish`),
      el("div", { class: "actions two", style: "margin-top:0" }, field("Tartib raqam", serial), field("Mijozdan qoldiq (ming so'm)", collectU.node)),
      metaOnly ? null : field("Mebel nomi", el("div", {}, product, dl)),
      field("1 dona narxi ($)", price),
      metaOnly ? el("p", { class: "muted small" }, "Narx o'zgarsa, diller qarzi avtomatik qayta hisoblanadi.") : null,
      metaOnly ? null : [field("Soni", amount), field("Muddat", due), field("Izoh", comment), field("O'zgarishli mebelmi?", chg),
        el("p", { class: "muted small" }, "Mebel yoki soni o'zgarsa, ombor qoldig'i avtomatik to'g'rilanadi. Yangi mebel tanlansa va narx o'zgartirilmasa — katalog narxi qo'yiladi.")],
      el("div", { class: "actions" }, btn));
  });
}

function newOrderSheet() {
  const m = S.me.meta;
  sheet((close) => {
    const clientSel = el("select", {}, el("option", { value: "" }, "— Dillerni tanlang —"),
      (m.clients || []).map((c) => el("option", { value: c }, c)), el("option", { value: "__new" }, "+ Yangi diller"));
    // Tartib raqam qo'lda kiritiladi (avtomatik berilmaydi); bitta diller ichida takrorlanmaydi
    const serial = el("input", { type: "text", maxlength: "20", placeholder: "Masalan: 001", autocomplete: "off" });
    const collectU = uzsInput({ placeholder: "Ming so'mda. Masalan: 1 850 — yig'uvchi shu summani oladi" });
    const newClient = el("input", { type: "text", maxlength: "60", placeholder: "Yangi diller nomi", class: "hidden" });
    clientSel.addEventListener("change", () => newClient.classList.toggle("hidden", clientSel.value !== "__new"));
    const product = el("input", { type: "text", list: "models-dl", maxlength: "60", placeholder: "Ro'yxatdan tanlang yoki o'zingiz yozing" });
    const productHint = el("p", { class: "muted small", style: "margin:4px 0 0" }, "");
    const known = new Set(m.models.map((x) => x.replace(/[\s-]/g, "").toUpperCase()));
    product.addEventListener("input", () => {
      const v = product.value.trim();
      const custom = v && !known.has(v.replace(/[\s-]/g, "").toUpperCase());
      productHint.textContent = custom ? "Shablonda yo'q mebel — narxini albatta kiriting." : "";
      if (!changedTouched) setChanged(!!custom);  // shablonda yo'q mebel odatda o'zgarishli
      price.placeholder = custom ? "Narxi ($) — majburiy" : "Bo'sh qoldirsangiz — ombordagi narx";
    });
    const dl = el("datalist", { id: "models-dl" }, m.models.map((x) => el("option", { value: x })));
    // Variant: «Tanlang» bosilganda Matrasli / Kapotli chiqadi; hech biri tanlanmasa — bazoviy
    const chosen = new Set();
    const variantLabel = el("span", {}, "Bazoviy");
    const variantChips = el("div", { class: "chips variant-chips hidden" }, (m.variants || []).map((v) => {
      const c = el("button", { type: "button", "aria-pressed": "false" }, v);
      c.addEventListener("click", () => {
        if (chosen.has(v)) chosen.delete(v); else chosen.add(v);
        c.setAttribute("aria-pressed", String(chosen.has(v)));
        variantLabel.textContent = chosen.size ? (m.variants || []).filter((x) => chosen.has(x)).join(", ") : "Bazoviy";
      });
      return c;
    }));
    const variantBtn = el("button", { class: "btn ghost variant-btn", type: "button" }, "Tanlang ▾ · ", variantLabel);
    // «O'zgarishli»: omborchi va xodimda alohida bo'limga tushadi
    let changed = false;
    let changedTouched = false;
    const changedBtn = el("button", { class: "btn ghost changed-btn", type: "button", "aria-pressed": "false" });
    const setChanged = (on) => {
      changed = on;
      changedBtn.setAttribute("aria-pressed", String(on));
      changedBtn.textContent = on ? "❗️ O'zgarishli — HA" : "O'zgarishli emas (bazoviy)";
    };
    setChanged(false);
    changedBtn.addEventListener("click", () => { changedTouched = true; setChanged(!changed); });
    variantBtn.addEventListener("click", () => variantChips.classList.toggle("hidden"));
    const amount = el("input", { type: "number", min: "1", max: "10000", value: "1", inputmode: "numeric" });
    const price = el("input", { type: "number", min: "0", step: "0.5", inputmode: "decimal", placeholder: "Bo'sh qoldirsangiz — ombordagi narx" });
    const due = el("input", { type: "date", value: isoToday(2), min: isoToday() });
    const comment = el("textarea", { maxlength: "500", placeholder: "Masalan: rangi oq, eshigi oynali" });
    const btn = el("button", { class: "btn", type: "button" }, "Buyurtmani yaratish");
    btn.addEventListener("click", async () => {
      const isNew = clientSel.value === "__new";
      const client = isNew ? newClient.value.trim() : clientSel.value;
      if (!client) { toast("Dillerni tanlang.", true); return; }
      if (!serial.value.trim()) { toast("Tartib raqamini kiriting.", true); serial.focus(); return; }
      if (!product.value.trim()) { toast("Mebelni kiriting.", true); return; }
      const body = { client_name: client, serial: serial.value.trim(), product: product.value.trim(), amount: Number(amount.value), due_date: due.value,
        comment: comment.value, new_client: isNew, variant: [...chosen], changed };
      if (!isNaN(collectU.value())) body.collect = collectU.value();
      if (changed && !comment.value.trim()) { toast("O'zgarishli mebel uchun izohga nimasi o'zgarganini yozing.", true); comment.focus(); return; }
      if (price.value !== "") body.price = Number(price.value);
      const r = await act(btn, () => api("POST", "/api/orders", body), "Buyurtma yaratildi");
      if (r) { close(); S.ordersScope = "active"; go("orders"); }
    });
    return el("div", {}, el("h2", {}, "Yangi buyurtma"),
      field("Diller", el("div", {}, clientSel, newClient)), field("Tartib raqam *", serial),
      field("Mebel", el("div", {}, product, dl, productHint)),
      (m.variants || []).length ? field("Variant", el("div", {}, variantBtn, variantChips)) : "",
      field("O'zgarishli mebelmi?", el("div", {}, changedBtn,
        el("p", { class: "muted small", style: "margin:4px 2px 0" }, "HA bo'lsa — buyurtma omborchi va xodimda «❗️O'zgarishli❗️» bo'limiga tushadi. Nimasi o'zgarganini izohga yozing."))),
      el("div", { class: "actions two", style: "margin-top:0" }, field("Soni", amount), field("Muddat", due)),
      field("1 dona narxi ($)", price),
      field("Mijozdan olinadigan qoldiq (ming so'm)", collectU.node), field("Izoh", comment), el("div", { class: "actions" }, btn));
  });
}

/* ================= ISHLAB CHIQARISH (xodim) ================= */
async function viewPlan() {
  const [plan, d] = await Promise.all([api("GET", "/api/production"), api("GET", "/api/dashboard"), loadUnread()]);
  const view = clear($("view"));
  unreadLink(view, "orders");
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
    // Omborchi faqat bazada bor mebelni tanlaydi; yangi nomni admin qo'shadi
    const name = (role === "admin" || p)
      ? el("input", { type: "text", list: "models-dl2", maxlength: "60", value: p ? p.name : "", placeholder: "Masalan: BF 07", readonly: p ? true : null })
      : el("select", {}, el("option", { value: "" }, "— Mebelni tanlang —"), S.me.meta.models.map((x) => el("option", { value: x }, x)));
    const dl = el("datalist", { id: "models-dl2" }, S.me.meta.models.map((x) => el("option", { value: x })));
    const model = el("input", { type: "text", maxlength: "60", value: p ? p.model : "", placeholder: "Masalan: Spalniy" });
    const qty = el("input", { type: "number", min: "0", value: p ? p.qty : "0", inputmode: "numeric" });
    const price = el("input", { type: "number", min: "0", step: "0.5", value: p && p.price ? p.price : "", inputmode: "decimal" });
    const image = el("input", { type: "url", maxlength: "500", value: p ? p.image : "", placeholder: "https://…" });
    const btn = el("button", { class: "btn", type: "button" }, "Saqlash");
    btn.addEventListener("click", async () => {
      if (!name.value.trim()) { toast("Mebel nomini kiriting.", true); return; }
      const body = { name: name.value.trim(), model: model.value, qty: Number(qty.value || 0), image: image.value.trim() };
      if (role === "admin") {
        if (!(Number(price.value) > 0) && !(p && p.price)) { toast("Mebel narxini kiriting ($).", true); price.focus(); return; }
        if (price.value !== "") body.price = Number(price.value);
      }
      const r = await act(btn, () => api("POST", "/api/products", body), "Mebel saqlandi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, p ? "Mebelni tahrirlash" : "Yangi mebel"),
      field("Nomi", el("div", {}, name, dl)), field("Modeli / turi", model), field("Omborda soni", qty),
      role === "admin" ? field("1 dona narxi ($) *", price) : null, field("Rasm manzili (ixtiyoriy)", image),
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
    el("div", { class: "grow" }, el("div", {}, el("b", {}, plabel(r)), ` × ${r.amount || 1} — ${r.client || "—"}`),
      el("div", { class: "sub" }, `${r.driver || "—"} · ${r.price || "0"}${r.comment ? " · " + r.comment : ""}`)),
    el("div", { class: "end small muted" }, fdate(r.timestamp))))));
}

/* ================= MOLIYA (admin) ================= */
async function viewMoney() {
  $("toolbar").appendChild(seg([["debts", "Qarzlar"], ["workers", "🧰 Yig'uvchilar"], ["payments", "To'lovlar"], ["drivers", "Haydovchilar"]], S.moneySeg,
    (k) => { S.moneySeg = k; refresh(); }));
  const view = clear($("view"));
  if (S.moneySeg === "workers") { await viewWorkers(view); return; }
  if (S.moneySeg === "debts") {
    const data = await api("GET", "/api/debts");
    const total = data.items.filter((r) => r.debt > 0).reduce((s, r) => s + r.debt, 0);
    view.appendChild(el("div", { class: "stats" }, el("div", { class: "stat wide" }, el("b", {}, money(total)), el("span", {}, "Dillerlarning jami qarzi"))));
    const fx = await api("GET", "/api/fx");
    view.appendChild(el("button", { class: "row", type: "button", on: { click: () => fxSheet(refresh) } },
      el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, "💱 Dollar kursi"),
        el("div", { class: "sub" }, fx.is_set ? `Kiritilgan: ${fx.at}` : "Kiritilmagan — 12 000 ishlatilyapti")),
      el("div", { class: "end" }, el("b", {}, uzs(fx.rate)))));
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
    if (a.last_settlement) box.appendChild(lastSettlementNote(a.last_settlement));
    const payBtn = el("button", { class: "btn", type: "button", on: { click: () => partialSheet(client, null, reopen) } }, "💵 To'lov qabul qilish");
    const actions = el("div", { class: "actions" }, payBtn);
    if (a.unsettled.length) {
      actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(`${client}: ${a.unsettled.length} ta buyurtma va ${money(a.debt)} qarz to'liq to'landi deb belgilansinmi?`))) return;
        const r = await act(e.target, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/settle_all`), "Hammasi hisob-kitob qilindi");
        if (r) { reopen(); }
      } } }, "💳 Barchasi to'landi"));
    }
    if (a.unsettled.length) {
      actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => rangeSettleSheet(client, a.last_settlement, reopen) } },
        "🗓 Sana bo'yicha to'landi"));
    }
    actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => reportSheet(client) } }, "📄 Yetkazilganlar: PDF / nusxa"));
    actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => settlementsSheet(client) } }, "📑 Hisob-kitoblar tarixi (PDF)"));
    box.appendChild(actions);
    box.appendChild(el("div", { class: "section-title" }, `To'lanmagan (yetkazilgan) — ${a.unsettled.length} ta`));
    if (!a.unsettled.length) box.appendChild(empty("Hammasi to'langan."));
    else box.appendChild(el("div", { class: "list" }, a.unsettled.map((r) => {
      const left = Math.max(0, r.net - r.paid_partial);
      const row = el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("div", {}, el("b", {}, plabel(r)), ` × ${r.amount}`),
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
        el("div", { class: "grow" }, el("b", {}, plabel(r)), ` × ${r.amount}`, el("div", { class: "sub" }, `${r.status} · ${fdate(r.due_date)}`)),
        el("div", { class: "end" }, money(r.gross))))));
    }
    box.appendChild(el("div", { class: "section-title" }, "Hisob-kitob tarixi"));
    if (!a.history.length) box.appendChild(empty("Tarix bo'sh."));
    else box.appendChild(el("div", { class: "list" }, a.history.slice(0, 60).map((h) => el("div", { class: "row" },
      el("div", { class: "grow" }, h.accounting_type === "toliq" ? `✅ ${plabel(h) || ""} × ${h.amount || ""}` : `💰 Qisman to'lov${plabel(h) ? " · " + plabel(h) : ""}`,
        el("div", { class: "sub" }, `${fdate(h.accounting_date)}${h.note ? " · " + h.note : ""}${h.settled ? " · yopilgan" : ""}`)),
      el("div", { class: "end" }, money(h.accounting_type === "toliq" ? h.total_price : h.partial_payment))))));
    return box;
  });
}

/* Eslatma: oxirgi hisob-kitob qaysi sanalar oralig'ida qilingan */
function lastSettlementNote(ls) {
  const when = ls.at ? ` (${fdate(ls.at)} kuni bosilgan)` : "";
  return el("p", { class: "muted small" }, `🕘 Oxirgi hisob-kitob: ${fdate(ls.from)} – ${fdate(ls.to)}, ${ls.count} ta mebel${when}`);
}

/* Hisob-kitoblar tarixi: qachon va qaysi sana oralig'ida bosilgan; PDF — admin o'zini tekshirishi uchun */
async function settlementsSheet(client) {
  let data;
  try { data = await api("GET", `/api/reports/settlements?client=${encodeURIComponent(client)}`); } catch (e) { toast(e.message, true); return; }
  sheet(() => {
    const pdf = el("button", { class: "btn", type: "button" }, "📄 PDF yuklash");
    pdf.addEventListener("click", async () => {
      const r = await act(pdf, () => api("POST", "/api/reports/settlements/link", { client }));
      if (r) { try { await openFile(r.url, "hisob-kitoblar.pdf"); } catch (e) { toast(e.message, true); } }
    });
    const list = !data.items.length ? empty("Hali hisob-kitob qilinmagan.") :
      el("div", { class: "list" }, data.items.map((b) => el("div", { class: "row" },
        el("div", { class: "grow" }, el("b", {}, b.range_label === "noma'lum" ? "Sana oralig'i noma'lum" : b.range_label),
          el("div", { class: "sub" }, `${b.at_label} · ${b.count} ta mebel · ${b.by_name}${b.legacy ? " · eski" : ""}`)),
        el("div", { class: "end" }, b.received === null ? "—" : money(b.received)))));
    return el("div", {}, el("h2", {}, "Hisob-kitoblar tarixi"), el("p", { class: "muted small" }, `${client} · ${data.items.length} ta`),
      el("div", { class: "actions" }, pdf), list);
  });
}

/* Sana bo'yicha «To'landi»: avval ko'rinish, keyin tasdiqlash. Yetkazilgan sana bo'yicha, ikkala chegara ham kiradi. */
function rangeSettleSheet(client, last, onDone) {
  sheet((close) => {
    const from = el("input", { type: "date" });
    const to = el("input", { type: "date" });
    const result = el("div", {});
    const preview = el("button", { class: "btn", type: "button" }, "Ko'rish");
    const params = () => ({ from: from.value, to: to.value });
    const reset = () => clear(result);
    from.addEventListener("change", reset);
    to.addEventListener("change", reset);
    preview.addEventListener("click", async () => {
      if (!from.value || !to.value) { toast("Ikkala sanani tanlang.", true); return; }
      const p = await act(preview, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/settle_range`, params()));
      if (!p) return;
      clear(result);
      if (!p.count) { result.appendChild(empty("Bu sanalarda hisob-kitob qilinmagan yetkazilgan mebel yo'q.")); return; }
      result.appendChild(el("div", { class: "list" },
        el("div", { class: "row" }, el("div", { class: "grow" }, "Mebellar soni"), el("div", { class: "end" }, `${p.count} ta`)),
        el("div", { class: "row" }, el("div", { class: "grow" }, "Narxi jami"), el("div", { class: "end" }, money(p.net_total))),
        p.paid_total ? el("div", { class: "row" }, el("div", { class: "grow" }, "Allaqachon olingan", p.paid_uzs ? el("div", { class: "sub" }, `${uzs(p.paid_uzs)} (o'sha kundagi kurs bilan)`) : null), el("div", { class: "end" }, "−" + money(p.paid_total))) : null,
        p.from_advance ? el("div", { class: "row" }, el("div", { class: "grow" }, "Umumiy to'lovdan ayriladi"), el("div", { class: "end" }, "−" + money(p.from_advance))) : null,
        el("div", { class: "row" }, el("div", { class: "grow" }, el("b", {}, p.to_receive < 0 ? "Ortiqcha to'langan" : "Olinadigan summa")), el("div", { class: "end" }, el("b", {}, money(Math.abs(p.to_receive))))),
        p.overpaid && p.overpaid.length ? el("div", { class: "unread-banner", style: "display:block" }, `⚠️ ${p.overpaid.length} ta mebelda narxdan ko'p pul olingan. Tasdiqlashdan oldin ro'yxatni tekshiring.`) : null,
        el("div", { class: "section-title" }, "Mebellar"),
        p.rows.map((r) => el("div", { class: "row" },
          el("div", { class: "grow" }, el("div", {}, r.serial ? `№${r.serial} · ` : "", el("b", {}, plabel(r)), ` × ${r.amount}`),
            el("div", { class: "sub" }, `${fdate(r.delivered_at)} · narxi ${money(r.net)}` + (r.paid_uzs ? ` · olindi ${uzs(r.paid_uzs)} = ${money(r.paid_usd)}` : r.paid_usd ? ` · olindi ${money(r.paid_usd)}` : ""))),
          el("div", { class: "end " + (r.paid_usd > r.net + 0.005 ? "neg" : "") }, money(r.net - r.paid_usd))))));
      const confirmBtn = el("button", { class: "btn", type: "button" }, "✅ Tasdiqlash: to'landi deb belgilash");
      confirmBtn.addEventListener("click", async () => {
        if (!(await confirmDlg(`${client}: ${fdate(p.from)} – ${fdate(p.to)} oralig'idagi ${p.count} ta mebel to'landi deb belgilansinmi? Buni qaytarib bo'lmaydi.`))) return;
        const r = await act(confirmBtn, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/settle_range`, { ...params(), confirm: true }),
          "Hisob-kitob qilindi");
        if (r) { close(); onDone(); }
      });
      result.appendChild(el("div", { class: "actions" }, confirmBtn));
    });
    return el("div", {}, el("h2", {}, "Sana bo'yicha to'landi"),
      last ? lastSettlementNote(last) : el("p", { class: "muted small" }, "Hali sana bo'yicha hisob-kitob qilinmagan."),
      el("p", { class: "muted small" }, "Shu sanalar oralig'ida yetkazilgan, hali yopilmagan mebellar to'landi bo'ladi."),
      field("Dan (yetkazilgan sana)", from), field("Gacha (shu kun ham kiradi)", to),
      el("div", { class: "actions" }, preview), result);
  });
}

function partialSheet(client, row, onDone) {
  sheet((close) => {
    const amountU = uzsInput({ autofocus: true });
    const note = el("input", { type: "text", maxlength: "200", placeholder: "Izoh (ixtiyoriy)" });
    const btn = el("button", { class: "btn", type: "button" }, "To'lovni saqlash");
    btn.addEventListener("click", async () => {
      const v = amountU.value();
      if (!v || v <= 0) { toast("Summani kiriting (ming so'mda).", true); return; }
      const r = await act(btn, () => api("POST", `/api/accounts/${encodeURIComponent(client)}/partial`,
        { uzs: v, order_id: row ? row.order_id : null, note: note.value }), "To'lov saqlandi");
      if (r) { close(); onDone(); }
    });
    return el("div", {}, el("h2", {}, "To'lov qabul qilish"),
      el("p", { class: "muted small" }, row ? `${client} · ${plabel(row)} × ${row.amount}` : `${client} · umumiy to'lov (qarzdan ayiriladi)`),
      field("Olingan summa (ming so'm)", amountU.node), field("Izoh", note), el("div", { class: "actions" }, btn));
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
        el("div", { class: "grow" }, el("b", {}, plabel(i)), el("div", { class: "bar" }, el("i", { style: `width:${Math.round(i.count / max * 100)}%` }))),
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
  holder.appendChild(el("div", { class: "actions" }, el("button", { class: "btn", type: "button", on: { click: () => userSheet(null) } }, "＋ Foydalanuvchi qo'shish")));
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
    // ID tahrirlanadi: noto'g'ri kiritilgan (masalan, telefon raqami yozilgan) ID ni to'g'rilash uchun
    const id = el("input", { type: "text", inputmode: "numeric", maxlength: "15", value: u ? u.id : "", readonly: u && u.owner ? true : null, placeholder: "Masalan: 123456789" });
    const name = el("input", { type: "text", maxlength: "80", value: u ? u.name : "", placeholder: "Masalan: Javohir (haydovchi)" });
    const role = el("select", {}, Object.entries(roles).map(([k, v]) => el("option", { value: k, selected: u && u.role === k ? true : null }, v)));
    const client = el("select", {}, el("option", { value: "" }, "— Kompaniyani tanlang —"),
      S.me.meta.clients.map((c) => el("option", { value: c, selected: u && u.client_name === c ? true : null }, c)));
    const clientField = field("Diller kompaniyasi", client);
    const sync = () => clientField.classList.toggle("hidden", role.value !== "diller");
    role.addEventListener("change", sync); sync();
    const delBtn = el("button", { class: "btn danger", type: "button" }, "Foydalanuvchini o'chirish");
    delBtn.addEventListener("click", async () => {
      if (!u || !(await confirmDlg(`${u.name || u.id} ro'yxatdan o'chirilsinmi? Ilovaga kira olmaydi. Eski buyurtma va hisob tarixi saqlanadi.`))) return;
      const r = await act(delBtn, () => api("DELETE", `/api/users/${encodeURIComponent(u.id)}`), "O'chirildi");
      if (r) { close(); refresh(); }
    });
    const btn = el("button", { class: "btn", type: "button" }, "Saqlash");
    btn.addEventListener("click", async () => {
      const newId = id.value.trim();
      if (!/^-?\d{3,15}$/.test(newId)) { toast("Telegram ID faqat raqamlardan iborat (botda /id yozib bilinadi).", true); id.focus(); return; }
      let uid = u ? u.id : newId;
      const r = await act(btn, async () => {
        if (u && (newId !== u.id || name.value.trim() !== (u.name || ""))) {
          if (newId !== u.id && !(await confirmDlg(`ID ${u.id} → ${newId} ga o'zgartirilsinmi? Rol, ism va boshqa ma'lumotlar yangi ID ga o'tadi.`))) return null;
          uid = (await api("PATCH", `/api/users/${encodeURIComponent(u.id)}`, { name: name.value.trim(), new_id: newId })).id;
        }
        return api("POST", "/api/users", { id: uid, role: role.value, client_name: client.value, name: u ? "" : name.value.trim() });
      }, "Saqlandi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, u ? (u.name || "Foydalanuvchi") : "Foydalanuvchi qo'shish"),
      field("Ismi", name), field("Telegram ID", id), field("Rol", role), clientField,
      u && u.phone ? el("p", { class: "muted small" }, `Telefon: +${u.phone}`) : null,
      el("p", { class: "muted small" }, "Telegram ID ni odam botga /id yozib biladi (telefon raqami emas!). Yangi rol 30 soniyagacha kuchga kiradi."),
      el("div", { class: "actions" }, btn),
      u && !u.owner ? el("div", { class: "actions" }, delBtn) : null);
  });
}

async function settingsSection(holder) {
  const s = await api("GET", "/api/settings");
  const block = (key, title, hint) => {
    const ta = el("textarea", { rows: "8" }, (s[key] || []).join("\n"));
    const btn = el("button", { class: "btn ghost", type: "button" }, "Saqlash");
    btn.addEventListener("click", async () => {
      const items = ta.value.split("\n").map((x) => x.trim()).filter(Boolean);
      const save = async (extra) => {
        const r = await act(btn, () => api("PUT", `/api/settings/${key}`, { items, ...extra }), `${title}: saqlandi`);
        if (r) { s[key] = r.items; S.me = await api("GET", "/api/me"); }
        return r;
      };
      if (key !== "models") { await save({}); return; }
      // Yangi model narxsiz saqlanmaydi: har biriga narx so'raymiz
      const norm = (x) => x.replace(/[\s-]/g, "").toUpperCase();
      const old = new Set((s.models || []).map(norm));
      const fresh = items.filter((x) => !old.has(norm(x)));
      if (!fresh.length) { await save({}); return; }
      sheet((close) => {
        const inputs = fresh.map((name) => [name, el("input", { type: "number", min: "0", step: "0.5", inputmode: "decimal", placeholder: "Narxi, $" })]);
        const ok = el("button", { class: "btn", type: "button" }, "Narxlar bilan saqlash");
        ok.addEventListener("click", async () => {
          const prices = {};
          for (const [name, inp] of inputs) {
            if (!(Number(inp.value) > 0)) { toast(`${name}: narxini kiriting.`, true); inp.focus(); return; }
            prices[name] = Number(inp.value);
          }
          if (await save({ prices })) close();
        });
        return el("div", {}, el("h2", {}, "Yangi model narxi"),
          el("p", { class: "muted small" }, "Yangi mebel modeli narxsiz saqlanmaydi. 1 dona narxini kiriting."),
          inputs.map(([name, inp]) => field(name, inp)), el("div", { class: "actions" }, ok));
      });
    });
    return el("div", {}, el("div", { class: "section-title" }, title), el("p", { class: "muted small", style: "margin:0 4px 6px" }, hint),
      ta, el("div", { class: "actions" }, btn));
  };
  holder.appendChild(block("clients", "Dillerlar ro'yxati", "Har qatorda bitta nom. Botdagi tanlov tugmalari shu ro'yxatdan olinadi."));
  holder.appendChild(block("drivers", "Haydovchilar", "Har qatorda bitta ism."));
  holder.appendChild(block("models", "Mebel modellari", "Botdagi tanlov tugmalari tartibi."));
  holder.appendChild(block("variants", "Buyurtma variantlari", "Yangi buyurtmada «Tanlang» tugmasi ostidagi variantlar (masalan: Matrasli, Kapotli). Tanlanmasa — bazoviy."));
}

/* ================= YETKAZILGANLAR HISOBOTI (admin) ================= */
/* Fayl Authorization sarlavhasisiz ochilishi uchun bir martalik qisqa havola olinadi */
async function openFile(path, filename) {
  const url = location.origin + path;
  if (window.MMebelApp && window.MMebelApp.openExternal) { window.MMebelApp.openExternal(url); return; }  // Android ilova
  if (IN_TELEGRAM && tg.openLink) { tg.openLink(url); return; }
  const res = await fetch(url);
  if (!res.ok) throw new Error("Faylni yuklab bo'lmadi.");
  const blobUrl = URL.createObjectURL(await res.blob());
  const a = el("a", { href: blobUrl, download: filename });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast("Nusxa olindi — Excel yoki Telegram'ga joylashtiring"); return; } catch (_) { /* quyida */ }
  sheet(() => {
    const ta = el("textarea", { rows: "12", readonly: true }, text);
    setTimeout(() => { ta.focus(); ta.select(); }, 50);
    return el("div", {}, el("h2", {}, "Nusxa olish"), el("p", { class: "muted small" }, "Matnni belgilab, «Nusxa olish» ni bosing."), ta);
  });
}
function reportSheet(client) {
  sheet((close) => {
    let unsettled = true;
    const from = el("input", { type: "date" });
    const to = el("input", { type: "date", max: isoToday() });
    const info = el("p", { class: "muted small" }, "");
    const preview = el("div");
    const params = () => ({ client, from: from.value, to: to.value, unsettled: unsettled ? "1" : "" });
    const load = async () => {
      info.textContent = "Yuklanmoqda…";
      try {
        const q = new URLSearchParams(params()).toString();
        const d = await api("GET", `/api/reports/delivered?${q}`);
        info.textContent = `${d.items.length} ta mebel · tartib raqami bo'yicha`;
        clear(preview).appendChild(d.items.length ? el("div", { class: "list" }, d.items.slice(0, 50).map((r) => el("div", { class: "row" },
          el("div", { class: "grow" }, el("div", {}, r.serial ? el("span", { class: "serial" }, `№${r.serial}`) : "— ", plabel({ product_id: r.product, variant: r.variant })),
            el("div", { class: "sub" }, `${fdate(r.delivered_at)}${r.settled ? " · ✅ hisob-kitob" : ""}`)),
          el("div", { class: "end" }, money(r.price), el("div", { class: "sub" }, `olindi ${money(r.collected)}`))))) : empty("Ro'yxat bo'sh."));
        preview.dataset.text = d.text;
      } catch (e) { info.textContent = e.message; }
    };
    const download = (format) => async (e) => {
      await act(e.target, async () => {
        const r = await api("POST", "/api/reports/delivered/link", { ...params(), unsettled: unsettled, format });
        await openFile(r.url, `${client}_yetkazilgan.${format}`);
      });
    };
    from.addEventListener("change", load); to.addEventListener("change", load);
    const kind = chips(["unsettled", "all"], "unsettled", (v) => { unsettled = v === "unsettled"; load(); },
      (v) => (v === "unsettled" ? "Hisob-kitob qilinmagan" : "Hammasi"));
    load();
    return el("div", {}, el("h2", {}, `${client} — yetkazilganlar`),
      field("Qaysilari", kind),
      el("div", { class: "actions two", style: "margin-top:0" }, field("Dan (yetkazilgan)", from), field("Gacha", to)),
      info,
      el("div", { class: "actions" },
        el("button", { class: "btn", type: "button", on: { click: download("pdf") } }, "📄 PDF yuklab olish (A4)"),
        el("div", { class: "actions two", style: "margin-top:0" },
          el("button", { class: "btn ghost", type: "button", on: { click: () => (preview.dataset.text ? copyText(preview.dataset.text) : toast("Ro'yxat hali yuklanmadi.", true)) } }, "📋 Nusxa olish"),
          el("button", { class: "btn ghost", type: "button", on: { click: download("csv") } }, "📊 Excel (CSV)"))),
      preview);
  });
}

/* ================= MEBEL YIG'UVCHILAR (admin / omborchi) ================= */
async function viewWorkers(target) {
  const d = await api("GET", "/api/workers");
  const view = target || clear($("view"));
  clear(view);
  const isAdmin = S.me.role === "admin";
  view.appendChild(el("div", { class: "stats" },
    el("div", { class: "stat wide" + (d.total_cash ? " late" : "") }, el("b", {}, money(d.total_cash)), el("span", {}, "Topshirilmagan naqd pul (jami)")),
    el("div", { class: "stat" }, el("b", {}, d.month_delivered), el("span", {}, `Shu oy topshirildi (${d.month})`)),
    el("div", { class: "stat" }, el("b", {}, money(d.month_cash)), el("span", {}, "Shu oy naqd")),
    el("div", { class: "stat wide" }, el("b", {}, money(d.month_card)), el("span", {}, "Shu oy karta orqali"))));
  // Tasdiqlash kutayotgan topshirishlar
  const pending = (d.pending || []).filter((t) => t.from_holder !== `u_${S.me.id}`);
  if (pending.length) {
    view.appendChild(el("div", { class: "section-title" }, `Tasdiqlash kutilmoqda — ${pending.length} ta`));
    view.appendChild(el("div", { class: "list" }, pending.map((t) => {
      const canResolve = isAdmin || t.to_role === S.me.role;
      const row = el("div", { class: "row", style: "flex-wrap:wrap" },
        el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, `${t.from_name} → ${t.to_role === "admin" ? "admin" : "omborchi"}`),
          el("div", { class: "sub" }, `${t.from_kind === "worker" ? "Mebel yig'uvchi" : "Omborchi"} · ${fdate(t.ts)}`)),
        el("div", { class: "end" }, el("b", {}, money(t.amount))));
      if (canResolve) {
        const resolve = (approve) => async (e) => {
          if (!(await confirmDlg(approve ? `Siz ${t.from_name} dan ${money(t.amount)} oldingizmi? Tasdiqlaysizmi?` : `${t.from_name}: ${money(t.amount)} rad etilsinmi?`))) return;
          const r = await act(e.target, () => api("POST", `/api/cash/transfers/${encodeURIComponent(t.id)}/resolve`, { approve }),
            approve ? "Tasdiqlandi" : "Rad etildi");
          if (r) refresh();
        };
        row.appendChild(el("div", { class: "actions two", style: "width:100%;margin-top:6px" },
          el("button", { class: "btn", type: "button", on: { click: resolve(true) } }, "✅ Tasdiqlash"),
          el("button", { class: "btn danger", type: "button", on: { click: resolve(false) } }, "Rad etish")));
      }
      return row;
    })));
  }
  // Omborchining o'z kassasi (yig'uvchilardan qabul qilgani) -> adminga
  if (S.me.role === "omborchi") {
    view.appendChild(el("div", { class: "section-title" }, "Mening kassam"));
    const row = el("div", { class: "row", style: "flex-wrap:wrap" },
      el("div", { class: "grow" }, "Yig'uvchilardan qabul qilingan, adminga topshirilmagan",
        d.my_pending ? el("div", { class: "sub" }, `⏳ ${money(d.my_pending.amount)} adminga topshirildi — tasdiq kutilmoqda`) : null),
      el("div", { class: "end" }, el("b", {}, money(d.my_cash || 0))));
    if (d.my_cash > 0 && !d.my_pending) row.appendChild(el("div", { class: "actions", style: "width:100%;margin-top:6px" },
      el("button", { class: "btn", type: "button", on: { click: () => cashTransferSheet(d.my_cash, ["admin"], "/api/cash/transfer") } }, "Adminga topshirish")));
    view.appendChild(el("div", { class: "list" }, row));
  } else if ((d.staff || []).length) {
    view.appendChild(el("div", { class: "section-title" }, "Omborchilar kassasi"));
    view.appendChild(el("div", { class: "list" }, d.staff.map((s) => el("div", { class: "row" },
      el("div", { class: "grow" }, s.name), el("div", { class: "end" }, el("b", {}, money(s.cash)))))));
  }
  view.appendChild(el("div", { class: "section-title" }, `Yig'uvchilar — ${d.workers.length}`));
  view.appendChild(el("div", { class: "actions" }, el("button", { class: "btn ghost", type: "button", on: { click: newWorkerSheet } }, "＋ Yig'uvchi qo'shish")));
  if (!d.workers.length) view.appendChild(empty("Hali yig'uvchi yo'q. «＋ Yig'uvchi qo'shish» ni bosing."));
  view.appendChild(el("div", { class: "list" }, d.workers.map((w) => el("button", { class: "row" + (w.active ? "" : " muted"), type: "button", on: { click: () => workerSheet(w.id) } },
    el("div", { class: "grow" }, el("div", { style: "font-weight:600" }, w.name, w.active ? "" : " (o'chirilgan)"),
      el("div", { class: "sub" }, [`${w.assigned} ta yig'ishda`, `shu oy ${w.month_delivered} ta`, w.linked ? null : "⚠️ botga kirmagan"].filter(Boolean).join(" · "))),
    el("div", { class: "end " + (w.cash > 0 ? "pos" : "muted") }, money(w.cash))))));
  view.appendChild(el("p", { class: "muted small", style: "margin:6px 4px" },
    "O'ngdagi summa — yig'uvchi qo'lidagi naqd pul (sexga topshirishi kerak). Karta orqali to'lovlar bunga qo'shilmaydi."));
}

function newWorkerSheet() {
  sheet((close) => {
    const name = el("input", { type: "text", maxlength: "60", placeholder: "Masalan: Javohir", "data-autofocus": "" });
    const phone = el("input", { type: "tel", maxlength: "20", placeholder: "+998 90 123 45 67" });
    const btn = el("button", { class: "btn", type: "button" }, "Profil ochish");
    btn.addEventListener("click", async () => {
      const r = await act(btn, () => api("POST", "/api/workers", { name: name.value.trim(), phone: phone.value.trim() }), "Yig'uvchi qo'shildi");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "Yangi mebel yig'uvchi"),
      field("Ismi", name), field("Telefon raqami (Telegram'dagi)", phone),
      el("p", { class: "muted small" }, "Yig'uvchi botga /start yozib, «📱 Raqamni ulashish» tugmasini bossa — profil avtomatik bog'lanadi va ilovaga shu raqam bilan kiradi."),
      el("div", { class: "actions" }, btn));
  });
}

async function workerSheet(wid) {
  let w;
  try { w = await api("GET", `/api/workers/${encodeURIComponent(wid)}`); } catch (e) { toast(e.message, true); return; }
  sheet((close) => {
    const box = el("div", {}, el("h2", {}, w.name),
      el("p", { class: "muted small" }, `+${w.phone || "—"} · ${w.linked ? "✅ botga ulangan" : "⚠️ hali botga kirmagan"}`),
      el("div", { class: "code-big " + (w.cash > 0 ? "pos" : "") }, money(w.cash)),
      el("p", { class: "muted small" }, "Qo'lidagi naqd pul — sexga topshirishi kerak"));
    if (S.me.role === "admin") {
      box.appendChild(el("div", { class: "actions" }, el("button", { class: "btn ghost", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(w.active ? `${w.name} profili o'chirilsinmi? Yangi mebel yuborib bo'lmaydi.` : `${w.name} profili qayta yoqilsinmi?`))) return;
        const r = await act(e.target, () => api("PATCH", `/api/workers/${encodeURIComponent(wid)}`, { active: !w.active }), "Saqlandi");
        if (r) { close(); refresh(); }
      } } }, w.active ? "Profilni o'chirish" : "Profilni yoqish")));
    }
    box.appendChild(el("div", { class: "section-title" }, `Yig'ishda — ${w.active_orders.length} ta`));
    box.appendChild(w.active_orders.length ? el("div", { class: "list" }, w.active_orders.map((o) => el("div", { class: "row" },
      el("div", { class: "grow" }, el("b", {}, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)}`), ` × ${o.amount}`, el("div", { class: "sub" }, `${o.client_name} · yuborildi ${fdate(o.assigned_at)}`)),
      el("div", { class: "end" }, o.collect != null ? money(o.collect) : "—")))) : empty("Hozir yig'ishda mebel yo'q."));
    box.appendChild(el("div", { class: "section-title" }, "Mijozlardan olingan to'lovlar"));
    box.appendChild(w.payments.length ? payList(w.payments, true) : empty("Hali to'lov yo'q."));
    box.appendChild(el("div", { class: "section-title" }, "Kassa tarixi"));
    box.appendChild(cashLogList(w.log));
    return box;
  });
}

function cashLogList(log) {
  if (!log.length) return empty("Tarix bo'sh.");
  return el("div", { class: "list" }, log.map((h) => el("div", { class: "row" },
    el("div", { class: "grow" }, h.text || h.kind, el("div", { class: "sub" }, `${fdate(h.ts)} · qoldiq ${money(h.balance)}`)),
    el("div", { class: "end " + (h.amount < 0 ? "neg" : "pos") }, (h.amount > 0 ? "+" : "−") + money(Math.abs(h.amount))))));
}

function cashTransferSheet(balance, targets, path) {
  sheet((close) => {
    let to = targets.length === 1 ? targets[0] : null;
    const amount = el("input", { type: "number", min: "0.01", step: "0.01", inputmode: "decimal", value: balance });
    const btn = el("button", { class: "btn", type: "button" }, "Topshirish");
    btn.addEventListener("click", async () => {
      if (!to) { toast("Kimga topshirishni tanlang.", true); return; }
      const v = Number(amount.value);
      if (!(v > 0)) { toast("Summani kiriting.", true); return; }
      if (!(await confirmDlg(`${money(v)} ${to === "admin" ? "adminga" : "omborchiga"} topshirilsinmi? U tasdiqlagach kassangizdan ayiriladi.`))) return;
      const r = await act(btn, () => api("POST", path, { to, amount: v }), "Yuborildi. Tasdiqlashni kuting.");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "Qarzni topshirish"),
      el("p", { class: "muted small" }, `Kassangizda: ${money(balance)}`),
      targets.length > 1 ? field("Kimga topshirasiz?", chips(targets, null, (v) => { to = v; }, (v) => (v === "admin" ? "👤 Adminga" : "📦 Omborchiga"))) : null,
      field("Summa ($)", amount), el("div", { class: "actions" }, btn));
  });
}

/* ================= YIG'UVCHI PANELI ================= */
async function viewWHome() {
  const [d] = await Promise.all([api("GET", "/api/w/me"), loadUnread()]);
  markSeen();
  const view = clear($("view"));
  view.appendChild(el("button", { class: "stat wide" + (d.cash > 0 ? " late" : ""), type: "button", style: "width:100%", on: { click: () => go("w_cash") } },
    el("b", {}, money(Math.abs(d.cash))), el("span", {}, d.cash < 0 ? "Sex sizga qarzdor (xarajatlar)" : "Sexga topshirishingiz kerak (naqd)")));
  view.appendChild(el("div", { class: "section-title" }, `Yig'ish uchun yuborilgan — ${d.active.length} ta`));
  if (!d.active.length) view.appendChild(empty("Hozircha sizga yuborilgan mebel yo'q."));
  view.appendChild(el("div", { class: "list" }, d.active.map((o) => {
    const tag = o.ret && o.ret.status === "pending" ? "⏳ skladga qaytarish tasdiqlanmoqda"
      : o.defect && o.defect.open ? "⚠️ kamchilikni tuzatish" : null;
    const due = o.left_uzs != null ? o.left_uzs : o.collect_uzs;
    return el("button", { class: "row", type: "button", on: { click: () => wOrderSheet(o) } },
      el("div", { class: "grow" }, el("div", {}, o.serial ? el("span", { class: "serial" }, `№${o.serial}`) : null, el("b", {}, plabel(o)), ` × ${o.amount}`),
        el("div", { class: "sub" }, [tag, o.client_name, o.comment].filter(Boolean).join(" · "))),
      el("div", { class: "end" }, due != null ? el("b", {}, uzs(due)) : "—"));
  })));
  if (d.done.length) {
    view.appendChild(el("div", { class: "section-title" }, "Topshirilganlar"));
    view.appendChild(el("div", { class: "list" }, d.done.map((o) => {
      const pend = (o.payments || []).some((p) => p.edit_req && p.edit_req.status === "pending");
      return el("button", { class: "row", type: "button", on: { click: () => wDoneSheet(o) } },
        el("div", { class: "grow" }, el("div", {}, o.serial ? el("span", { class: "serial" }, `№${o.serial}`) : null, el("b", {}, plabel(o))),
          el("div", { class: "sub" }, [fdate(o.delivered_at), o.client_name, o.defect && o.defect.open ? "⚠️ tugallanmagan" : (o.handover && o.handover.correct === false ? "⚠️ chala" : null),
            pend ? "⏳ tuzatish tasdiqlanmoqda" : null].filter(Boolean).join(" · "))),
        el("div", { class: "end" }, money(o.paid), el("div", { class: "sub" }, o.method === "karta" ? "💳" : o.method ? "💵" : "")));
    })));
  }
}

function wOrderSheet(o) {
  sheet((close) => {
    const pendingRet = o.ret && o.ret.status === "pending";
    const defect = o.defect && o.defect.open;
    const kv = el("dl", { class: "kv" },
      el("dt", {}, "Diller"), el("dd", {}, o.client_name || "—"),
      o.comment ? [el("dt", {}, "Izoh"), el("dd", {}, o.comment)] : null,
      el("dt", {}, "Olinadigan qoldiq"), el("dd", {}, o.left_uzs != null ? el("b", {}, uzs(o.left_uzs)) : o.collect != null ? el("b", {}, money(o.collect)) : "Belgilanmagan"),
      el("dt", {}, "Yuborildi"), el("dd", {}, fdate(o.assigned_at)));
    const box = el("div", {}, el("div", { class: "code-big" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)} × ${o.amount}`));
    // Tugallanmagan mebel: oldingi yig'uvchi izohi va qolgan summa
    if (defect) {
      box.appendChild(el("div", { class: "unread-banner", style: "display:block" },
        el("b", {}, "⚠️ Kamchilikni tuzatish kerak"),
        (o.defect.history || []).map((h) => el("div", { class: "small", style: "margin-top:4px" }, `${fdate(h.at)} · ${h.worker_name}: ${h.note}`)),
        o.left_uzs != null ? el("div", { style: "margin-top:6px" }, "Sizga qolgan ", el("b", {}, uzs(o.left_uzs)), " ni olish kerak.") : null));
    }
    box.appendChild(kv);
    const actions = el("div", { class: "actions" });
    if (pendingRet) {
      actions.appendChild(el("p", { class: "muted" }, `⏳ Skladga qaytarish tasdiqlanishi kutilmoqda${o.ret.expense ? " (xarajat " + money(o.ret.expense) + ")" : ""}.`));
    } else {
      actions.append(
        el("button", { class: "btn", type: "button", on: { click: () => { close(); handoverSheet(o, defect ? "complete" : "handover"); } } }, "✅ Mebel mijozga topshirildi"),
        el("button", { class: "btn ghost", type: "button", on: { click: () => { close(); handoverSheet(o, "defect"); } } }, "⚠️ Mebelda kamchilik aniqlandi"));
      if (!defect) actions.appendChild(el("button", { class: "btn ghost", type: "button", on: { click: () => { close(); returnSheet(o); } } }, "↩️ Skladga qaytdi"));
    }
    box.appendChild(actions);
    return box;
  });
}

/* «Skladga qaytdi» — faqat izoh. Admin/omborchi tasdiqlaydi */
function returnSheet(o) {
  sheet((close) => {
    const note = el("textarea", { maxlength: "500", placeholder: "Nima uchun qaytdi" });
    const save = el("button", { class: "btn", type: "button" }, "Saqlash");
    save.addEventListener("click", async () => {
      const r = await act(save, () => api("POST", `/api/w/orders/${encodeURIComponent(o.id)}/return`,
        { expense_yes: false, note: note.value.trim() }), "Yuborildi. Tasdiqlashni kuting.");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "Skladga qaytdi"),
      el("p", { class: "muted small" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)} · ${o.client_name}`),
      field("Izoh", note),
      el("div", { class: "actions" }, save));
  });
}

function wDoneSheet(o) {
  sheet((close) => {
    const box = el("div", {},
      el("div", { class: "code-big" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)}`),
      el("dl", { class: "kv" },
        el("dt", {}, "Diller"), el("dd", {}, o.client_name),
        el("dt", {}, "Topshirildi"), el("dd", {}, fdate(o.delivered_at)),
        el("dt", {}, "Kutilgan qoldiq"), el("dd", {}, o.collect != null ? money(o.collect) : "—"),
        el("dt", {}, "Olingan (jami)"), el("dd", {}, el("b", {}, money(o.paid)))));
    const mine = o.payments || [];
    if (mine.length) {
      box.appendChild(el("div", { class: "section-title" }, "Siz kiritgan to'lovlar"));
      box.appendChild(el("div", { class: "list" }, mine.map((p) => {
        const pend = p.edit_req && p.edit_req.status === "pending";
        return el("div", { class: "row", style: "flex-wrap:wrap" },
          el("div", { class: "grow" }, el("b", {}, money(p.amount)), ` · ${p.method === "karta" ? "💳 karta" : "💵 naqd"}`,
            el("div", { class: "sub" }, [fdate(p.ts), pend ? `⏳ ${money(p.edit_req.old_amount)} → ${money(p.edit_req.new_amount)} tasdiqlanmoqda`
              : p.edit_req && p.edit_req.status === "rejected" ? "❌ oxirgi tuzatish rad etilgan" : null].filter(Boolean).join(" · "))),
          pend ? null : el("button", { class: "btn ghost", type: "button", style: "width:auto;padding:6px 12px", on: { click: () => { close(); payEditSheet(p); } } }, "✏️ Tahrirlash"));
      })));
    }
    box.appendChild(el("div", { class: "actions" }, el("button", { class: "btn ghost", type: "button", on: { click: () => { close(); handoverSheet(o, "extra"); } } }, "💵 Mijoz qolgan pulni berdi")));
    return box;
  });
}

/* Olingan summani tuzatish — admin/omborchi tasdiqlagach kuchga kiradi */
function payEditSheet(p) {
  sheet((close) => {
    const soum = p.uzs != null;     // so'mda olingan to'lov: «ming so'm»da tuzatiladi
    const amountU = uzsInput({ value: soum ? p.uzs / 1000 : p.amount });
    const amount = amountU.input;
    const note = el("textarea", { maxlength: "300", placeholder: "Nima uchun o'zgartiryapsiz" });
    const save = el("button", { class: "btn", type: "button" }, "Tasdiqlashga yuborish");
    save.addEventListener("click", async () => {
      if (amount.value === "" || Number(amount.value) < 0) { toast("Summani kiriting.", true); return; }
      if (!note.value.trim()) { toast("Sababini yozing.", true); note.focus(); return; }
      const r = await act(save, () => api("POST", `/api/w/pay/${encodeURIComponent(p.pay_id)}/edit`,
        { amount: Number(amount.value), note: note.value.trim() }), "Yuborildi. Tasdiqlangach o'zgaradi.");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "Olingan summani tuzatish"),
      el("p", { class: "muted small" }, `Hozir: ${soum ? uzs(p.uzs) : money(p.amount)} (${p.method === "karta" ? "karta" : "naqd"})`),
      field(soum ? "Mijozdan olingan summa (ming so'm)" : "Mijozdan olingan summa ($)", soum ? amountU.node : amount), field("Sabab", note),
      el("p", { class: "muted small" }, "Admin yoki omborchi tasdiqlagandan keyingina hisob o'zgaradi."),
      el("div", { class: "actions" }, save));
  });
}

/* Rasmni telefonda kichraytirib (≤1600px, JPEG) yuklaymiz — tez va 5 MB dan oshmaydi */
async function compressImage(file) {
  // Android WebView ba'zi fayllar uchun type ni bo'sh beradi — bunda ruxsat beramiz, rasm ekanini dekoder aniqlaydi
  if (file.type && !/^image\//.test(file.type)) throw new Error(`Faqat rasm yuklash mumkin (${file.type}).`);
  if (!file.size) throw new Error("Rasm o'qilmadi (hajmi 0). Boshqa rasm tanlang.");
  const bmp = await (window.createImageBitmap ? createImageBitmap(file).catch(() => null) : null);
  const src = bmp || await new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("Rasm ochilmadi.")); i.src = URL.createObjectURL(file); });
  const k = Math.min(1, 1600 / Math.max(src.width, src.height));
  const c = document.createElement("canvas");
  c.width = Math.round(src.width * k); c.height = Math.round(src.height * k);
  c.getContext("2d").drawImage(src, 0, 0, c.width, c.height);
  const blob = await new Promise((res) => c.toBlob(res, "image/jpeg", 0.82));
  if (!blob) throw new Error("Rasmni tayyorlab bo'lmadi.");
  if (blob.size > 5 * 1024 * 1024) throw new Error("Rasm hajmi 5 MB dan oshmasin.");
  return blob;
}
async function uploadPhoto(blob) {
  const auth = IN_TELEGRAM ? "tma " + tg.initData : (getToken() ? "Bearer " + getToken() : "");
  let res;
  try { res = await fetch("/api/w/photos", { method: "POST", headers: { Authorization: auth, "Content-Type": "image/jpeg" }, body: blob }); }
  catch (_) { throw new Error("Internet aloqasi yo'q."); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Xato (${res.status})`);
  return data.key;
}

/* mode: "handover" — «Mebel mijozga topshirildi» (Qoldiq to'g'ri olindimi? Ha/Yo'q);
   "complete" — tugallanmagan mebelni tugatish (qolgan summa bilan); "defect" — kamchilik + qisman pul;
   "extra" — mijoz qolgan pulni keyin berdi */
function handoverSheet(o, mode) {
  const extra = mode === "extra", defectMode = mode === "defect";
  const expected = o.left_uzs != null ? o.left_uzs : o.collect_uzs;   // so'm; tugallanmaganda: kutilgan − oldin olingan
  sheet((close) => {
    let correct = extra ? true : defectMode ? false : null;
    let card = false;
    const photos = [];  // {blob, url}
    const amountU = uzsInput();
    const amount = amountU.input;
    if (defectMode && expected != null) amount.max = String(expected / 1000);
    const note = el("textarea", { maxlength: "500", placeholder: defectMode ? "Masalan: fasad tirnalgan, fabrikaga qaytarish kerak" : "Qo'shimcha izoh" });
    const noteLabel = el("span", {}, defectMode ? "Kamchilik nima? (majburiy)" : "Qo'shimcha izoh");
    const form = el("div", { class: extra || defectMode ? "" : "hidden" });
    const thumbs = el("div", { class: "thumbs" });
    // Rasm tanlash: tugma ichiga shaffof input qo'yilgan — foydalanuvchi bevosita inputni bosadi (JS click() ishonchsiz)
    const fileInput = el("input", { type: "file", accept: "image/*", multiple: true, class: "file-overlay", "aria-label": "Skrinshot tanlash" });
    const addPhoto = el("label", { class: "btn ghost file-btn" }, "📷 Skrinshot qo'shish (1–5 ta)", fileInput);
    const drawThumbs = () => {
      clear(thumbs);
      photos.forEach((p, i) => thumbs.appendChild(el("div", { class: "thumb-wrap" }, el("img", { class: "thumb", src: p.url, alt: `Rasm ${i + 1}` }),
        el("button", { class: "thumb-x", type: "button", "aria-label": "O'chirish", on: { click: () => { URL.revokeObjectURL(p.url); photos.splice(i, 1); drawThumbs(); } } }, "×"))));
      fileInput.disabled = photos.length >= 5;
      addPhoto.classList.toggle("is-disabled", photos.length >= 5);
    };
    fileInput.addEventListener("change", async () => {
      for (const f of Array.from(fileInput.files || [])) {
        if (photos.length >= 5) { toast("Ko'pi bilan 5 ta rasm.", true); break; }
        try { const blob = await compressImage(f); photos.push({ blob, url: URL.createObjectURL(blob) }); } catch (e) { toast(`${e.message} [${f.name || "?"}, ${f.type || "tur yo'q"}, ${f.size}B]`, true); }
      }
      fileInput.value = "";
      drawThumbs();
    });
    const cardBox = el("div", { class: "hidden" }, addPhoto, thumbs);
    const cardBtn = el("button", { class: "btn ghost", type: "button", "aria-pressed": "false" }, "💳 To'lov karta orqali amalga oshirildi");
    cardBtn.addEventListener("click", () => {
      card = !card;
      cardBtn.setAttribute("aria-pressed", String(card));
      cardBox.classList.toggle("hidden", !card);
    });
    const pick = (v) => {
      correct = v;
      form.classList.remove("hidden");
      if (v && expected != null && amount.value === "") amount.value = expected;
      if (!v) amount.value = "";
      noteLabel.textContent = v ? "Qo'shimcha izoh" : "Nima uchun farq bor? (majburiy)";
      note.placeholder = v ? "Qo'shimcha izoh" : "Masalan: chala ish qolgani uchun mijoz hamma pulni bermadi";
      amount.focus();
    };
    const save = el("button", { class: "btn", type: "button" }, "Saqlash");
    save.addEventListener("click", async () => {
      if (correct === null) { toast("«Ha» yoki «Yo'q» ni tanlang.", true); return; }
      const v = amount.value === "" ? NaN : Number(amount.value);
      if (isNaN(v) || v < 0) { toast("Olingan summani kiriting (olinmagan bo'lsa 0).", true); amount.focus(); return; }
      if (defectMode && expected != null && Math.round(v * 1000) > expected) { toast(`Qoldiq ${uzs(expected)} — undan ko'p yozib bo'lmaydi.`, true); return; }
      if (!correct && !note.value.trim()) { toast(defectMode ? "Kamchilikni izohga yozing." : "Farq sababini izohga yozing.", true); note.focus(); return; }
      if (card && v > 0 && !photos.length) { toast("Karta to'lovi uchun skrinshot yuklang.", true); return; }
      save.disabled = true;
      try {
        const keys = [];
        for (let i = 0; i < photos.length; i++) { save.textContent = `Rasm yuklanmoqda ${i + 1}/${photos.length}…`; keys.push(await uploadPhoto(photos[i].blob)); }
        save.textContent = "Saqlanmoqda…";
        const body = { amount: v, method: card ? "karta" : "naqd", note: note.value.trim(), photos: keys };
        const base = `/api/w/orders/${encodeURIComponent(o.id)}`;
        if (extra) await api("POST", `${base}/payment`, body);
        else if (defectMode) await api("POST", `${base}/defect`, body);
        else await api("POST", `${base}/handover`, { ...body, correct });
        toast(extra ? "To'lov saqlandi" : defectMode ? "Saqlandi. Admin/omborchi qayta yuboradi." : "Topshirildi. Rahmat!");
        close(); refresh();
      } catch (e) { toast(e.message, true); }
      finally { save.disabled = false; save.textContent = "Saqlash"; }
    });
    const amountLabel = defectMode ? `Mijozdan qisman olingan pul (ming so'm)${expected != null ? " — ko'pi bilan " + uzs(expected) : ""}`
      : extra ? "Olingan summa (ming so'm)" : "Olingan summa (ming so'm) — olinmagan bo'lsa 0";
    form.append(field(amountLabel, amountU.node), el("label", { class: "field" }, noteLabel, note), cardBtn, cardBox, el("div", { class: "actions" }, save));
    const title = extra ? "Qo'shimcha to'lov" : defectMode ? "Mebelda kamchilik aniqlandi" : "Mebel mijozga topshirildi";
    return el("div", {}, el("h2", {}, title),
      el("p", { class: "muted small" }, `${o.serial ? "№" + o.serial + " · " : ""}${plabel(o)} · ${o.client_name}`),
      expected != null && !extra ? el("p", {}, mode === "complete" || defectMode ? "Hozirgi qoldiq: " : "Olinadigan qoldiq: ", el("b", {}, uzs(expected))) : null,
      extra || defectMode ? null : el("div", {}, el("p", { style: "font-weight:600;margin:8px 2px" }, "Mebelning qoldiq summasi to'g'ri olindimi?"),
        chips([true, false], null, pick, (x) => (x ? "✅ Ha" : "❌ Yo'q"))),
      form);
  });
}

async function viewWCash() {
  const d = await api("GET", "/api/w/me");
  const view = clear($("view"));
  view.appendChild(el("div", { class: "code-big " + (d.cash > 0 ? "pos" : "") }, money(Math.abs(d.cash))));
  view.appendChild(el("p", { class: "muted small", style: "text-align:center" }, d.cash < 0
    ? "Sex sizga qarzdor (tasdiqlangan xarajatlar)" : "Qo'lingizdagi naqd pul — sexga topshirishingiz kerak"));
  if (d.pending_transfer) {
    view.appendChild(el("div", { class: "unread-banner" }, el("b", {}, `⏳ ${money(d.pending_transfer.amount)} ${d.pending_transfer.to_role === "admin" ? "adminga" : "omborchiga"} topshirildi`),
      el("span", {}, " — tasdiqlanishi kutilmoqda")));
  } else if (d.cash > 0) {
    view.appendChild(el("div", { class: "actions" }, el("button", { class: "btn", type: "button",
      on: { click: () => cashTransferSheet(d.cash, ["omborchi", "admin"], "/api/w/transfer") } }, "💰 Qarzni topshirish")));
  }
  view.appendChild(el("div", { class: "section-title" }, "Hisob-kitob tarixi"));
  view.appendChild(cashLogList(d.log));
}

/* ================= DILLER PANELI ================= */
function dOrderCard(o) {
  const done = !ACTIVE.includes(o.status);
  const isNew = !!S.unread[o.id];
  return el("button", { type: "button", class: `order ${edgeClass(o.status)}${o.overdue ? " late" : ""}${isNew ? " unread" : ""}`,
    on: { click: (e) => { if (isNew) { markSeen([o.id]); e.currentTarget.classList.remove("unread"); e.currentTarget.querySelector(".newtag")?.remove(); } dOrderSheet(o); } } },
    unreadTag(o),
    el("div", {}, el("span", { class: "code" }, plabel(o)), el("span", { class: "qty" }, `× ${o.amount}`),
      el("span", { style: "margin-left:8px" }, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status))),
    el("div", { class: "line2" },
      el("span", { class: "client" }, o.total_price ? money(o.total_price) : (o.own ? "Siz bergansiz" : "Zavod yaratgan")),
      el("span", { class: "due" }, done ? fdate(o.delivered_at || o.created_at) : `📅 ${fdate(o.due_date)}`)),
    o.comment ? el("div", { class: "note" }, "📝 " + o.comment) : null);
}

function dOrderSheet(o) {
  sheet((close) => {
    const kv = el("dl", { class: "kv" },
      el("dt", {}, "Holati"), el("dd", {}, el("span", { class: `badge ${edgeClass(o.status)}` }, o.status)),
      el("dt", {}, "Soni"), el("dd", {}, `${o.amount} ta`),
      el("dt", {}, "Muddat"), el("dd", { class: o.overdue ? "pos" : "" }, fdate(o.due_date)),
      o.total_price ? [el("dt", {}, "Narxi"), el("dd", {}, `${money(o.price)} × ${o.amount} = ${money(o.total_price)}`)] : null,
      o.comment ? [el("dt", {}, "Izoh"), el("dd", {}, o.comment)] : null,
      o.driver ? [el("dt", {}, "Yetkazdi"), el("dd", {}, o.driver)] : null,
      o.delivered_at ? [el("dt", {}, "Yetkazilgan"), el("dd", {}, fdate(o.delivered_at))] : null,
      el("dt", {}, "Berilgan"), el("dd", {}, `${fdate(o.created_at)} · ${o.own ? "siz" : "zavod"}`),
      el("dt", {}, "ID"), el("dd", { class: "small muted" }, o.id));
    const actions = el("div", { class: "actions" });
    if (o.can_cancel) {
      actions.appendChild(el("button", { class: "btn danger", type: "button", on: { click: async (e) => {
        if (!(await confirmDlg(`${plabel(o)} × ${o.amount} zakazini bekor qilasizmi?`))) return;
        const r = await act(e.target, () => api("POST", `/api/d/orders/${encodeURIComponent(o.id)}/cancel`), "Zakaz bekor qilindi");
        if (r) { close(); refresh(); }
      } } }, "Zakazni bekor qilish"));
    } else if (o.status === "Tayyorlanmoqda" && !o.own) {
      actions.appendChild(el("p", { class: "muted small" }, "Bu buyurtmani zavod yaratgan — bekor qilish uchun admin bilan bog'laning."));
    }
    return el("div", {}, el("div", { class: "code-big" }, `${plabel(o)} × ${o.amount}`), kv, actions);
  });
}

async function viewDHome() {
  const [d] = await Promise.all([api("GET", "/api/d/summary"), loadUnread()]);
  const view = clear($("view"));
  unreadLink(view, "d_orders");
  view.appendChild(el("div", { class: "stats" },
    el("button", { class: "stat wide", type: "button", on: { click: () => go("d_account") } },
      el("b", { class: d.debt > 0 ? "pos" : "" }, money(d.debt)), el("span", {}, d.debt < 0 ? "Oldindan to'langan" : "Joriy qarzingiz")),
    el("button", { class: "stat", type: "button", on: { click: () => go("d_orders") } }, el("b", {}, d.active), el("span", {}, "Jarayonda")),
    el("button", { class: "stat", type: "button", on: { click: () => go("d_orders") } }, el("b", {}, d.ready), el("span", {}, "Tayyor, yetkazilmagan")),
    d.overdue ? el("div", { class: "stat late wide" }, el("b", {}, d.overdue), el("span", {}, "Muddati o'tgan — zavod bilan bog'laning")) : null));
  view.appendChild(el("div", { class: "section-title" }, "So'nggi buyurtmalar"));
  if (!d.recent.length) view.appendChild(empty("Hali buyurtma yo'q. «Katalog» dan zakaz bering."));
  d.recent.forEach((o) => view.appendChild(dOrderCard(o)));
  fab("＋ Zakaz berish", () => go("d_catalog"));
}

async function viewDCatalog() {
  const search = el("input", { class: "search", type: "search", placeholder: "Qidirish: model" });
  $("toolbar").appendChild(search);
  const data = await api("GET", "/api/d/catalog");
  const view = clear($("view"));
  const list = el("div", { class: "list" });
  view.appendChild(el("p", { class: "muted small", style: "margin:6px 4px 10px" },
    "✅ — omborda bor, tez yetkaziladi. Qolganlari oldindan zakaz (ishlab chiqariladi). ",
    data.price_channel ? el("a", { href: data.price_channel, on: { click: (e) => { e.preventDefault(); openLinkOut(data.price_channel); } } }, "Rasmlar va narxlar kanali") : null));
  view.appendChild(list);
  const draw = () => {
    const q = search.value.trim().toLowerCase();
    clear(list);
    const items = data.items.filter((p) => !q || `${p.name} ${p.model}`.toLowerCase().includes(q));
    if (!items.length) { list.appendChild(empty("Topilmadi.")); return; }
    items.forEach((p) => list.appendChild(el("button", { class: "row", type: "button", on: { click: () => dOrderForm(p) } },
      el("div", { class: "grow" }, el("div", { style: "font-weight:700;font-size:16px" }, p.name),
        el("div", { class: "sub" }, [p.model, p.price ? money(p.price) : null].filter(Boolean).join(" · ") || " ")),
      el("div", { class: "end" }, p.qty > 0 ? el("b", { class: "neg" }, `✅ ${p.qty} ta`) : el("span", { class: "muted small" }, "zakazga")))));
  };
  search.addEventListener("input", draw);
  draw();
}

/* ================= MIJOZ (rol berilmagan) ================= */
async function viewMCatalog() {
  const search = el("input", { class: "search", type: "search", placeholder: "Qidirish: model" });
  $("toolbar").appendChild(search);
  const data = await api("GET", "/api/m/catalog");
  const view = clear($("view"));
  view.appendChild(el("div", { class: "hint", style: "margin:6px 0 12px" },
    el("b", {}, "Siz mijoz sifatida kirdingiz"),
    el("p", { class: "muted small", style: "margin:6px 0 0" }, "Bu yerda hozir omborda bor mebellar ko'rinadi. Buyurtma berish yoki diller bo'lish uchun admin bilan bog'laning. ",
      data.price_channel ? el("a", { href: data.price_channel, on: { click: (e) => { e.preventDefault(); openLinkOut(data.price_channel); } } }, "Rasmlar va narxlar kanali") : null)));
  const list = el("div", { class: "list" });
  view.appendChild(list);
  const draw = () => {
    const q = search.value.trim().toLowerCase();
    clear(list);
    const items = data.items.filter((p) => !q || `${p.name} ${p.model}`.toLowerCase().includes(q));
    if (!items.length) { list.appendChild(empty(data.items.length ? "Topilmadi." : "Hozircha sotuvda mebel yo'q.")); return; }
    items.forEach((p) => list.appendChild(el("div", { class: "row" },
      el("div", { class: "grow" }, el("div", { style: "font-weight:700;font-size:16px" }, p.name),
        el("div", { class: "sub" }, p.model || " ")),
      el("div", { class: "end" }, el("b", { class: "neg" }, `✅ ${p.qty} ta`)))));
  };
  search.addEventListener("input", draw);
  draw();
}

function openLinkOut(url) {
  if (IN_TELEGRAM && tg.openTelegramLink && /^https:\/\/t\.me\//.test(url)) tg.openTelegramLink(url);
  else if (IN_APP) window.location.href = url.replace(/^https:\/\/t\.me\/\+/, "tg://join?invite=");
  else window.open(url, "_blank", "noopener");
}

function dOrderForm(p) {
  sheet((close) => {
    const amount = el("input", { type: "number", min: "1", max: "1000", value: "1", inputmode: "numeric" });
    const due = el("input", { type: "date", value: isoToday(p.qty > 0 ? 1 : 3), min: isoToday() });
    const comment = el("textarea", { maxlength: "500", placeholder: "Masalan: rangi oq (ixtiyoriy)" });
    const total = el("p", { class: "muted small" });
    const upd = () => {
      const n = Number(amount.value) || 0;
      const parts = [];
      if (p.price) parts.push(`Jami: ${money(p.price * n)}`);
      if (n > p.qty) parts.push(p.qty > 0 ? `${p.qty} tasi omborda, qolgani ishlab chiqariladi` : "Omborda yo'q — ishlab chiqariladi");
      total.textContent = parts.join(" · ");
    };
    amount.addEventListener("input", upd); upd();
    const btn = el("button", { class: "btn", type: "button" }, "Zakaz berish");
    btn.addEventListener("click", async () => {
      const n = Number(amount.value);
      if (!n || n < 1) { toast("Sonini kiriting.", true); return; }
      const r = await act(btn, () => api("POST", "/api/d/orders", { product: p.name, amount: n, due_date: due.value, comment: comment.value }),
        "Zakaz qabul qilindi. Zavodga xabar ketdi.");
      if (r) { close(); go("d_orders"); }
    });
    return el("div", {}, el("div", { class: "code-big" }, p.name),
      el("p", { class: "muted small" }, [p.model, p.price ? `1 dona: ${money(p.price)}` : null, p.qty > 0 ? `omborda ${p.qty} ta` : "oldindan zakaz"].filter(Boolean).join(" · ")),
      el("div", { class: "actions two", style: "margin-top:0" }, field("Soni", amount), field("Qachonga kerak", due)),
      total, field("Izoh", comment), el("div", { class: "actions" }, btn));
  });
}

async function viewDOrders() {
  S.dScope = S.dScope || "active";
  $("toolbar").appendChild(seg([["active", "Jarayonda"], ["done", "Yetkazilgan"], ["cancelled", "Bekor"]], S.dScope,
    (k) => { S.dScope = k; refresh(); }));
  const [data] = await Promise.all([api("GET", "/api/d/orders"), loadUnread()]);
  const view = clear($("view"));
  const pick = (o) => S.dScope === "active" ? ACTIVE.includes(o.status)
    : S.dScope === "cancelled" ? o.status === "Bekor qilindi" : !ACTIVE.includes(o.status) && o.status !== "Bekor qilindi";
  const all = data.items.filter(pick);
  const sec = unreadSection(all, dOrderCard);
  if (sec) view.appendChild(sec);
  const items = all.filter((o) => !S.unread[o.id]);
  if (S.dScope === "active") items.sort((a, b) => (parseDate(a.due_date) || 0) - (parseDate(b.due_date) || 0));
  if (!items.length && !sec) view.appendChild(empty(S.dScope === "active" ? "Jarayondagi buyurtma yo'q." : "Bu ro'yxat bo'sh."));
  items.slice(0, 200).forEach((o) => view.appendChild(dOrderCard(o)));
  fab("＋ Zakaz berish", () => go("d_catalog"));
}

async function viewDAccount() {
  const a = await api("GET", "/api/d/account");
  const view = clear($("view"));
  view.appendChild(el("div", { class: "stats" }, el("div", { class: "stat wide" },
    el("b", { class: a.debt > 0 ? "pos" : a.debt < 0 ? "neg" : "" }, money(a.debt)),
    el("span", {}, a.debt < 0 ? `${a.client} · oldindan to'langan` : `${a.client} · joriy qarz`))));
  view.appendChild(el("div", { class: "actions" }, el("button", { class: "btn", type: "button", on: { click: dPaymentForm } }, "💵 To'lov qildim")));
  if (a.pending_payments.length) {
    view.appendChild(el("div", { class: "section-title" }, "Tasdiq kutilmoqda"));
    view.appendChild(el("div", { class: "list" }, a.pending_payments.map((p) => el("div", { class: "row" },
      el("div", { class: "grow" }, money(p.amount), el("div", { class: "sub" }, `${fdate(p.timestamp)} · admin tasdiqlashi kutilmoqda`))))));
  }
  view.appendChild(el("div", { class: "section-title" }, `To'lanmagan (olingan) mebellar — ${a.unsettled.length} ta`));
  if (!a.unsettled.length) view.appendChild(empty("Hammasi to'langan."));
  else view.appendChild(el("div", { class: "list" }, a.unsettled.map((r) => el("div", { class: "row" },
    el("div", { class: "grow" }, el("b", {}, plabel(r)), ` × ${r.amount}`,
      el("div", { class: "sub" }, `${fdate(r.delivered_at)}${r.discount ? " · chegirma " + money(r.discount) : ""}${r.paid_partial ? " · to'langan " + money(r.paid_partial) : ""}`)),
    el("div", { class: "end" }, el("b", {}, money(Math.max(0, r.net - r.paid_partial))))))));
  if (a.pending_orders) view.appendChild(el("p", { class: "muted small", style: "margin:8px 4px" },
    `Yana ${a.pending_orders} ta buyurtma tayyorlanmoqda — yetkazilgandan keyin qarzga qo'shiladi.`));
  view.appendChild(el("div", { class: "section-title" }, "To'lovlar tarixi"));
  if (!a.payments.length) view.appendChild(empty("Hali to'lov yo'q."));
  else view.appendChild(el("div", { class: "list" }, a.payments.map((p) => el("div", { class: "row" },
    el("div", { class: "grow" }, p.note, el("div", { class: "sub" }, fdate(p.date))), el("div", { class: "end neg" }, "−" + money(p.amount))))));
}

function dPaymentForm() {
  sheet((close) => {
    const amount = el("input", { type: "number", min: "1", step: "1", inputmode: "decimal", placeholder: "Summa, $" });
    const btn = el("button", { class: "btn", type: "button" }, "Adminga yuborish");
    btn.addEventListener("click", async () => {
      const v = Number(amount.value);
      if (!v || v <= 0) { toast("Summani kiriting.", true); return; }
      const r = await act(btn, () => api("POST", "/api/d/payments", { amount: v }), "Yuborildi. Admin tasdiqlagach qarzdan ayiriladi.");
      if (r) { close(); refresh(); }
    });
    return el("div", {}, el("h2", {}, "To'lov qildim"),
      el("p", { class: "muted small" }, "Qancha to'laganingizni yozing. Admin tasdiqlagandan keyin qarzingizdan ayiriladi va sizga xabar keladi."),
      field("Summa ($)", amount), el("div", { class: "actions" }, btn));
  });
}

/* ================= ishga tushirish ================= */
/* ---------- push: Android ilova tokenni shu funksiyaga beradi ---------- */
let PUSH_TOKEN = "";
let pushRegistered = "";
async function registerPush() {
  if (!PUSH_TOKEN || IN_TELEGRAM || !S.me || pushRegistered === PUSH_TOKEN) return;
  try {
    await api("POST", "/api/push/register", { token: PUSH_TOKEN, device: navigator.userAgent.slice(0, 110) });
    pushRegistered = PUSH_TOKEN;
  } catch (_) { /* keyingi ochilishda qayta urinadi */ }
}
window.mmebelSetPushToken = function (t) {
  if (typeof t !== "string" || !/^[A-Za-z0-9:_-]{20,4096}$/.test(t)) return;
  PUSH_TOKEN = t;
  registerPush();
};

/* ---------- ilova rejimi: Telegram orqali kirish ---------- */
let loginTimer = null;
const IN_APP = /MMebelApp/.test(navigator.userAgent);
const IS_IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const IS_STANDALONE = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
function openExternal(s) {
  // Android ilova va iPhone'dagi o'rnatilgan web-ilova: tg:// to'g'ridan-to'g'ri Telegram ilovasini ochadi
  if (IN_APP || (IS_IOS && IS_STANDALONE)) { window.location.href = s.tg_link || s.bot_link; return; }
  window.open(s.bot_link, "_blank", "noopener");
}

/* ---------- Web Push: iPhone (bosh ekrandagi web-ilova) va brauzerlar ---------- */
const WEB_PUSH_OK = !IN_APP && !IN_TELEGRAM && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
let WEB_ENDPOINT = "";
function b64uToBytes(s) {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
}
function bytesToB64u(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
/* ask=true faqat tugma bosilganda: iOS ruxsat so'rovini faqat foydalanuvchi harakatida ko'rsatadi */
async function webPushSubscribe(ask) {
  if (!WEB_PUSH_OK || !S.me || Notification.permission === "denied") return false;
  if (Notification.permission !== "granted") {
    if (!ask || (await Notification.requestPermission()) !== "granted") return false;
  }
  const { key } = await api("GET", "/api/push/web/key");
  if (!key) return false;
  const reg = await navigator.serviceWorker.register("/panel/sw.js", { scope: "/panel/" });
  await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  const old = sub && sub.options && sub.options.applicationServerKey;
  if (sub && old && bytesToB64u(old) !== key) { await sub.unsubscribe(); sub = null; } // server kaliti almashgan
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64uToBytes(key) });
  await api("POST", "/api/push/web/subscribe", { subscription: sub.toJSON(), device: navigator.userAgent.slice(0, 110) });
  WEB_ENDPOINT = sub.endpoint;
  return true;
}
/* Kompyuter (Chrome/Edge) va Android brauzer: «O'rnatish» — ilova alohida oynada, ish stolida belgi bilan */
let installPrompt = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  installPrompt = e;
  showInstallButton();
});
window.addEventListener("appinstalled", () => { installPrompt = null; document.getElementById("install-btn")?.remove(); });
function showInstallButton() {
  if (!installPrompt || IN_APP || IN_TELEGRAM || IS_STANDALONE || document.getElementById("install-btn")) return;
  const who = $("who");
  if (!who) return;
  const btn = el("button", { id: "install-btn", class: "linkbtn", type: "button" }, "💻 O'rnatish");
  btn.addEventListener("click", async () => {
    const p = installPrompt;
    if (!p) return;
    installPrompt = null;
    p.prompt();
    await p.userChoice.catch(() => null);
    btn.remove();
  });
  who.appendChild(btn);
}

function iosInstallHint() {
  if (!IS_IOS || IS_STANDALONE || IN_TELEGRAM) return null;
  return el("div", { class: "hint" },
    el("b", {}, "📲 iPhone'ga ilova qilib o'rnating"),
    el("ol", {},
      el("li", {}, "Safari'ning pastidagi «Ulashish» ", el("b", {}, "⬆︎"), " tugmasini bosing"),
      el("li", {}, "«Bosh ekranga qo'shish» (Add to Home Screen) ni tanlang"),
      el("li", {}, "Ekrandagi «Munosib Mebel» belgisidan oching va shu yerda kiring")),
    el("p", { class: "muted small" }, "Xabarnomalar faqat o'rnatilgan ilovada ishlaydi (iOS 16.4+)."));
}
function showLogin(note) {
  clearTimeout(loginTimer);
  S.me = null;
  sheetStack.slice().forEach((c) => c());
  $("tabs").classList.add("hidden");
  document.querySelectorAll(".fab").forEach((f) => f.remove());
  clear($("toolbar"));
  $("title").textContent = "Munosib Mebel";
  $("who").textContent = "Sklad va buyurtmalar";
  const status = el("p", { class: "muted small", role: "status" }, note || "");
  const device = navigator.userAgent.slice(0, 110);

  /* ---- 1-usul: telefon raqam + botga keladigan kod ---- */
  const phone = el("input", { type: "tel", inputmode: "tel", autocomplete: "tel", value: "+998 ", maxlength: "20",
    placeholder: "+998 90 123 45 67", "aria-label": "Telefon raqam" });
  const getCode = el("button", { class: "btn", type: "button" }, "Kod olish");
  const codeBox = el("div", { class: "hidden" });
  let req = null;
  let resendTimer = null;
  const startCooldown = (sec) => {
    clearInterval(resendTimer);
    let left = sec;
    getCode.disabled = true;
    getCode.textContent = `Qayta yuborish (${left})`;
    resendTimer = setInterval(() => {
      left -= 1;
      if (left <= 0) { clearInterval(resendTimer); getCode.disabled = false; getCode.textContent = "Kodni qayta yuborish"; }
      else getCode.textContent = `Qayta yuborish (${left})`;
    }, 1000);
  };
  getCode.addEventListener("click", async () => {
    const digits = phone.value.replace(/\D/g, "");
    if (digits.length < 9) { status.textContent = "Telefon raqamingizni to'liq kiriting."; phone.focus(); return; }
    getCode.disabled = true;
    status.textContent = "Kod yuborilmoqda…";
    try { req = await api("POST", "/api/auth/phone/start", { phone: phone.value, device }); }
    catch (e) { status.textContent = e.message; getCode.disabled = false; return; }
    startCooldown(60);
    const botHref = (IN_APP || (IS_IOS && IS_STANDALONE)) ? (req.tg_link || req.bot_link) : req.bot_link;
    clear(status).append(
      "Kod Telegram'dagi botimizga yuborildi. Botni ochib kodni shu yerga kiriting.",
      el("div", { class: "actions" }, el("a", { class: "btn ghost", href: botHref,
        style: "display:block;text-align:center;text-decoration:none" }, "Botni ochish")),
      el("p", { class: "muted small" }, "Kod kelmadimi? Botga «START» bosing va «📱 Raqamni ulashish» tugmasi orqali raqamingizni yuboring, so'ng kodni qayta oling."));
    codeBox.classList.remove("hidden");
    code.value = "";
    code.focus();
  });
  const code = el("input", { type: "text", inputmode: "numeric", autocomplete: "one-time-code", maxlength: "6",
    placeholder: "6 xonali kod", "aria-label": "Kod", class: "otp" });
  const enter = el("button", { class: "btn", type: "button" }, "Kirish");
  const verify = async () => {
    if (!req) return;
    const v = code.value.replace(/\D/g, "");
    if (v.length !== 6) { status.textContent = "Kod 6 ta raqamdan iborat."; return; }
    enter.disabled = true;
    try {
      const r = await api("POST", "/api/auth/phone/verify", { request_id: req.request_id, code: v });
      setToken(r.token); haptic("success"); clearInterval(resendTimer); boot();
    } catch (e) { status.textContent = e.message; enter.disabled = false; code.select(); }
  };
  enter.addEventListener("click", verify);
  code.addEventListener("input", () => { code.value = code.value.replace(/\D/g, "").slice(0, 6); if (code.value.length === 6) verify(); });
  phone.addEventListener("keydown", (e) => { if (e.key === "Enter") getCode.click(); });
  codeBox.append(field("Telegram'ga kelgan kod", code), el("div", { class: "actions" }, enter));

  /* ---- 2-usul: Telegram tugmasi (avvalgidek) ---- */
  const tgBtn = el("button", { class: "linkbtn", type: "button", style: "padding:0;font-size:14px" }, "Telegram orqali kirish");
  tgBtn.addEventListener("click", async () => {
    tgBtn.disabled = true;
    status.textContent = "Bot ochilmoqda…";
    let s;
    try { s = await api("POST", "/api/auth/start", { device }); }
    catch (e) { status.textContent = e.message; tgBtn.disabled = false; return; }
    openExternal(s);
    clear(status).append(
      "Telegram'da botni oching, «START» va «✅ Ha, men kiryapman» ni bosing, so'ng shu yerga qayting. Kutilmoqda…",
      el("div", { class: "actions" },
        el("a", { class: "btn ghost", href: IN_APP ? (s.tg_link || s.bot_link) : s.bot_link,
          style: "display:block;text-align:center;text-decoration:none" }, "Telegram ochilmadimi? Shu yerni bosing")));
    const deadline = Date.now() + s.expires_in * 1000;
    const tick = async () => {
      if (Date.now() > deadline) { clear(status).append("Vaqt tugadi. Qaytadan bosing."); tgBtn.disabled = false; return; }
      try {
        const r = await api("POST", "/api/auth/poll", { code: s.code, poll_secret: s.poll_secret });
        if (r.status === "approved") { setToken(r.token); haptic("success"); boot(); return; }
        if (r.status === "rejected") { status.textContent = "Kirish rad etildi."; tgBtn.disabled = false; return; }
        if (r.status === "expired") { status.textContent = "Vaqt tugadi. Qaytadan bosing."; tgBtn.disabled = false; return; }
      } catch (_) { /* tarmoq uzilishi — keyingi urinish */ }
      loginTimer = setTimeout(tick, 2000);
    };
    loginTimer = setTimeout(tick, 2000);
  });

  clear($("view")).appendChild(el("div", { class: "gate" },
    el("img", { class: "gate-logo", src: "/panel/static/logo-full.png", alt: "Munosib Mebel" }),
    el("h1", {}, "Hisobingizga kiring"),
    el("p", { class: "muted" }, "Telefon raqamingizni kiriting — kirish kodi Telegram'dagi botimizga keladi."),
    el("div", { class: "login-form" }, field("Telefon raqam", phone), el("div", { class: "actions" }, getCode), codeBox),
    status,
    el("p", { class: "muted small" }, "yoki ", tgBtn),
    iosInstallHint() || ""));
  showInstallButton();
}

async function logout() {
  if (!(await confirmDlg("Ilovadan chiqilsinmi?"))) return;
  const out = {};
  if (PUSH_TOKEN) out.push_token = PUSH_TOKEN;
  if (WEB_ENDPOINT) out.web_endpoint = WEB_ENDPOINT;
  try { await api("POST", "/api/logout", out); } catch (_) { /* baribir chiqamiz */ }
  WEB_ENDPOINT = "";
  pushRegistered = "";
  setToken("");
  showLogin("Chiqdingiz.");
}

function showError(msg) {
  const retry = el("button", { class: "btn ghost", type: "button", on: { click: boot } }, "Qayta urinish");
  clear($("view")).appendChild(el("div", { class: "gate" }, el("h1", {}, "Ulanib bo'lmadi"),
    el("p", { class: "muted" }, msg), el("div", { class: "actions" }, retry)));
  $("who").textContent = "";
}

async function boot() {
  if (IN_TELEGRAM) {
    tg.ready(); tg.expand();
    document.documentElement.classList.add(tg.colorScheme === "dark" ? "tg-dark" : "tg-light");
    try { if (tg.isVersionAtLeast("6.1")) { tg.setHeaderColor("#182028"); tg.setBackgroundColor(tg.colorScheme === "dark" ? "#11161b" : "#eef3ea"); } } catch (_) { /* eski versiya */ }
  }
  else document.documentElement.classList.add("standalone");
  if (!IN_TELEGRAM && !getToken()) { showLogin(); return; }
  clear($("view")).appendChild(loading());
  try {
    S.me = await api("GET", "/api/me");
  } catch (e) {
    if (e.status === 401 && !IN_TELEGRAM) return; // showLogin allaqachon chaqirilgan
    if (e.status === 403 && !IN_TELEGRAM) { setToken(""); showLogin(e.message); return; }
    showError(e.message);
    return;
  }
  const who = $("who");
  clear(who).appendChild(document.createTextNode(`${S.me.name || "Foydalanuvchi"} · ${S.me.role_label}`));
  if (!IN_TELEGRAM) who.appendChild(el("button", { class: "linkbtn", type: "button", on: { click: logout } }, "Chiqish"));
  const testBtn = () => el("button", { class: "linkbtn", type: "button", on: { click: async (e) => {
    const sound = PUSH_TEST_SOUNDS[pushTestIdx++ % PUSH_TEST_SOUNDS.length];
    const r = await act(e.target, () => api("POST", "/api/push/test", { sound }));
    if (!r) return;
    if (!r.enabled) toast("Push hali serverda yoqilmagan.", true);
    else if (!r.sent) toast("Bu telefon bildirishnomaga ro'yxatdan o'tmagan. Bildirishnoma ruxsatini bering va qayta oching.", true);
    else toast("Sinov xabari yuborildi");
  } } }, "🔔 Sinov");
  const canPush = S.me.role !== "mijoz";  // mijozga xabarnoma yuborilmaydi
  if (IN_APP && canPush) who.appendChild(testBtn());
  if (canPush) registerPush();
  if (!canPush) { /* web push ham kerak emas */ }
  else if (WEB_PUSH_OK && Notification.permission === "granted") {
    webPushSubscribe(false).then((ok) => { if (ok) who.appendChild(testBtn()); }).catch(() => { /* keyingi ochilishda */ });
  } else if (WEB_PUSH_OK && Notification.permission === "default") {
    const enable = el("button", { class: "linkbtn", type: "button" }, "🔔 Xabarnomalarni yoqish");
    enable.addEventListener("click", async () => {
      enable.disabled = true;
      let ok = false;
      try { ok = await webPushSubscribe(true); } catch (e) { toast(e.message || "Yoqib bo'lmadi", true); }
      enable.disabled = false;
      if (ok) { enable.replaceWith(testBtn()); toast("Xabarnomalar yoqildi ✅"); }
      else if (Notification.permission === "denied") { enable.remove(); toast("Ruxsat berilmadi. Sozlamalar → Bildirishnomalar orqali yoqing.", true); }
    });
    who.appendChild(enable);
  }
  showInstallButton();
  const hint = iosInstallHint();
  if (hint) who.appendChild(el("button", { class: "linkbtn", type: "button",
    on: { click: () => sheet(() => el("div", {}, iosInstallHint())) } }, "📲 O'rnatish"));
  if (new URLSearchParams(location.search).get("next") === "dashboard" && S.me.role === "admin" && !IN_TELEGRAM) {
    location.replace("/panel/dashboard");
    return;
  }
  go(TABS[S.me.role][0][0]);
  loadUnread();
}
// Ilovaga qaytilganda (push kelgandan keyin) yangi xabarlar ro'yxatini yangilash
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !S.me) return;
  const before = Object.keys(S.unread).length;
  loadUnread().then(() => {
    const onOrders = ["orders", "d_orders", "d_home"].includes(S.tab);
    if (onOrders && Object.keys(S.unread).length !== before && !sheetStack.length) refresh();
  });
});
const PUSH_TEST_SOUNDS = ["new", "ready", "cancel"]; // har bosishda navbatdagi ovoz
let pushTestIdx = 0;
boot();
