// Service worker: makes replyloop installable and lets the app shell open instantly.
// Data (/api) always comes from the network, so you never see stale replies or stats.
const VERSION = "rl-v9";
const SHELL = ["/", "/static/app.css?v=9", "/static/app.js?v=9", "/static/theme.js?v=9", "/static/i18n.js?v=9",
  "/static/icons/icon-192.png", "/static/icons/icon-512.png", "/manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/") || url.pathname === "/webhook" || url.pathname === "/health" || url.pathname.startsWith("/auth/")) return;
  if (e.request.mode === "navigate") {
    // network first, so a new version shows up right away; cached shell when offline
    e.respondWith(fetch(e.request).catch(() => caches.match("/")));
    return;
  }
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
    if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(e.request, copy)); }
    return res;
  })));
});
