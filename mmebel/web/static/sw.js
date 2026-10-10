/* Munosib Mebel — service worker: faqat push xabarlar (kesh yo'q — panel doim serverdan yangi). */
"use strict";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

// iOS talabi: har bir push albatta bildirishnoma ko'rsatishi kerak, aks holda obuna bekor qilinadi.
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data ? e.data.text() : "" }; }
  const title = typeof d.title === "string" && d.title ? d.title : "Munosib Mebel";
  e.waitUntil(self.registration.showNotification(title, {
    body: typeof d.body === "string" ? d.body : "",
    icon: "/panel/static/icon-192.png",
    badge: "/panel/static/icon-192.png",
    data: { url: "/panel/" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  e.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const c of all) {
      if (new URL(c.url).pathname.startsWith("/panel")) { await c.focus(); return; }
    }
    await self.clients.openWindow("/panel/");
  })());
});
