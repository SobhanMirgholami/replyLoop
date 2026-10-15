/* replyloop dashboard — plain JavaScript, no build step.
   Screens: login · posts · post automations · automations · inbox · insights · settings.
   Languages: Persian (default, right-to-left) and English. Persian texts live in i18n.js. */
"use strict";

// ------------------------------------------------------------------ helpers
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const S = { me: null, accounts: [], aid: null, posts: null, overview: null, settings: null, ai: false, webhookReady: false, installEvt: null };
const store = { get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };

// ------------------------------------------------------------------ language
const LANG = store.get("rl_lang", "fa") === "en" ? "en" : "fa";
const FA_MODE = LANG === "fa";
/** Translate: t("English text", {vars}). Persian comes from i18n.js; English is the key itself. */
function t(s, vars) {
  let out = (FA_MODE && window.FA && window.FA[s]) || s;
  if (vars) for (const k in vars) out = out.split(`{${k}}`).join(vars[k]);
  return out;
}
// Shamsi calendar with English digits in Persian mode
const DATE_LOCALE = FA_MODE ? "fa-IR-u-nu-latn-ca-persian" : undefined;
const NUM_LOCALE = FA_MODE ? "fa-IR-u-nu-latn" : undefined;
const splitList = (s) => s.split(/[,،]/).map((x) => x.trim()).filter(Boolean);   // Persian comma works too
const handle = (u) => `<bdi dir="ltr">@${esc(u)}</bdi>`;                         // keeps @user readable inside Persian text
function setLanguage(lang) { store.set("rl_lang", lang); location.reload(); }

const I = {
  posts: '<rect x="3" y="3" width="7" height="7" rx="1.6"/><rect x="14" y="3" width="7" height="7" rx="1.6"/><rect x="3" y="14" width="7" height="7" rx="1.6"/><rect x="14" y="14" width="7" height="7" rx="1.6"/>',
  auto: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  inbox: '<path d="M3 13l2.5-7.5A2 2 0 0 1 7.4 4h9.2a2 2 0 0 1 1.9 1.5L21 13v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 13h5l1.5 2.5h5L16 13h5"/>',
  settings: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  system: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', back: '<path d="M15 6l-6 6 6 6"/>', chev: '<path d="M9 6l6 6-6 6"/>',
  down: '<path d="M6 9l6 6 6-6"/>', up: '<path d="M6 15l6-6 6 6"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>', x: '<path d="M6 6l12 12M18 6L6 18"/>',
  reel: '<rect x="3" y="3" width="18" height="18" rx="5"/><path d="M10 9l5 3-5 3z"/>',
  photo: '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="9" cy="9" r="1.8"/><path d="M21 16l-5-5-9 9"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  out: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10"/>',
  msg: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  send: '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
  follow: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 11l2 2 4-4"/>',
  tap: '<path d="M9 11V5a2 2 0 0 1 4 0v6"/><path d="M13 9a2 2 0 0 1 4 0v3a6 6 0 0 1-6 6h-.5A6.5 6.5 0 0 1 5 13.5V12a2 2 0 0 1 4 0"/>',
  skip: '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>', warn: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
  spark: '<path d="M12 3l1.8 4.7 4.7 1.8-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/>', globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4"/>', trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>', phone: '<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', story: '<rect x="6" y="2" width="12" height="20" rx="3"/><circle cx="12" cy="10" r="3"/>',
  shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
  laptop: '<rect x="4" y="5" width="16" height="11" rx="1.8"/><path d="M2 19h20"/>',
  copy: '<rect x="8" y="8" width="13" height="13" rx="2.5"/><path d="M16 8V5.5A2.5 2.5 0 0 0 13.5 3h-8A2.5 2.5 0 0 0 3 5.5v8A2.5 2.5 0 0 0 5.5 16H8"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3M14 9l2 2"/>',
  lang: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
};
// icons that point in a reading direction get mirrored in Persian (class "flip")
const DIRECTIONAL = new Set(["back", "chev", "send", "out", "ext"]);
const ic = (name, size = 20, sw = 1.9) => `<svg ${DIRECTIONAL.has(name) ? 'class="flip" ' : ""}width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${I[name]}</svg>`;
const BOLT = `<span class="logo">${ic("msg", 18, 2.2)}</span>`;

const HEADERS = { "Content-Type": "application/json", "X-Requested-With": "replyloop", "X-Lang": LANG };
async function api(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch("/api" + path, {
      method, credentials: "same-origin",
      headers: method === "GET" ? { "X-Lang": LANG } : HEADERS,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    toast(t("You're offline. Check your connection."), true);
    throw new Error("offline");
  }
  let data = null;
  try { data = await res.json(); } catch {}
  if (res.status === 401 && path !== "/login" && path !== "/password") { await boot(); throw new Error("signed out"); }
  if (!res.ok) { const msg = (data && data.detail) || t("Something went wrong ({n}).", { n: res.status }); toast(msg, true); throw new Error(msg); }
  return data;
}
const A = (p) => `/a/${S.aid}${p}`;
const isOwner = () => S.role === "owner";
const canEdit = () => S.role === "owner" || S.role === "editor";
const ROLE_LABEL = { owner: "Owner", editor: "Editor", viewer: "View only" };

let toastTimer;
function toast(msg, err = false) {
  const box = $("#toast");
  box.innerHTML = `<div class="t ${err ? "err" : ""}">${esc(msg)}</div>`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    const el = $(".t", box); if (!el) return;
    el.classList.add("out"); setTimeout(() => { if (el.isConnected) box.innerHTML = ""; }, 220);
  }, 3200);
}

function ago(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60) return t("just now");
  if (s < 3600) return t("{n}m ago", { n: Math.floor(s / 60) });
  if (s < 86400) return t("{n}h ago", { n: Math.floor(s / 3600) });
  return t("{n}d ago", { n: Math.floor(s / 86400) });
}
const clock = (iso) => (iso ? new Date(iso).toLocaleTimeString(NUM_LOCALE, { hour: "2-digit", minute: "2-digit" }) : "");
const hasRTL = (s) => /[؀-ۿ]/.test(s || "");
const dirAttr = (s) => (hasRTL(s) ? ' dir="rtl"' : ' dir="auto"');
const tintOf = (id) => `tint-${[...String(id)].reduce((a, c) => a + c.charCodeAt(0), 0) % 4}`;
const currentAccount = () => S.accounts.find((a) => a.id === S.aid);
const isTest = () => !(currentAccount() || {}).live;
const typeLabel = (type) => t(type === "REEL" ? "Reel" : type === "CAROUSEL" ? "Carousel" : "Post");

// ------------------------------------------------------------------ theme
function applyTheme(pref) {
  store.set("rl_theme", pref);
  const dark = pref === "dark" || (pref === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  const btn = $("#theme-btn");
  if (btn) btn.innerHTML = ic(dark ? "sun" : "moon", 19);
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (store.get("rl_theme", "system") === "system") applyTheme("system"); });


// ------------------------------------------------------------------ motion
// Page changes use the View Transitions API (Chrome/Edge/Safari 18+). Older browsers get a simple fade.
// Everything is skipped when the phone asks for reduced motion.
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)");
const ROOT = document.documentElement;
const canVT = () => typeof document.startViewTransition === "function" && !REDUCED.matches && !document.hidden;
let pendingNav = null;     // set by route(); the next paint() animates the page change
let lastPos = null;
const morph = { post: null, inbox: null };   // which post / comment the user opened, to fly it back

function routePos(name, arg) {
  const base = { "": 0, post: 0, automations: 1, inbox: 2, insights: 3, settings: 4 }[name || ""] ?? 0;
  let sub = 0;
  if (name === "post" && arg) sub = 1;
  if (name === "inbox" && arg && innerWidth <= 960) sub = 1;
  if (name === "insights") sub = Math.max(0, INS_TABS.findIndex(([k]) => k === (arg || "account")));
  return base * 10 + sub;
}
function setNav(navKey) {
  $$("[data-nav]").forEach((a) => a.setAttribute("aria-current", a.dataset.nav === navKey ? "page" : "false"));
}
function startVT(kind, update) {
  ROOT.dataset.vt = kind;
  const vt = document.startViewTransition(update);
  vt.finished.catch(() => {}).finally(() => { if (ROOT.dataset.vt === kind) delete ROOT.dataset.vt; });
  vt.ready.catch(() => {});
  return vt;
}
// Swaps the page content. The first paint after a navigation slides/morphs from the old page.
function paint(view, html) {
  const nav = pendingNav; pendingNav = null;
  const apply = () => { view.innerHTML = html; if (nav) { setNav(nav.navKey); window.scrollTo(0, 0); } };
  if (!nav) { apply(); return Promise.resolve(); }
  if (!canVT()) {
    apply();
    if (!REDUCED.matches) view.animate([{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "none" }], { duration: 240, easing: "cubic-bezier(.2,.8,.2,1)" });
    return Promise.resolve();
  }
  const x = nav.dir * (FA_MODE ? -1 : 1);
  ROOT.style.setProperty("--nav-x", x);
  ROOT.style.setProperty("--nav-y", nav.dir ? 0 : 1);
  return startVT("nav", apply).updateCallbackDone.catch(() => {});
}
// Animates a list re-order / filter: cards with --vtn glide to their new places.
function morphList(container, update) {
  if (!container || !canVT()) { update(); return; }
  container.classList.add("vt-list");
  startVT("list", update).finished.catch(() => {}).finally(() => container.classList.remove("vt-list"));
}
// Theme change: the new theme grows in a circle from the button you pressed.
function themeTransition(pref, from) {
  const before = ROOT.dataset.theme;
  const dark = pref === "dark" || (pref === "system" && matchMedia("(prefers-color-scheme: dark)").matches);
  if (!from || !canVT() || before === (dark ? "dark" : "light")) { applyTheme(pref); spinThemeIcon(); return; }
  const r = from.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const R = Math.hypot(Math.max(cx, innerWidth - cx), Math.max(cy, innerHeight - cy));
  const vt = startVT("theme", () => { applyTheme(pref); });
  vt.ready.then(() => ROOT.animate({ clipPath: [`circle(0px at ${cx}px ${cy}px)`, `circle(${R}px at ${cx}px ${cy}px)`] },
    { duration: 620, easing: "cubic-bezier(.65,0,.35,1)", pseudoElement: "::view-transition-new(root)" })).catch(() => {});
  vt.finished.catch(() => {}).finally(spinThemeIcon);
}
function spinThemeIcon() { const svg = $("#theme-btn svg"); if (svg && !REDUCED.matches) svg.animate([{ transform: "rotate(-90deg) scale(.4)", opacity: 0 }, { transform: "none", opacity: 1 }], { duration: 420, easing: "cubic-bezier(.34,1.56,.64,1)" }); }

// Thin loading bar under the top bar, only when a page takes a moment.
let progressTimer;
function progress(on) {
  const bar = $("#progress");
  clearTimeout(progressTimer);
  if (!bar) return;
  if (on) progressTimer = setTimeout(() => bar.classList.add("on"), 140);
  else { bar.classList.remove("on"); }
}

// Segmented controls get a sliding "thumb" that follows the selected option.
function syncSeg(seg, animate = true) {
  let ind = seg.querySelector(":scope > .seg-ind");
  if (!ind) { ind = document.createElement("span"); ind.className = "seg-ind"; ind.setAttribute("aria-hidden", "true"); seg.prepend(ind); animate = false; }
  const on = seg.querySelector(':scope > button[aria-pressed="true"]');
  if (!on || !on.offsetWidth) { ind.style.opacity = "0"; return; }
  ind.classList.toggle("still", !animate);
  ind.style.opacity = "1";
  ind.style.width = `${on.offsetWidth}px`;
  ind.style.height = `${on.offsetHeight}px`;
  ind.style.transform = `translate(${on.offsetLeft}px, ${on.offsetTop}px)`;
  seg.classList.add("has-ind");
}
new MutationObserver((muts) => {
  const segs = new Set();
  for (const m of muts) {
    if (m.type === "attributes") { const seg = m.target.closest?.(".seg"); if (seg) segs.add(seg); }
    else m.addedNodes.forEach((n) => { if (n.nodeType === 1) { if (n.matches(".seg")) segs.add(n); n.querySelectorAll?.(".seg").forEach((x) => segs.add(x)); } });
  }
  segs.forEach((seg) => requestAnimationFrame(() => syncSeg(seg, true)));
}).observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ["aria-pressed"] });
addEventListener("resize", () => $$(".seg").forEach((seg) => syncSeg(seg, false)));

// Shared-element morphs: the tapped post thumbnail / inbox avatar flies to its spot on the next page.
document.addEventListener("click", (e) => {
  const link = e.target.closest?.('a[href^="#/post/"], a.item[href^="#/inbox/"]');
  if (!link || !canVT()) return;
  $$("[data-vt]").forEach((el) => (el.style.viewTransitionName = ""));
  const target = $("[data-vt]", link);
  if (target) target.style.viewTransitionName = target.dataset.vt;
  const id = decodeURIComponent(link.getAttribute("href").split("/")[2] || "");
  if (link.matches('[href^="#/post/"]')) morph.post = id; else morph.inbox = id;
}, true);

// ------------------------------------------------------------------ sheets & menus
function openSheet(title, bodyHtml, footHtml = "", { onClose } = {}) {
  closeLayer();
  const layer = $("#layer");
  layer.innerHTML = `<div class="scrim" data-close-scrim><div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(title)}">
    <div class="sheet-head"><h2>${esc(title)}</h2><button class="icon-btn flat" data-act="close" aria-label="${esc(t("Close"))}">${ic("x")}</button></div>
    <div class="sheet-body">${bodyHtml}</div>${footHtml ? `<div class="sheet-foot">${footHtml}</div>` : ""}</div></div>`;
  layer._onClose = onClose;
  document.body.style.overflow = "hidden";
  setTimeout(() => { const f = $(".sheet input:not([type=checkbox]), .sheet textarea", layer); if (f && innerWidth > 760) f.focus(); }, 30);
  return $(".sheet", layer);
}
function openMenu(anchor, html) {
  closeLayer();
  const layer = $("#layer");
  layer.innerHTML = `<div class="scrim" data-close-scrim style="background:transparent"></div><div class="menu" role="menu">${html}</div>`;
  const menu = $(".menu", layer), r = anchor.getBoundingClientRect();
  menu.style.top = `${Math.min(r.bottom + 8, innerHeight - menu.offsetHeight - 12)}px`;
  if (FA_MODE) menu.style.left = `${Math.max(12, r.left)}px`;          // anchor to the button's start edge
  else menu.style.right = `${Math.max(12, innerWidth - r.right)}px`;
  return menu;
}
function closeLayer() {
  const layer = $("#layer");
  const onClose = layer.innerHTML ? layer._onClose : null;
  layer._onClose = null;        // cleared first: onClose may itself close layers (e.g. re-render the page)
  if (layer.firstElementChild && !REDUCED.matches) {     // let the sheet/menu slide away instead of vanishing
    const ghost = document.createElement("div");
    ghost.className = "layer-ghost"; ghost.setAttribute("aria-hidden", "true"); ghost.inert = true;
    ghost.append(...layer.childNodes);
    ghost.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id"));
    document.body.append(ghost);
    setTimeout(() => ghost.remove(), 240);
  }
  layer.innerHTML = "";
  document.body.style.overflow = "";
  if (onClose) onClose();
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLayer(); });
document.addEventListener("click", (e) => { if (e.target.matches("[data-close-scrim]")) closeLayer(); });

function confirmSheet(title, text, okLabel, danger = false) {
  return new Promise((resolve) => {
    openSheet(title, `<p>${esc(text)}</p>`,
      `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn ${danger ? "btn-accent" : "btn-dark"} grow" id="confirm-ok">${esc(okLabel)}</button>`,
      { onClose: () => resolve(false) });
    $("#confirm-ok").onclick = () => { $("#layer")._onClose = null; closeLayer(); resolve(true); };
  });
}

const langSwitch = () => `<div class="seg" role="group" aria-label="${t("Language")}">
  <button data-act="set-lang" data-lang="fa" aria-pressed="${FA_MODE}" lang="fa">فارسی</button>
  <button data-act="set-lang" data-lang="en" aria-pressed="${!FA_MODE}" lang="en">English</button></div>`;

// ------------------------------------------------------------------ boot & auth
async function boot() {
  let me;
  try { me = await (await fetch("/api/me", { credentials: "same-origin", headers: { "X-Lang": LANG } })).json(); }
  catch {
    $("#root").innerHTML = `<div class="auth"><div class="auth-main"><div class="auth-form"><h1>${t("Can't reach the server")}</h1>
      <p class="muted">${t("Check your connection and reload.")}</p><button class="btn btn-dark" data-act="reload">${t("Reload")}</button></div></div></div>`;
    return;
  }
  if (!me.user) return renderAuth(me.setup_needed, me.google, me.pending_2fa);
  S.me = me.user; S.role = me.user.role || (me.user.is_owner ? "owner" : "editor"); document.body.dataset.role = S.role; S.accounts = me.accounts; S.ai = me.ai_available; S.webhookReady = me.webhook_ready; S.keyWarning = me.key_warning; S.dbWarning = me.db_warning; S.google = !!me.google;
  const saved = Number(store.get("rl_account", 0));
  S.aid = S.accounts.some((a) => a.id === saved) ? saved : (S.accounts[0] || {}).id ?? null;
  renderShell();
  route();
}

const GOOGLE_G = `<svg width="20" height="20" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>`;
const GOOGLE_ERRORS = {
  not_allowed: "This Google account doesn't have access. Sign in with the Gmail address the owner added, or use your password.",
  cancelled: "Google sign-in was cancelled.",
  expired: "Google sign-in took too long. Try again.",
  unverified: "This Google account's email isn't verified.",
  google_off: "Google sign-in isn't set up on this server yet.",
  failed: "Couldn't sign in with Google. Try again or use your password.",
};

function renderAuth(setupNeeded, google, pending2fa = false) {
  // Google sends people back here with ?login_error=... when something went wrong
  const params = new URLSearchParams(location.search);
  const gErr = params.get("login_error");
  if (gErr) history.replaceState(null, "", location.pathname + location.hash);
  $("#root").innerHTML = `<div class="auth">
    <section class="auth-art" aria-hidden="true">
      <div class="row spread"><div class="brand" style="color:inherit">${BOLT} replyloop</div></div>
      <div class="chat stack" style="gap:12px">
        <div class="say them">${t("menu please! 🙏")}</div>
        <div class="say us" dir="rtl">برای دریافت لینک، صفحه‌ی ما رو دنبال کن<div class="ig-btn" style="background:rgba(255,255,255,.22);margin-top:10px">دنبال میکنم</div></div>
        <div class="say them" style="display:flex;align-items:center;gap:8px;font-weight:700">${ic("check", 15, 2.4)} ${t("Follower confirmed · link sent")}</div>
      </div>
      <p class="big" style="font-size:30px;line-height:1.3;font-weight:800;max-width:440px">${t("Your comments answer themselves while you sleep.")}</p>
    </section>
    <main class="auth-main">
      ${setupNeeded ? `<div class="auth-form">
          <h1>${t("Almost ready")}</h1>
          <p class="muted">${t("There's no login yet. On your server, set <b>ADMIN_EMAIL</b> and <b>ADMIN_PASSWORD</b> (at least 10 characters), restart it, then reload this page.")}</p>
          <button class="btn btn-dark" data-act="reload">${t("Reload")}</button>${langSwitch()}</div>`
        : `<form class="auth-form" id="login-form" novalidate>
          <div class="row spread" style="align-items:flex-start"><div><h1>${t("Welcome back")}</h1><p class="muted" style="margin-top:6px">${t("Sign in to manage your Instagram replies.")}</p></div></div>
          <div id="login-error" role="alert">${gErr ? `<div class="error-box">${t(GOOGLE_ERRORS[gErr] || GOOGLE_ERRORS.failed)}</div>` : ""}</div>
          ${google ? `<a class="btn btn-google" href="/auth/google">${GOOGLE_G}<span>${t("Continue with Google")}</span></a>
          <div class="or"><span>${t("or with your password")}</span></div>` : ""}
          <label class="field"><span>${t("Email")}</span><input class="input" type="email" name="email" autocomplete="username" dir="ltr" required></label>
          <label class="field"><span>${t("Password")}</span>
            <span class="input-wrap"><input class="input" type="password" name="password" autocomplete="current-password" dir="ltr" required>
            <button type="button" class="icon-btn flat" data-act="toggle-pw" aria-label="${t("Show password")}">${ic("eye")}</button></span></label>
          <label class="switch"><input type="checkbox" name="remember" checked><span class="track"></span><span>${t("Keep me signed in on this device")}</span></label>
          <button class="btn btn-dark" type="submit">${t("Sign in")}</button>
          <p class="small muted row" style="gap:8px;flex-wrap:nowrap">${ic("lock", 16)} ${t("Private dashboard. There's no sign-up: only people you add can sign in.")}</p>
          ${langSwitch()}
        </form>`}
    </main></div>`;
  if (pending2fa) return renderCodeStep();
  const form = $("#login-form");
  if (!form) return;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const btn = $("button[type=submit]", form), box = $("#login-error");
    box.innerHTML = "";
    if (!form.email.value || !form.password.value) { box.innerHTML = `<div class="error-box">${t("Enter your email and password.")}</div>`; return; }
    btn.disabled = true; btn.textContent = t("Signing in…");
    try {
      const res = await fetch("/api/login", { method: "POST", credentials: "same-origin", headers: HEADERS,
        body: JSON.stringify({ email: form.email.value, password: form.password.value, remember: form.remember.checked }) });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(d.detail || t("Couldn't sign in."));
      if (d.two_factor) return renderCodeStep();
      await boot();
    } catch (err) {
      box.innerHTML = `<div class="error-box">${esc(err.message === "Failed to fetch" ? t("You're offline.") : err.message)}</div>`;
      btn.disabled = false; btn.textContent = t("Sign in");
    }
  };
}


// Second step of signing in, when two-step login is on (after the password or Google).
function renderCodeStep(backup = false) {
  const main = $(".auth-main");
  if (!main) return;
  main.innerHTML = `<form class="auth-form" id="code-form" novalidate>
      <span class="shield-badge">${ic("shield", 26)}</span>
      <div><h1>${t("Two-step login")}</h1><p class="muted" style="margin-top:6px">${t(backup ? "Enter one of the backup codes you saved when you turned this on." : "Open your authenticator app and enter the 6-digit code for replyloop.")}</p></div>
      <div id="login-error" role="alert"></div>
      <label class="field"><span>${t(backup ? "Backup code" : "6-digit code")}</span>
        <input class="input code-input" name="code" dir="ltr" autocomplete="one-time-code" ${backup ? 'maxlength="12" autocapitalize="off" spellcheck="false" placeholder="xxxx-xxxx"' : 'inputmode="numeric" maxlength="6" placeholder="••••••"'} required></label>
      <button class="btn btn-dark" type="submit">${t("Verify")}</button>
      <button class="btn btn-ghost" type="button" data-act="code-mode" data-backup="${backup ? "" : "1"}">${t(backup ? "Use the authenticator app instead" : "Lost your phone? Use a backup code")}</button>
      <button class="link-btn" type="button" data-act="cancel-code">${ic("back", 16)} ${t("Back to sign in")}</button>
    </form>`;
  const form = $("#code-form"), input = form.code;
  setTimeout(() => input.focus(), 50);
  const digits = (v) => v.replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/\D/g, "");
  if (!backup) input.addEventListener("input", () => { if (digits(input.value).length === 6) form.requestSubmit(); });
  form.onsubmit = async (e) => {
    e.preventDefault();
    const btn = $("button[type=submit]", form), box = $("#login-error");
    if (!input.value.trim()) return;
    btn.disabled = true; btn.textContent = t("Checking…"); box.innerHTML = "";
    try {
      const res = await fetch("/api/login/code", { method: "POST", credentials: "same-origin", headers: HEADERS, body: JSON.stringify({ code: input.value }) });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (res.status === 401 && /expired|Start again|از اول/.test(d.detail || "")) { await boot(); $("#login-error") && ($("#login-error").innerHTML = `<div class="error-box">${esc(d.detail)}</div>`); return; }
        throw new Error(d.detail || t("Couldn't sign in."));
      }
      await boot();
    } catch (err) {
      box.innerHTML = `<div class="error-box">${esc(err.message === "Failed to fetch" ? t("You're offline.") : err.message)}</div>`;
      btn.disabled = false; btn.textContent = t("Verify"); input.select();
      if (!REDUCED.matches) form.animate([{ transform: "translateX(0)" }, { transform: "translateX(-8px)" }, { transform: "translateX(8px)" }, { transform: "translateX(-4px)" }, { transform: "none" }], { duration: 320 });
    }
  };
}

// ------------------------------------------------------------------ shell
const NAV = [["posts", "#/", "Posts"], ["auto", "#/automations", "Automations"], ["inbox", "#/inbox", "Inbox"], ["chart", "#/insights", "Insights"], ["settings", "#/settings", "Settings"]];
function renderShell() {
  const nav = (cls) => NAV.map(([icon, href, label]) =>
    `<a href="${href}" data-nav="${icon}">${cls === "bottom" ? `<span class="bn-ic">${ic(icon, 22)}</span>` : ""}${t(label)}<span class="count" data-badge="${icon}" hidden></span></a>`).join("");
  $("#root").innerHTML = `
    <header class="topbar"><div class="topbar-in">
      <a class="brand" href="#/">${BOLT}<span class="hide-phone">replyloop</span></a>
      <nav class="tabs" aria-label="${t("Settings")}">${nav("top")}</nav>
      <span style="flex:1" class="show-phone"></span>
      <button class="icon-btn" id="theme-btn" data-act="theme" aria-label="${t("Switch theme")}"></button>
      <button class="acct-btn" id="acct-btn" data-act="accounts" aria-haspopup="menu"></button>
    </div><div id="progress" aria-hidden="true"></div></header>
    <main class="page" id="view"></main>
    <nav class="bottomnav" aria-label="${t("Settings")}">${nav("bottom")}</nav>`;
  applyTheme(store.get("rl_theme", "system"));
  renderAccountButton();
}

const vtName = (prefix, id) => `${prefix}-${String(id).replace(/[^a-zA-Z0-9_-]/g, "_")}`;
function avatarHtml(name, size = 32, extra = "") {
  return `<span class="avatar ${tintOf(name || "?")}" style="width:${size}px;height:${size}px;flex-basis:${size}px${extra}"${extra ? ' data-vt="ib-avatar"' : ""}>${esc((name || "?").replace(/^@/, "")[0] || "?")}</span>`;
}
function renderAccountButton() {
  const a = currentAccount();
  $("#acct-btn").innerHTML = a ? `${avatarHtml(a.username, 36)}<span class="name hide-phone">${handle(a.username)}</span>${ic("down", 16)}`
    : `<span class="avatar tint-1" style="width:36px;height:36px">${ic("user", 18)}</span>${ic("down", 16)}`;
  $("#acct-btn").setAttribute("aria-label", a ? t("Account: @{u}. Switch account", { u: a.username }) : t("Accounts"));
  $$("[data-badge=chart], [data-badge=posts], [data-badge=auto], [data-badge=settings]").forEach((b) => (b.hidden = true));
  $$("[data-badge=inbox]").forEach((b) => { const n = S.overview?.counts?.waiting; b.hidden = !n; b.textContent = n || ""; });
}

function accountMenu() {
  const items = S.accounts.map((a) => `
    <button class="menu-item ${a.id === S.aid ? "current" : ""}" role="menuitem" data-act="switch-account" data-id="${a.id}">
      ${avatarHtml(a.username, 42)}
      <span style="flex:1;min-width:0"><span style="display:block">${handle(a.username)}</span>
      <span class="small muted row" style="gap:6px;font-weight:500"><span class="dot" style="color:${a.live ? "var(--ok)" : "var(--warn)"}"></span>${t(a.is_demo ? "Demo" : a.live ? "Live" : "Test mode")}${a.waiting ? t(" · {n} waiting", { n: a.waiting }) : ""}${a.last_error ? t(" · needs attention") : ""}</span></span>
      ${a.id === S.aid ? `<span style="color:var(--accent-text)">${ic("check", 20, 2.4)}</span>` : ""}
    </button>`).join("");
  openMenu($("#acct-btn"), `<div class="menu-label">${t("YOUR ACCOUNTS")}</div>${items || `<p class="muted small" style="padding:6px 10px">${t("No accounts yet.")}</p>`}
    <div class="menu-sep"></div>
    <button class="menu-item" data-act="add-account"><span class="avatar" style="width:42px;height:42px;border:1.5px dashed var(--border-strong);color:var(--muted)">${ic("plus", 18)}</span>${t("Connect an Instagram account")}</button>
    <button class="menu-item" data-act="logout" style="color:var(--muted)"><span style="width:42px;display:grid;place-items:center">${ic("out", 18)}</span>${t("Sign out")}</button>`);
}

function switchAccount(id) {
  S.aid = id; store.set("rl_account", id);
  S.posts = null; S.overview = null; S.settings = null;
  closeLayer(); renderAccountButton();
  location.hash = "#/"; route();
}

// ------------------------------------------------------------------ router
async function route() {
  if (!S.me) return;
  const [name, arg] = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  const navKey = { "": "posts", post: "posts", automations: "auto", inbox: "inbox", insights: "chart", settings: "settings" }[name || ""] || "posts";
  const pos = routePos(name, arg);
  pendingNav = { navKey, dir: lastPos === null || !$("#view").childElementCount ? 0 : Math.sign(pos - lastPos) };
  if (lastPos === null || !$("#view").childElementCount) pendingNav.first = true;
  lastPos = pos;
  closeLayer();
  const view = $("#view");
  if (pendingNav.first) { pendingNav = null; setNav(navKey); }
  progress(true);
  try {
    if (!S.aid && name !== "settings") return await renderNoAccounts(view);
    if (name === "post" && arg) await renderPost(view, arg);
    else if (name === "automations") await renderAutomations(view);
    else if (name === "inbox") await renderInbox(view, arg);
    else if (name === "insights") await renderInsights(view, arg || "account");
    else if (name === "settings") await renderSettings(view);
    else await renderPosts(view);
  } catch (e) {
    if (e.message !== "signed out") await paint(view, `<div class="empty">${t("Couldn't load this page.")} ${esc(e.message)}<br><br><button class="btn" data-act="reload">${t("Try again")}</button></div>`);
  } finally {
    if (pendingNav && pendingNav.navKey === navKey) { setNav(navKey); pendingNav = null; }
    progress(false);
  }
}
window.addEventListener("hashchange", route);

async function loadOverview() {
  S.overview = await api(A("/overview"));
  const i = S.accounts.findIndex((a) => a.id === S.aid);
  if (i >= 0) S.accounts[i] = S.overview.account;
  renderAccountButton();
  return S.overview;
}
async function loadSettings() { if (!S.settings) S.settings = await api(A("/settings")); return S.settings; }

// ------------------------------------------------------------------ no accounts
async function renderNoAccounts(view) {
  if (!isOwner()) return paint(view, `<section class="hero" style="max-width:720px"><h1>${t("No Instagram accounts yet")}</h1>
    <p style="opacity:.85">${t("The owner connects Instagram accounts. Once they do, you'll see them here.")}</p></section>`);
  await paint(view, `<section class="hero" style="max-width:720px">
      <span class="chip" style="align-self:flex-start">${ic("spark", 15)} ${t("Getting started")}</span>
      <h1>${t("Connect your first Instagram account")}</h1>
      <p style="opacity:.85">${t("Paste an access token from your Meta app, or try everything with a demo account first. Nothing is sent to Instagram from a demo.")}</p>
      <div class="row"><button class="btn btn-light" data-act="add-account">${t("Connect account")}</button><button class="btn btn-outline" data-act="add-demo">${t("Try a demo account")}</button></div>
    </section>`);
}

// ------------------------------------------------------------------ posts
function postThumb(p, size = 36, named = false) {
  const icon = p.type === "REEL" ? "reel" : "photo";
  return `<div class="thumb ${tintOf(p.id)}" data-vt="post-thumb"${named ? ' style="view-transition-name:post-thumb"' : ""}>${p.thumb ? `<img src="${esc(p.thumb)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ic(icon, size, 1.4)}
    <span class="chip">${typeLabel(p.type)}</span>
    ${p.autoreply_enabled === false ? `<span class="chip paused">${t("Paused")}</span>` : ""}</div>`;
}
function postChip(p) {
  if (p.autoreply_enabled === false) return `<span class="chip bad">${t("Paused")}</span>`;
  if (p.gated) return `<span class="chip dm">${ic("follow", 14, 2)} ${t("Followers DM")}</span>`;
  if (p.rule_count) return `<span class="chip ok">${p.rule_count === 1 ? t("1 automation") : t("{n} automations", { n: p.rule_count })}</span>`;
  return `<span class="chip">${t("Global rules")}</span>`;
}

let postFilter = "all";
async function renderPosts(view, refresh = false) {
  const [ov, posts] = await Promise.all([loadOverview(), api(A(`/posts${refresh ? "?refresh=true" : ""}`))]);
  S.posts = posts;
  const a = ov.account, st = ov.stats;
  const headline = a.is_demo ? t("This is a demo. Open a post and tap Simulate to watch the bot work.")
    : !a.live ? t("Test mode: the bot decides and logs, but nothing is sent yet.")
    : (st.handled === 1 ? t("1 comment answered in the last 24 hours.") : t("{n} comments answered in the last 24 hours.", { n: st.handled }))
      + (st.waiting ? t(" {n} waiting on a follow.", { n: st.waiting }) : "");
  const filters = [["all", "All"], ["reels", "Reels"], ["posts", "Posts"], ["paused", "Paused"]];
  await paint(view, `
    ${a.last_error ? `<div class="note-box">${ic("warn", 16)} ${esc(a.last_error)} <a href="#/settings">${t("Open settings")}</a></div>` : ""}
    <div class="hero-row">
      <section class="hero">
        <span class="chip" style="align-self:flex-start"><span class="dot" style="color:${a.live ? "#5BD99A" : "#FFC24D"}"></span>${t(a.is_demo ? "Demo account" : a.live ? "Live" : "Test mode")} · ${handle(a.username)}</span>
        <h1>${esc(headline)}</h1>
        <div class="row">
          ${!a.live && !a.is_demo ? `<button class="btn btn-light" data-act="go-live">${t("Go live")}</button>` : ""}
          <a class="btn ${!a.live && !a.is_demo ? "btn-outline" : "btn-light"}" href="#/inbox">${t("Open inbox")}</a>
        </div>
      </section>
      <div class="stats">
        ${[["Public replies", st.replies], ["DMs delivered", st.dms], ["Waiting on follow", st.waiting], ["Skipped", st.skipped]].map(([l, n]) =>
          `<div class="stat"><span class="small muted" style="font-weight:600">${t(l)}</span><b>${n}</b></div>`).join("")}
      </div>
    </div>
    <section class="stack" style="gap:16px">
      <div class="row spread"><h2>${t("Your posts")}</h2>
        <div class="row" style="gap:8px">
          <div class="pills" role="group" aria-label="${t("Filter posts")}">${filters.map(([f, l]) =>
            `<button class="pill" data-act="post-filter" data-f="${f}" aria-pressed="${postFilter === f}">${t(l)}</button>`).join("")}</div>
          <button class="icon-btn" data-act="reload-posts" aria-label="${t("Reload posts from Instagram")}">${ic("refresh", 18)}</button>
        </div></div>
      <div class="posts" id="posts-grid"></div>
    </section>`);
  drawPosts();
}
function drawPosts() {
  const grid = $("#posts-grid");
  if (!grid) return;
  const list = (S.posts || []).filter((p) => postFilter === "all" || (postFilter === "reels" && p.type === "REEL")
    || (postFilter === "posts" && p.type !== "REEL") || (postFilter === "paused" && p.autoreply_enabled === false));
  grid.innerHTML = list.length ? list.map((p) => `
    <a class="post" href="#/post/${encodeURIComponent(p.id)}" style="--vtn:${vtName("p", p.id)}">${postThumb(p, 36, morph.post === p.id)}
      <div class="post-body"><div class="caption"${dirAttr(p.caption)}>${esc(p.caption) || `<span class="muted">${t("No caption")}</span>`}</div>
        <div class="row small muted" style="gap:8px">${postChip(p)}${p.comments_count ? `<span>${t("{n} comments", { n: p.comments_count })}</span>` : ""}</div></div>
    </a>`).join("") : `<div class="empty">${t("No posts here.")}</div>`;
}

// ------------------------------------------------------------------ one post
async function renderPost(view, mediaId) {
  if (!S.posts) S.posts = await api(A("/posts"));
  const p = S.posts.find((x) => x.id === mediaId);
  if (!p) { await paint(view, `<a class="back" href="#/">${ic("back", 18)} ${t("Posts")}</a><div class="empty">${t("This post isn't in your latest 25.")}</div>`); return; }
  if (!S.overview) await loadOverview();
  const [rules, globals, recent] = await Promise.all([api(A(`/rules?media_id=${encodeURIComponent(mediaId)}`)), api(A("/rules?media_id=global")),
    api(A(`/inbox?media_id=${encodeURIComponent(mediaId)}&limit=5`))]);
  await paint(view, `
    <a class="back" href="#/">${ic("back", 18)} ${t("Posts")}</a>
    <div class="two-col">
      <div class="stack" style="gap:20px">
        <section class="card">
          <div class="post-head">${postThumb(p, 28, true)}
            <div class="stack" style="gap:6px;min-width:0;flex:1">
              <span class="small muted" style="font-weight:700">${typeLabel(p.type)}</span>
              <h2 style="font-size:18px"${dirAttr(p.caption)}>${esc(p.caption) || t("No caption")}</h2>
              ${p.permalink ? `<a class="small row" style="gap:4px;font-weight:600" href="${esc(p.permalink)}" target="_blank" rel="noopener">${t("Open on Instagram")} ${ic("ext", 14)}</a>` : ""}
            </div></div>
          <div class="row" style="gap:6px 24px">
            <label class="switch"><input type="checkbox" data-post-toggle="autoreply_enabled" ${p.autoreply_enabled !== false ? "checked" : ""}><span class="track"></span><span>${t("Auto-reply on this post")}</span></label>
            <label class="switch"><input type="checkbox" data-post-toggle="ai_enabled" ${S.ai && p.ai_enabled !== false ? "checked" : ""} ${S.ai ? "" : "disabled"}><span class="track"></span><span class="txt">${t("AI fallback")}${S.ai ? "" : `<span class="small muted">${t("Add an AI key on the server")}</span>`}</span></label>
          </div>
        </section>
        <section class="card">
          <div class="card-head"><div><h3>${t("When someone comments here")}</h3><p class="small muted">${t("Checked top to bottom. The first match wins.")}</p></div>
            <button class="btn btn-dark btn-sm" data-act="new-rule" data-media="${esc(mediaId)}">${ic("plus", 16, 2.2)} ${t("New")}</button></div>
          <div id="rules-box" data-media="${esc(mediaId)}"></div>
          <div class="then"><span class="small muted" style="font-weight:700">${t("THEN")}</span>
            <a class="then-item" href="#/automations">${ic("globe", 18)}<span style="flex:1">${t("Automations for every post")}</span><span class="small muted">${globals.length}</span>${ic("chev", 16)}</a>
            <div class="then-item">${ic("spark", 18)}<span style="flex:1">${t("AI writes a reply")}</span><span class="small muted">${t(S.ai && p.ai_enabled !== false ? "On" : "Off")}</span></div>
          </div>
        </section>
      </div>
      <div class="stack" style="gap:20px">
        ${tryItCard(mediaId)}
        <section class="card"><div class="card-head"><h3>${t("Post stats")}</h3><a class="small" style="font-weight:600" href="#/insights/posts">${t("Compare")}</a></div>
          <div id="post-stats"><p class="small muted">${t("Loading…")}</p></div></section>
        <section class="card">
          <div><h3>${t("Info for the AI")}</h3><p class="small muted">${t("Facts the AI may use for this post, e.g. \"Pistachio latte, 140 TL, until Sunday\".")}</p></div>
          <textarea class="input" id="post-context" rows="3" maxlength="2000" dir="auto" ${canEdit() ? "" : "readonly"}>${esc(p.context || "")}</textarea>
          <button class="btn btn-sm" data-act="save-context" style="align-self:flex-start">${t("Save")}</button>
        </section>
        <section class="card">
          <div class="card-head"><h3>${t("Recent comments")}</h3><a class="small" style="font-weight:600" href="#/inbox">${t("All")}</a></div>
          ${recent.length ? `<ul class="list" style="box-shadow:none;padding:0;background:transparent">${recent.map((c) => inboxItem(c)).join("")}</ul>` : `<p class="small muted">${t("No comments handled on this post yet.")}</p>`}
        </section>
      </div>
    </div>`);
  drawRules($("#rules-box"), rules);
  postStats(mediaId);
}

function tryItCard(mediaId) {
  if (!canEdit()) return "";
  return `<section class="card" id="try-card">
    <div><h3>${t("Try a comment")}</h3><p class="small muted">${isTest() ? t("Preview what the bot would do, or simulate a real comment to see the whole flow in the inbox.") : t("Preview what the bot would do. Nothing is posted.")}</p></div>
    <textarea class="input" id="try-text" rows="2" maxlength="1000" dir="auto" placeholder="${esc(t("e.g. menu please! 🙏"))}"></textarea>
    <div class="row"><button class="btn btn-sm" data-act="try-preview" data-media="${esc(mediaId || "")}">${t("Preview")}</button>
      ${isTest() ? `<button class="btn btn-dark btn-sm" data-act="try-simulate" data-media="${esc(mediaId || "")}">${t("Simulate comment")}</button>` : ""}</div>
    <div id="try-result"></div></section>`;
}

const igBubble = (text, button) => `<div class="ig"><div class="ig-bubble"${dirAttr(text)}>${esc(text) || `<span class="ig-empty">${t("Message…")}</span>`}${button !== undefined && button !== null ? `<div class="ig-btn"${dirAttr(button)}>${esc(button) || `<span class="ig-empty">${t("Button")}</span>`}</div>` : ""}</div></div>`;

function sourceLabel(src) {
  if (!src) return "";
  if (src.startsWith("post:")) return t("Matched this post's automation “{n}”", { n: src.slice(5) });
  if (src.startsWith("global:")) return t("Matched the automation “{n}” (all posts)", { n: src.slice(7) });
  const m = { ai: "Written by AI", "ai-skip": "AI decided not to reply", ignored: "Matched the ignore list", paused: "Auto-reply is paused on this post", "no-match": "No automation matched" }[src];
  return m ? t(m) : src;
}

function decisionHtml(d) {
  if (!d.reply && !d.dm) return `<p class="small muted">${esc(t("No reply: {r}.", { r: sourceLabel(d.source) }))}</p>`;
  let h = `<p class="small muted" style="font-weight:600">${esc(sourceLabel(d.source))}</p>`;
  if (d.reply) h += `<div class="stack" style="gap:6px"><span class="step-label">${t("💬 Public reply")}</span><div class="bubble"${dirAttr(d.reply)}>${esc(d.reply)}</div></div>`;
  if (d.dm && d.followers_only) h += `
    <div class="steps"><span class="step-label">${t("📩 1 · They get")}</span>${igBubble(d.gate_text, d.gate_button)}
    <span class="step-label">${t("2 · They tap and follow you")}</span>${igBubble(d.dm)}
    <span class="step-label">${t("3 · They tap but don't follow yet")}</span>${igBubble(d.not_following_text, d.gate_button)}</div>`;
  else if (d.dm) h += `<div class="stack" style="gap:6px"><span class="step-label">${t("📩 DM")}</span>${igBubble(d.dm)}</div>`;
  return `<div class="stack" style="gap:12px">${h}</div>`;
}

// ------------------------------------------------------------------ automations list + editor
function drawRules(box, rules) {
  box._rules = rules;
  box.innerHTML = rules.length ? `<ol class="rules">${rules.map((r, i) => `
    <li class="rule ${r.enabled ? "" : "off"}" data-id="${r.id}" style="--vtn:r-${r.id}">
      <div class="order">
        <button data-act="rule-move" data-dir="-1" aria-label="${t("Move up")}" ${i === 0 ? "disabled" : ""}>${ic("up", 18, 2.2)}</button>
        <span class="num">${i + 1}</span>
        <button data-act="rule-move" data-dir="1" aria-label="${t("Move down")}" ${i === rules.length - 1 ? "disabled" : ""}>${ic("down", 18, 2.2)}</button>
      </div>
      <div class="rule-body">
        <div class="row" style="gap:8px"><b${dirAttr(r.name)}>${esc(r.name || t("Untitled"))}</b>${r.enabled ? "" : `<span class="chip">${t("Off")}</span>`}${r.followers_only ? `<span class="chip dm">${ic("follow", 13, 2)} ${t("Followers only")}</span>` : ""}</div>
        <div class="row" style="gap:5px">${r.keywords.map((k) => `<span class="kw"${dirAttr(k)}>${esc(k)}</span>`).join("")}</div>
        ${r.reply ? `<div class="rule-line"><span>💬</span><span${dirAttr(r.reply)}>${esc(r.reply)}</span></div>` : ""}
        ${r.dm ? `<div class="rule-line"><span>📩</span><span${dirAttr(r.dm)}>${esc(r.dm)}</span></div>` : ""}
      </div>
      <button class="icon-btn flat" data-act="rule-edit" aria-label="${esc(t("Edit {n}", { n: r.name || t("automation") }))}">${ic("edit", 18)}</button>
    </li>`).join("")}</ol>` : `<div class="empty">${t("No automations yet. Tap <b>New</b> to add one.")}</div>`;
}

async function openRuleEditor(box, rule) {
  const s = await loadSettings();
  const r = rule || { name: "", keywords: [], reply: "", dm: "", followers_only: false, gate_text: "", gate_button: "", not_following_text: "", enabled: true };
  const optional = `<span class="muted" style="font-weight:500">${t("(optional)")}</span>`;
  const sheet = openSheet(t(rule ? "Edit automation" : "New automation"), `
    <form id="rule-form" class="stack" style="gap:18px" novalidate>
      <label class="field"><span>${t("Name")}</span><input class="input" name="name" maxlength="60" dir="auto" value="${esc(r.name)}" placeholder="${esc(t("e.g. Menu link"))}"></label>
      <label class="field"><span>${t("When the comment contains any of")}</span>
        <input class="input" name="keywords" maxlength="1500" dir="auto" value="${esc(r.keywords.join(FA_MODE ? "، " : ", "))}" placeholder="${FA_MODE ? "لینک، منو، link" : "menu, link, لینک"}">
        <span class="hint">${t("Separate with commas. Capitals and Turkish letters don't matter.")}</span><div class="row" id="kw-preview" style="gap:5px"></div></label>
      <label class="field"><span>${t("💬 Public reply under the comment")} ${optional}</span>
        <textarea class="input" name="reply" rows="2" maxlength="1000" dir="auto" placeholder="${esc(t("@{username} Sent you a DM 📩"))}">${esc(r.reply)}</textarea>
        <span class="hint">${t("{username} becomes their username.")}</span></label>
      <label class="field"><span>${t("📩 DM with the details")} ${optional}</span>
        <textarea class="input" name="dm" rows="3" maxlength="1000" dir="auto" placeholder="${esc(t("Here's the link: …"))}">${esc(r.dm)}</textarea></label>
      <div class="stack" style="gap:12px;padding:16px;border-radius:20px;background:var(--bg)">
        <label class="switch"><input type="checkbox" name="followers_only" ${r.followers_only ? "checked" : ""}><span class="track"></span>
          <span class="txt"><b>${t("Only send the DM to followers")}</b><span class="small muted">${t("They get a button first. When they tap it, the bot checks if they follow you.")}</span></span></label>
        <div id="gate" class="stack" style="gap:14px" ${r.followers_only ? "" : "hidden"}>
          <label class="field"><span>${t("First message")}</span><textarea class="input" name="gate_text" rows="2" maxlength="640" dir="auto" placeholder="${esc(s.gate_message)}">${esc(r.gate_text)}</textarea></label>
          <label class="field"><span>${t("Button text")}</span><span class="input-wrap"><input class="input" name="gate_button" maxlength="20" dir="auto" value="${esc(r.gate_button)}" placeholder="${esc(s.gate_button)}"><span class="counter" id="btn-count" dir="ltr"></span></span></label>
          <label class="field"><span>${t("If they tap but don't follow yet")}</span><textarea class="input" name="not_following_text" rows="2" maxlength="640" dir="auto" placeholder="${esc(s.not_following_message)}">${esc(r.not_following_text)}</textarea>
            <span class="hint">${t("Sent with the same button again. Empty fields use your defaults from Settings.")}</span></label>
          <div class="steps"><span class="step-label">${t("Preview: first message")}</span><div id="gate-preview"></div><span class="step-label">${t("Preview: not following yet")}</span><div id="nf-preview"></div></div>
        </div>
      </div>
      <label class="switch"><input type="checkbox" name="enabled" ${r.enabled ? "checked" : ""}><span class="track"></span><span>${t("Automation on")}</span></label>
    </form>`,
    `${rule ? `<button class="btn btn-ghost btn-danger" data-act="rule-delete">${ic("trash", 18)}<span class="hide-phone">${t("Delete")}</span></button>` : ""}
     <button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-dark grow" data-act="rule-save">${t("Save")}</button>`);
  const f = $("#rule-form", sheet);
  const refresh = () => {
    $("#kw-preview", sheet).innerHTML = splitList(f.keywords.value).map((k) => `<span class="kw"${dirAttr(k)}>${esc(k)}</span>`).join("");
    $("#gate", sheet).hidden = !f.followers_only.checked;
    const btn = f.gate_button.value.trim() || s.gate_button;
    $("#btn-count", sheet).textContent = `${[...f.gate_button.value].length}/20`;
    $("#gate-preview", sheet).innerHTML = igBubble(f.gate_text.value.trim() || s.gate_message, btn);
    $("#nf-preview", sheet).innerHTML = igBubble(f.not_following_text.value.trim() || s.not_following_message, btn);
  };
  f.addEventListener("input", refresh); f.addEventListener("change", refresh); refresh();
  sheet._save = async () => {
    const body = {
      media_id: box.dataset.media || null, name: f.name.value.trim(), keywords: splitList(f.keywords.value),
      reply: f.reply.value.trim(), dm: f.dm.value.trim(), followers_only: f.followers_only.checked,
      gate_text: f.gate_text.value.trim(), gate_button: f.gate_button.value.trim(), not_following_text: f.not_following_text.value.trim(),
      enabled: f.enabled.checked,
    };
    if (!body.keywords.length) return toast(t("Add at least one keyword."), true);
    if (!body.reply && !body.dm) return toast(t("Add a public reply, a DM, or both."), true);
    if (body.followers_only && !body.dm) return toast(t("“Followers only” needs a DM."), true);
    await api(rule ? A(`/rules/${rule.id}`) : A("/rules"), { method: rule ? "PUT" : "POST", body });
    closeLayer(); toast(t("Automation saved"));
    reloadRules(box);
  };
  sheet._delete = async () => {
    if (!(await confirmSheet(t("Delete automation?"), t("“{n}” will stop working right away.", { n: rule.name || t("Untitled") }), t("Delete"), true))) return;
    await api(A(`/rules/${rule.id}`), { method: "DELETE" });
    toast(t("Automation deleted")); reloadRules(box);
  };
}
async function reloadRules(box) {
  const mid = box.dataset.media || "global";
  drawRules(box, await api(A(`/rules?media_id=${encodeURIComponent(mid)}`)));
  S.posts = null;
}

// ------------------------------------------------------------------ automations (all posts)
async function renderAutomations(view) {
  const rules = await api(A("/rules?media_id=global"));
  await paint(view, `
    <div class="stack" style="gap:6px"><h1>${t("Automations")}</h1><p class="muted">${t("These work on every post, after the post's own automations.")}</p></div>
    <div class="two-col">
      <section class="card">
        <div class="card-head"><div><h3>${t("For every post")}</h3><p class="small muted">${t("Checked top to bottom. The first match wins.")}</p></div>
          <button class="btn btn-dark btn-sm" data-act="new-rule" data-media="">${ic("plus", 16, 2.2)} ${t("New")}</button></div>
        <div id="rules-box" data-media=""></div>
      </section>
      ${tryItCard(null)}
    </div>`);
  drawRules($("#rules-box"), rules);
}

// ------------------------------------------------------------------ inbox
const FILTERS = [["all", "All"], ["waiting", "Waiting"], ["delivered", "DM sent"], ["replied", "Replied"], ["skipped", "Skipped"], ["errors", "Errors"]];
let inboxFilter = "all";
function statusChip(c) {
  if ((c.status || "").startsWith("error") || (c.dm_status || "").startsWith("error")) return `<span class="chip bad">${t("Error")}</span>`;
  if ((c.dm_status || "").startsWith("waiting")) return `<span class="chip warn">${t("Waiting")}</span>`;
  if (c.dm_status === "delivered") return `<span class="chip ok">${t("Follower · sent")}</span>`;
  if (c.dm_status === "sent") return `<span class="chip dm">${t("DM sent")}</span>`;
  if (c.status === "skipped") return `<span class="chip">${t("Skipped")}</span>`;
  if (c.reply) return `<span class="chip info">${t("Replied")}</span>`;
  return `<span class="chip">${esc(c.status || "")}</span>`;
}
function postName(mid) {
  const p = (S.posts || []).find((x) => x.id === mid);
  if (!p) return mid ? t("a post") : "";
  const c = p.caption || typeLabel(p.type);
  const ch = Array.from(c); return ch.length > 32 ? ch.slice(0, 32).join("").trimEnd() + "…" : c;
}
function inboxItem(c, current) {
  return `<li><a class="item" href="#/inbox/${encodeURIComponent(c.comment_id)}" ${current ? 'aria-current="true"' : ""}>
    ${avatarHtml(c.username, 40, innerWidth <= 960 && morph.inbox === c.comment_id ? ";view-transition-name:ib-avatar" : ";")}
    <span class="item-main"><span class="row spread" style="flex-wrap:nowrap"><b>${handle(c.username)}</b><span class="small muted">${ago(c.created_at)}</span></span>
      <span class="item-text"${dirAttr(c.text)}>${esc(c.text)}</span>
      <span class="row small muted" style="gap:6px;flex-wrap:nowrap">${statusChip(c)}${c.status === "test" ? `<span class="chip">${t("Test")}</span>` : ""}<span class="item-text"${dirAttr(postName(c.media_id))}>${esc(postName(c.media_id))}</span></span></span></a></li>`;
}

async function renderInbox(view, cid) {
  if (!S.posts) S.posts = await api(A("/posts")).catch(() => []);
  const [ov, items, detail] = await Promise.all([loadOverview(), api(A(`/inbox?filter=${inboxFilter}`)),
    cid ? api(A(`/inbox/${encodeURIComponent(cid)}`)) : null]);
  const wide = innerWidth > 960;
  const showList = wide || !cid;
  const empty = inboxFilter === "all" ? t(isTest() ? "Nothing yet. Simulate a comment from a post to see how it works." : "No comments yet. New ones show up here.") : t("Nothing here.");
  await paint(view, `
    ${showList ? `<div class="stack" style="gap:14px"><h1>${t("Inbox")}</h1>
      <div class="pills" role="group" aria-label="${t("Filter")}">${FILTERS.map(([k, l]) =>
        `<button class="pill" data-act="inbox-filter" data-f="${k}" aria-pressed="${inboxFilter === k}">${t(l)}<span class="n">${ov.counts[k] ?? ""}</span></button>`).join("")}</div></div>` : ""}
    <div class="inbox ${showList && cid ? "" : "single"}">
      ${showList ? (items.length ? `<ul class="list">${items.map((c) => inboxItem(c, c.comment_id === cid)).join("")}</ul>` : `<div class="empty">${empty}</div>`) : ""}
      ${cid ? `<div class="detail-pane" id="detail"></div>` : (wide && items.length ? `<div class="detail-pane empty-pane"><div class="empty">${t("Choose a comment to see what happened.")}</div></div>` : "")}
    </div>`);
  if (cid) await renderDetail($("#detail"), cid, !wide, detail);
}

const EV = {
  comment: ["msg", "", "Commented"], reply: ["msg", "", "Public reply"], dm: ["send", "dm", "DM sent"], dm_button: ["send", "dm", "DM with button sent"],
  tap: ["tap", "", "Tapped the button"], message: ["msg", "", "Sent a message"], not_following: ["warn", "warn", "Not following yet: button sent again"],
  details: ["follow", "ok", "Follows you: details sent"], check_failed: ["warn", "warn", "Couldn't check follow status: asked for a message"],
  skipped: ["skip", "", "Skipped"], error: ["warn", "bad", "Error"],
};
async function renderDetail(el, cid, showBack, preloaded = null) {
  const c = preloaded || await api(A(`/inbox/${encodeURIComponent(cid)}`));
  const test = c.status === "test";
  el.innerHTML = `
    ${showBack ? `<a class="back" href="#/inbox">${ic("back", 18)} ${t("Inbox")}</a>` : ""}
    <section class="card">
      <div class="row" style="flex-wrap:nowrap">${avatarHtml(c.username, 44, ";view-transition-name:ib-avatar")}
        <div style="flex:1;min-width:0"><h3>${handle(c.username)}</h3><p class="small muted">${c.media_id ? esc(t("On “{p}”", { p: postName(c.media_id) })) + " · " : ""}${esc(sourceLabel(c.source))}</p></div>
        ${statusChip(c)}</div>
      ${test ? `<div class="note-box small">${t("Test mode: this was logged but nothing was sent to Instagram.")}</div>` : ""}
      <ol class="timeline">${c.events.map((e) => {
        const [icon, tone, title] = EV[e.kind] || ["msg", "", e.kind];
        const bubble = ["dm", "dm_button", "not_following", "details", "check_failed"].includes(e.kind) ? igBubble(e.text, e.button || null)
          : ["comment", "reply", "message"].includes(e.kind) && e.text ? `<div class="bubble"${dirAttr(e.text)}>${esc(e.text)}</div>`
          : e.kind === "tap" && e.text ? `<span class="chip"${dirAttr(e.text)}>${esc(e.text)}</span>`
          : e.text ? `<p class="small muted">${esc(e.kind === "skipped" ? sourceLabel(e.text) : e.text)}</p>` : "";
        return `<li class="ev"><div class="ev-rail"><span class="ev-dot ${tone}">${ic(icon, 15, 2)}</span><span class="ev-line"></span></div>
          <div class="ev-body"><div class="ev-title"><span>${t(title)}</span><time>${clock(e.created_at)}</time></div>${bubble}</div></li>`;
      }).join("")}</ol>
      ${c.pending_dm && isTest() ? `<div class="stack" style="gap:10px;padding:14px;border-radius:18px;background:var(--bg)">
          <b>${t("Simulate their tap")}</b><p class="small muted">${t("See what happens when they tap the button.")}</p>
          <div class="row"><button class="btn btn-sm btn-dark" data-act="sim-tap" data-cid="${esc(c.comment_id)}" data-follows="1">${ic("follow", 16)} ${t("They follow you")}</button>
          <button class="btn btn-sm" data-act="sim-tap" data-cid="${esc(c.comment_id)}" data-follows="0">${t("Not following yet")}</button></div></div>` : ""}
    </section>`;
}

// ------------------------------------------------------------------ insights
const nf = new Intl.NumberFormat(NUM_LOCALE, { notation: "compact", maximumFractionDigits: 1 });
const num = (v) => (v === null || v === undefined ? "—" : nf.format(v));
const pct = (v) => (v === null || v === undefined ? "—" : `${v}%`);
const shortDay = (d) => new Date(d + "T12:00:00").toLocaleDateString(DATE_LOCALE, { day: "numeric", month: "short" });
let insDays = 7;
let postSort = "views";
let audDim = "country";

const INS_TABS = [["account", "Account"], ["posts", "Posts & Reels"], ["stories", "Stories"], ["impact", "Bot impact"]];

async function renderInsights(view, tab) {
  if (!INS_TABS.some(([k]) => k === tab)) tab = "account";
  await paint(view, `
    <div class="row spread"><h1>${t("Insights")}</h1>
      <div class="seg" role="group" aria-label="${t("Period")}">${[7, 30].map((d) => `<button data-act="ins-days" data-d="${d}" aria-pressed="${insDays === d}">${t("{n} days", { n: d })}</button>`).join("")}</div></div>
    <div class="pills" role="tablist" aria-label="${t("Insights sections")}">${INS_TABS.map(([k, l]) =>
      `<a class="pill" role="tab" href="#/insights/${k}" aria-pressed="${k === tab}" aria-selected="${k === tab}" style="text-decoration:none">${t(l)}</a>`).join("")}</div>
    <div id="ins-body" class="stack" style="gap:20px">${skeleton()}</div>`);
  const body = $("#ins-body");
  if (tab === "account") await insAccount(body);
  else if (tab === "posts") await insPosts(body);
  else if (tab === "stories") await insStories(body);
  else await insImpact(body);
}

const skeleton = () => `<div class="skel" aria-label="${esc(t("Loading…"))}"><div class="kpis">${"<div class=\"stat kpi\"><i></i><i></i></div>".repeat(4)}</div><div class="card"><i></i><i class="tall"></i></div></div>`;
function kpi(label, value, sub = "", icon = "") {
  return `<div class="stat kpi"><span class="small muted row" style="gap:6px;font-weight:600">${icon ? ic(icon, 15) : ""}${esc(label)}</span><b dir="auto">${value}</b>${sub ? `<span class="small muted">${sub}</span>` : ""}</div>`;
}

function lineChart(points, label) {
  if (points.length < 2) return "";
  const W = 600, H = 160, vals = points.map((p) => p.v), min = Math.min(...vals), max = Math.max(...vals), span = max - min || 1;
  const xy = points.map((p, i) => [(i / (points.length - 1)) * W, H - 8 - ((p.v - min) / span) * (H - 24)]);
  const line = xy.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = xy[xy.length - 1];
  // charts always run left (older) to right (newer), as in Instagram's own Persian app
  return `<div dir="ltr"><svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(label)}">
      <path d="${line} L${W},${H} L0,${H} Z" fill="currentColor" opacity=".12"/>
      <path d="${line}" fill="none" stroke="currentColor" stroke-width="2.5" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>
      <circle cx="${last[0]}" cy="${last[1]}" r="4" fill="currentColor" vector-effect="non-scaling-stroke"/></svg>
    <div class="row spread small muted"><span>${shortDay(points[0].d)}</span><span>${shortDay(points[points.length - 1].d)}</span></div></div>`;
}

function columns(points, label) {
  if (!points.length) return `<p class="small muted">${t("No data yet.")}</p>`;
  const max = Math.max(...points.map((p) => p.v)) || 1;
  return `<div dir="ltr"><div class="cols" role="img" aria-label="${esc(label)}">${points.map((p, i) =>
      `<span title="${esc(shortDay(p.d))}: ${p.v.toLocaleString(NUM_LOCALE)}" style="height:${Math.max(3, (p.v / max) * 100)}%;--i:${i}"></span>`).join("")}</div>
    <div class="row spread small muted"><span>${shortDay(points[0].d)}</span><span>${shortDay(points[points.length - 1].d)}</span></div></div>`;
}

function hbars(items, { total, fmt = num } = {}) {
  if (!items.length) return `<p class="small muted">${t("Not available yet.")}</p>`;
  const max = Math.max(...items.map((i) => i.v)) || 1;
  const sum = total ?? items.reduce((a, i) => a + i.v, 0);
  return `<ul class="hbars">${items.map((i) => `<li><span class="hb-label"${dirAttr(i.label)}>${esc(i.label)}</span>
      <span class="hb-track"><span style="width:${(i.v / max) * 100}%"></span></span>
      <span class="hb-val" dir="auto">${fmt(i.v)}${sum ? ` <span class="muted">${Math.round((i.v / sum) * 100)}%</span>` : ""}</span></li>`).join("")}</ul>`;
}

const regionName = (() => { try { const d = new Intl.DisplayNames(FA_MODE ? "fa" : undefined, { type: "region" }); return (c) => d.of(c) || c; } catch { return (c) => c; } })();
const GENDER = { F: "Women", M: "Men", U: "Not specified" };

async function insAccount(body, refresh = false) {
  const d = await api(A(`/insights/account?days=${insDays}${refresh ? "&refresh=true" : ""}`));
  if (d.error) { body.innerHTML = `<div class="note-box">${esc(d.error)}</div>`; return; }
  const tot = d.totals || {};
  const hist = (d.follower_history || []).slice(-Math.max(insDays, 2));
  const change = hist.length > 1 ? hist[hist.length - 1].followers - hist[0].followers : null;
  body.innerHTML = `
    ${d.demo ? `<div class="note-box small">${t("Demo data. Real numbers appear when you connect an Instagram account.")}</div>` : ""}
    <div class="kpis">
      ${kpi(t("Views"), num(tot.views), "", "eye")}${kpi(t("Reach"), num(tot.reach), t("accounts that saw you"), "user")}
      ${kpi(t("Interactions"), num(tot.total_interactions), d.engagement_rate != null ? t("{n}% of reach", { n: d.engagement_rate }) : "", "msg")}
      ${kpi(t("Accounts engaged"), num(tot.accounts_engaged), "", "follow")}
      ${kpi(t("Profile link taps"), num(tot.profile_links_taps), "", "ext")}
      ${kpi(t("Net follows"), d.net_follows == null ? "—" : (d.net_follows > 0 ? "+" : "") + num(d.net_follows),
        d.net_follows == null ? t("needs 100+ followers") : `<bdi dir="ltr">+${num(tot.follows)} / −${num(tot.unfollows)}</bdi>`, "chart")}
    </div>
    <div class="two-col">
      <section class="card"><div class="card-head"><div><h3>${t("Followers")}</h3><p class="small muted">${t("{n} now", { n: num(d.followers) })}${change != null ? t(" · {c} in {d} days", { c: `<bdi dir="ltr">${change >= 0 ? "+" : ""}${change}</bdi>`, d: insDays }) : ""}</p></div></div>
        <div style="color:var(--accent)">${lineChart(hist.map((h) => ({ d: h.day, v: h.followers })), t("Followers over time")) || `<p class="small muted">${t("The chart builds up from today: the app saves your follower count once a day.")}</p>`}</div></section>
      <section class="card"><div class="card-head"><div><h3>${t("Reach per day")}</h3><p class="small muted">${t("Accounts that saw your content")}</p></div></div>
        ${columns((d.reach_by_day || []).map((p) => ({ d: p.day, v: p.value })), t("Reach per day"))}</section>
    </div>
    <section class="card"><div class="card-head"><div><h3>${t("Your audience")}</h3><p class="small muted">${t("Followers this month")}</p></div>
        <div class="seg" role="group" aria-label="${t("Audience")}">${[["country", "Countries"], ["city", "Cities"], ["age", "Age"], ["gender", "Gender"]].map(([k, l]) =>
          `<button data-act="aud-dim" data-k="${k}" aria-pressed="${audDim === k}">${t(l)}</button>`).join("")}</div></div>
      <div id="aud">${audienceBars(d.audience || {})}</div></section>
    <button class="btn btn-sm" data-act="ins-refresh" data-what="account" style="align-self:flex-start">${ic("refresh", 16)} ${t("Refresh from Instagram")}</button>`;
  body._aud = d.audience || {};
}
function audienceBars(aud) {
  const raw = aud[audDim] || {};
  let items = Object.entries(raw).map(([k, v]) => ({ label: audDim === "country" ? regionName(k) : audDim === "gender" ? t(GENDER[k] || k) : k, v }));
  items = audDim === "age" ? items.sort((a, b) => a.label.localeCompare(b.label)) : items.sort((a, b) => b.v - a.v).slice(0, 6);
  return items.length ? hbars(items, { total: Object.values(raw).reduce((a, b) => a + b, 0) })
    : `<p class="small muted">${t("Instagram shows audience details once an account has 100+ followers.")}</p>`;
}

const SORTS = [["views", "Views"], ["reach", "Reach"], ["engagement", "Engagement"], ["saved", "Saves"], ["shares", "Shares"]];
async function insPosts(body, refresh = false) {
  const d = await api(A(`/insights/posts${refresh ? "?refresh=true" : ""}`));
  if (d.error) { body.innerHTML = `<div class="note-box">${esc(d.error)}</div>`; return; }
  body._posts = d.posts;
  body.innerHTML = `
    ${d.demo ? `<div class="note-box small">${t("Demo data.")}</div>` : ""}
    ${d.partial ? `<div class="note-box small">${t("Instagram didn't return stats for {n} post(s) (very new posts can take up to 48 hours).", { n: d.partial })}</div>` : ""}
    <div class="row spread"><div class="pills" role="group" aria-label="${t("Sort by")}">${SORTS.map(([k, l]) =>
      `<button class="pill" data-act="post-sort" data-k="${k}" aria-pressed="${postSort === k}">${t(l)}</button>`).join("")}</div>
      <button class="icon-btn" data-act="ins-refresh" data-what="posts" aria-label="${t("Refresh from Instagram")}">${ic("refresh", 18)}</button></div>
    <ol class="ranked" id="ranked"></ol>
    <p class="small muted">${t("Your latest 25 posts · numbers are organic and can be up to 48 hours behind.")}</p>`;
  drawRanked();
}
function drawRanked() {
  const box = $("#ins-body"), list = [...(box._posts || [])];
  const val = (p) => postSort === "engagement" ? p.engagement_rate : p.stats[postSort];
  list.sort((a, b) => (val(b) ?? -1) - (val(a) ?? -1));
  $("#ranked").innerHTML = list.map((p, i) => {
    const s = p.stats || {};
    const extra = p.type === "REEL" && s.ig_reels_avg_watch_time ? t(" · {s}s avg watch", { s: (s.ig_reels_avg_watch_time / 1000).toFixed(1) }) : "";
    return `<li style="--vtn:${vtName("k", p.id)}"><a class="rank-row" href="#/post/${encodeURIComponent(p.id)}">
      <span class="rank-n">${i + 1}</span>${postThumb(p, 22)}
      <span class="rank-main"><span class="caption"${dirAttr(p.caption)}>${esc(p.caption) || t("No caption")}</span>
        <span class="small muted">${typeLabel(p.type)} · ${t("{r} reach · {l} likes · {c} comments", { r: num(s.reach), l: num(s.likes), c: num(s.comments) })}${extra}</span></span>
      <span class="rank-val"><b dir="auto">${postSort === "engagement" ? pct(p.engagement_rate) : num(val(p))}</b><span class="small muted">${t(SORTS.find(([k]) => k === postSort)[1])}</span></span></a></li>`;
  }).join("") || `<div class="empty">${t("No posts yet.")}</div>`;
}

async function insStories(body, refresh = false) {
  const d = await api(A(`/insights/stories?days=${insDays}${refresh ? "&refresh=true" : ""}`));
  const list = d.stories || [];
  const tot = (k) => list.reduce((a, s) => a + (s.stats[k] || 0), 0);
  body.innerHTML = `
    ${d.error ? `<div class="note-box">${esc(d.error)}</div>` : ""}
    <div class="note-box small" style="background:var(--info-bg);color:var(--info)">${t("Instagram deletes story stats 24 hours after posting, so the app saves them every hour while a story is live. Stories with fewer than 5 viewers have no stats.")}</div>
    ${list.length ? `<div class="kpis">${kpi(t("Stories"), list.length, t("last {n} days", { n: insDays }), "story")}${kpi(t("Views"), num(tot("views")), "", "eye")}${kpi(t("Replies"), num(tot("replies")), "", "msg")}
      ${kpi(t("Link clicks"), num(tot("link_clicks")), "", "ext")}${kpi(t("Follows"), num(tot("follows")), "", "follow")}
      ${kpi(t("Avg. views"), num(Math.round(tot("views") / list.length)), t("per story"), "chart")}</div>` : ""}
    <div class="row spread"><h2>${t("Saved stories")}</h2><button class="btn btn-sm" data-act="ins-refresh" data-what="stories">${ic("refresh", 16)} ${t("Save live stories now")}</button></div>
    ${list.length ? `<div class="story-grid">${list.map((s) => `
      <article class="story">
        <div class="story-thumb ${tintOf(s.id)}">${s.thumb ? `<img src="${esc(s.thumb)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ic("story", 28, 1.4)}
          <span class="chip">${ago(s.posted_at)}</span></div>
        ${s.stats.too_few_viewers ? `<p class="small muted">${t("Fewer than 5 viewers: no stats.")}</p>` : `
        <dl class="story-stats">
          <div><dt>${t("Views")}</dt><dd dir="auto">${num(s.stats.views)}</dd></div><div><dt>${t("Reach")}</dt><dd dir="auto">${num(s.stats.reach)}</dd></div>
          <div><dt>${t("Replies")}</dt><dd dir="auto">${num(s.stats.replies)}</dd></div><div><dt>${t("Exits")}</dt><dd dir="auto">${pct(s.exit_rate)}</dd></div>
          <div><dt>${t("Link clicks")}</dt><dd dir="auto">${num(s.stats.link_clicks)}</dd></div><div><dt>${t("Follows")}</dt><dd dir="auto">${num(s.stats.follows)}</dd></div>
        </dl>`}
        ${s.permalink ? `<a class="small" style="font-weight:600" href="${esc(s.permalink)}" target="_blank" rel="noopener">${t("Open")} ${ic("ext", 13)}</a>` : ""}
      </article>`).join("")}</div>` : `<div class="empty">${t("No stories saved yet. Post a story, and it shows up here within an hour (or tap <b>Save live stories now</b>).")}</div>`}`;
}

async function insImpact(body) {
  const d = await api(A(`/insights/impact?days=${insDays}`));
  const f = d.funnel;
  const conv = f.not_following ? Math.round((f.converted / f.not_following) * 100) : null;
  const ruleName = (src) => src === "ai" ? t("AI replies") : src.replace(/^(post|global):/, "");
  body.innerHTML = `
    <div class="kpis">
      ${kpi(t("Comments answered"), num(d.answered), t("of {n} comments", { n: num(d.comments) }), "msg")}
      ${kpi(t("Public replies"), num(d.replies), "", "send")}
      ${kpi(t("DMs delivered"), num(d.dms), "", "send")}
      ${kpi(t("Follows from the button"), num(f.converted), conv != null ? t("{n}% of non-followers who tapped", { n: conv }) : t("people who followed to get your DM"), "follow")}
    </div>
    <div class="two-col">
      <section class="card"><div><h3>${t("Follow button funnel")}</h3><p class="small muted">${t("Followers-only DMs in the last {n} days", { n: insDays })}</p></div>
        ${f.buttons ? hbars([{ label: t("Got the button"), v: f.buttons }, { label: t("Tapped it"), v: f.tapped }, { label: t("Weren't following"), v: f.not_following }, { label: t("Followed → got details"), v: f.converted }], { total: f.buttons })
          + `<p class="small muted">${t("{n} were already following and got the details straight away.", { n: num(f.already_following) })}</p>`
          : `<p class="small muted">${t("No followers-only DMs in this period.")}</p>`}</section>
      <section class="card"><div><h3>${t("By automation")}</h3><p class="small muted">${t("Which ones do the most work")}</p></div>
        ${d.by_rule.length ? `<div style="overflow-x:auto"><table class="table"><thead><tr><th>${t("Automation")}</th><th>${t("Comments")}</th><th>${t("Replies")}</th><th>${t("DMs")}</th><th>${t("Follows")}</th></tr></thead><tbody>
          ${d.by_rule.map((r) => `<tr><td${dirAttr(ruleName(r.source))}>${esc(ruleName(r.source))}</td><td>${r.comments}</td><td>${r.replies}</td><td>${r.dms}</td><td>${r.gated ? `${r.converted}` : "—"}</td></tr>`).join("")}
          </tbody></table></div>` : `<p class="small muted">${t("Nothing yet in this period.")}</p>`}</section>
    </div>
    ${isTest() && !currentAccount().is_demo ? `<p class="small muted">${t("Comments handled in test mode aren't counted here, since nothing was actually sent.")}</p>` : ""}`;
}

async function postStats(mediaId) {
  const box = $("#post-stats");
  if (!box) return;
  try {
    const d = await api(A("/insights/posts"));
    const p = (d.posts || []).find((x) => x.id === mediaId);
    if (!p || !p.stats || !Object.keys(p.stats).length) { box.innerHTML = `<p class="small muted">${esc(d.error || t("No stats for this post yet."))}</p>`; return; }
    const s = p.stats;
    box.innerHTML = `<dl class="story-stats" style="grid-template-columns:repeat(3,minmax(0,1fr))">
      ${[["Views", s.views], ["Reach", s.reach], ["Likes", s.likes], ["Comments", s.comments], ["Saves", s.saved], ["Shares", s.shares]].map(([l, v]) =>
        `<div><dt>${t(l)}</dt><dd dir="auto">${num(v)}</dd></div>`).join("")}</dl>
      <p class="small muted">${t("Engagement {e}", { e: `<bdi dir="ltr">${pct(p.engagement_rate)}</bdi>` })}${s.ig_reels_avg_watch_time ? t(" · {s}s average watch time", { s: (s.ig_reels_avg_watch_time / 1000).toFixed(1) }) : ""}</p>`;
  } catch { box.innerHTML = `<p class="small muted">${t("Stats unavailable.")}</p>`; }
}

// ------------------------------------------------------------------ settings
async function renderSettings(view) {
  const a = currentAccount();
  const s = a ? await loadSettings() : null;
  const [users, sec] = await Promise.all([isOwner() ? api("/users") : [], api("/security")]);
  const theme = store.get("rl_theme", "system");
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  await paint(view, `
    <div class="stack" style="gap:6px"><h1>${t("Settings")}</h1>${a ? `<p class="muted">${t("For @{u}, unless marked otherwise.", { u: `<bdi dir="ltr">${esc(a.username)}</bdi>` })}</p>` : ""}</div>
    ${S.keyWarning ? `<div class="note-box">${t("SECRET_KEY isn't set on the server, so saved Instagram tokens are lost on every restart. Add it in your hosting settings.")}</div>` : ""}
    ${S.dbWarning ? `<div class="note-box">${t("DATABASE_URL isn't set, so everything is stored in a temporary file that Render deletes on restart. Add your Supabase URL.")}</div>` : ""}
    <div class="two-col">
      <div class="stack" style="gap:20px">
        ${a ? `
        <section class="card">
          <div class="card-head"><div class="row" style="flex-wrap:nowrap">${avatarHtml(a.username, 44)}<div><h3>${handle(a.username)}</h3>
            <p class="small muted">${a.is_demo ? t("Demo account") : a.token_ok ? t("Token refreshed {t}", { t: ago(a.token_refreshed_at) }) : t("Token can't be read: reconnect")}</p></div></div></div>
          ${a.last_error ? `<div class="note-box small">${esc(a.last_error)}</div>` : ""}
          ${isOwner() ? `<div class="field"><span>${t("Mode")}</span>
            <div class="seg" role="group" aria-label="${t("Mode")}"><button data-act="set-live" data-live="0" aria-pressed="${!a.live}">${t("Test mode")}</button><button data-act="set-live" data-live="1" aria-pressed="${a.live}" ${a.is_demo ? "disabled" : ""}>${t("Live")}</button></div>
            <span class="hint">${t(a.is_demo ? "A demo account can't go live." : "Test mode logs what the bot would do. Live sends replies and DMs on Instagram.")}</span></div>
          <div class="row">${a.is_demo ? "" : `<button class="btn btn-sm" data-act="add-account">${t("Reconnect / new token")}</button>`}<button class="btn btn-sm btn-ghost btn-danger" data-act="remove-account">${ic("trash", 16)} ${t("Remove account")}</button></div>`
          : `<p class="small muted row" style="gap:6px;flex-wrap:nowrap"><span class="dot" style="color:${a.live ? "var(--ok)" : "var(--warn)"}"></span>${t(a.live ? "Live" : "Test mode")} · ${t("Only the owner can switch modes or remove this account.")}</p>`}
        </section>
        <form class="card" id="settings-form">
          <h3>${t("Replies")}</h3>
          <label class="switch"><input type="checkbox" name="ai_fallback" ${S.ai && s.ai_fallback ? "checked" : ""} ${S.ai ? "" : "disabled"}><span class="track"></span>
            <span class="txt">${t("Use AI when no automation matches")}${S.ai ? "" : `<span class="small muted">${t("Add ANTHROPIC_API_KEY on the server to enable")}</span>`}</span></label>
          <label class="field"><span>${t("Brand voice")}</span><textarea class="input" name="brand_voice" rows="3" maxlength="1000" dir="auto">${esc(s.brand_voice)}</textarea><span class="hint">${t("How the AI should sound.")}</span></label>
          <label class="field"><span>${t("Ignore comments containing")}</span><input class="input" name="ignore_keywords" dir="auto" value="${esc(s.ignore_keywords.join(FA_MODE ? "، " : ", "))}"><span class="hint">${t("Comma separated. These never get a reply.")}</span></label>
          <h3 style="margin-top:8px">${t("Followers-only DMs: defaults")}</h3>
          <p class="small muted" style="margin-top:-6px">${t("Each automation can override these.")}</p>
          <label class="field"><span>${t("1 · First message")}</span><textarea class="input" name="gate_message" rows="2" maxlength="640" dir="auto">${esc(s.gate_message)}</textarea></label>
          <label class="field"><span>${t("Button text")}</span><span class="input-wrap"><input class="input" name="gate_button" maxlength="20" dir="auto" value="${esc(s.gate_button)}"><span class="counter" id="s-btn-count" dir="ltr"></span></span></label>
          <div id="s-gate-preview"></div>
          <label class="field"><span>${t("2 · They tap but don't follow yet")}</span><textarea class="input" name="not_following_message" rows="2" maxlength="640" dir="auto">${esc(s.not_following_message)}</textarea></label>
          <div id="s-nf-preview"></div>
          <label class="field"><span>${t("3 · If Instagram won't share the follow status")}</span><textarea class="input" name="check_failed_message" rows="2" maxlength="640" dir="auto">${esc(s.check_failed_message)}</textarea><span class="hint">${t("Rare. Asks them to type a message, which always lets the bot check.")}</span></label>
          <button class="btn btn-dark" type="submit" style="align-self:flex-start">${t("Save settings")}</button>
        </form>` : `<section class="card"><h3>${t("No account")}</h3><p class="muted">${t("Connect an Instagram account first.")}</p><button class="btn btn-dark" data-act="add-account" style="align-self:flex-start">${t("Connect account")}</button></section>`}
      </div>
      <div class="stack" style="gap:20px">
        <section class="card"><h3>${t("Appearance")}</h3><p class="small muted">${t("On this device.")}</p>
          <div class="field"><span>${t("Language")}</span>${langSwitch()}</div>
          <div class="field"><span>${t("Theme")}</span><div class="seg" role="group" aria-label="${t("Theme")}">${[["system", "System"], ["light", "Light"], ["dark", "Dark"]].map(([k, l]) =>
            `<button data-act="set-theme" data-theme="${k}" aria-pressed="${theme === k}">${ic(k === "dark" ? "moon" : k === "light" ? "sun" : "system", 16)} ${t(l)}</button>`).join("")}</div></div></section>
        <section class="card"><h3>${t("Install on your phone")}</h3>
          ${standalone ? `<p class="small muted">${t("You're using the installed app.")}</p>`
          : S.installEvt ? `<p class="small muted">${t("Add replyloop to your home screen. It opens full-screen like a normal app.")}</p><button class="btn btn-dark btn-sm" data-act="install" style="align-self:flex-start">${ic("phone", 16)} ${t("Install app")}</button>`
          : `<p class="small">${t(ios ? "In <b>Safari</b>, tap the <b>Share</b> button, then <b>Add to Home Screen</b>." : "In <b>Chrome</b>, open the <b>⋮</b> menu and tap <b>Add to Home screen</b> or <b>Install app</b>.")}</p>`}
        </section>
        ${securityCard(sec)}
        ${devicesCard(sec)}
        ${isOwner() ? `<section class="card"><h3>${t("People with access")}</h3>
          <p class="small muted">${t("Editors can change automations, settings and the inbox. View-only people can look but not change anything. Only you can connect or remove Instagram accounts and switch them between test and live.")}</p>
          <ul class="people">${users.map((u) => `<li>
            <span class="row" style="flex-wrap:nowrap;min-width:0;flex:1">${avatarHtml(u.email, 34)}<span style="min-width:0"><span class="item-text" dir="ltr" style="display:block">${esc(u.email)}</span>
              ${u.two_factor ? `<span class="small" style="color:var(--ok);font-weight:600">${ic("shield", 13, 2)} ${t("Two-step on")}</span>` : `<span class="small muted">${t("Two-step off")}</span>`}</span></span>
            ${u.is_owner ? `<span class="chip">${t("Owner")}</span>` : `
              <select class="input role-select" data-role-user="${u.id}" aria-label="${esc(t("Role of {e}", { e: u.email }))}">
                ${["editor", "viewer"].map((r) => `<option value="${r}" ${u.role === r ? "selected" : ""}>${t(ROLE_LABEL[r])}</option>`).join("")}</select>
              ${u.two_factor ? `<button class="icon-btn flat" data-act="reset-user-2fa" data-id="${u.id}" data-email="${esc(u.email)}" aria-label="${esc(t("Reset two-step login for {e}", { e: u.email }))}" title="${esc(t("Reset two-step login"))}">${ic("key", 17)}</button>` : ""}
              <button class="icon-btn flat" data-act="remove-user" data-id="${u.id}" aria-label="${esc(t("Remove {e}", { e: u.email }))}">${ic("trash", 17)}</button>`}</li>`).join("")}</ul>
          <button class="btn btn-sm" data-act="add-user" style="align-self:flex-start">${ic("plus", 16)} ${t("Add person")}</button></section>` : ""}
        <form class="card" id="pw-form"><h3>${t("Your password")}</h3><p class="small muted">${t("Signed in as {e}", { e: `<bdi dir="ltr">${esc(S.me.email)}</bdi>` })} · ${t(ROLE_LABEL[S.role] || "Editor")}</p>
          <label class="field"><span>${t("Current password")}</span><input class="input" type="password" name="current" autocomplete="current-password" dir="ltr"></label>
          <label class="field"><span>${t("New password")}</span><input class="input" type="password" name="new" autocomplete="new-password" minlength="10" dir="ltr"><span class="hint">${t("At least 10 characters. Other devices get signed out.")}</span></label>
          <button class="btn btn-sm" type="submit" style="align-self:flex-start">${t("Change password")}</button></form>
        <button class="btn btn-ghost" data-act="logout" style="align-self:flex-start">${ic("out", 18)} ${t("Sign out")}</button>
      </div>
    </div>`);
  const f = $("#settings-form");
  if (f) {
    const prev = () => {
      $("#s-btn-count").textContent = `${[...f.gate_button.value].length}/20`;
      $("#s-gate-preview").innerHTML = igBubble(f.gate_message.value, f.gate_button.value);
      $("#s-nf-preview").innerHTML = igBubble(f.not_following_message.value, f.gate_button.value);
    };
    f.addEventListener("input", prev); prev();
    if (!canEdit()) {
      f.querySelectorAll("input, textarea").forEach((el) => (el.disabled = true));
      $("button[type=submit]", f).replaceWith(Object.assign(document.createElement("p"), { className: "small muted", textContent: t("You have view-only access.") }));
    }
    f.onsubmit = async (e) => {
      e.preventDefault();
      S.settings = await api(A("/settings"), { method: "PUT", body: {
        ai_fallback: S.ai ? f.ai_fallback.checked : s.ai_fallback, brand_voice: f.brand_voice.value,
        ignore_keywords: splitList(f.ignore_keywords.value),
        gate_message: f.gate_message.value, gate_button: f.gate_button.value,
        not_following_message: f.not_following_message.value, check_failed_message: f.check_failed_message.value } });
      toast(t("Settings saved"));
    };
  }
  $("#pw-form").onsubmit = async (e) => {
    e.preventDefault();
    const p = e.target;
    await api("/password", { method: "POST", body: { current: p.current.value, new: p.new.value } });
    p.reset(); toast(t("Password changed"));
  };
}


// ------------------------------------------------------------------ security (two-step login, devices)
function securityCard(sec) {
  const warnOwner = isOwner() && !sec.two_factor;
  return `<section class="card" id="sec-card">
    <div class="card-head"><div class="row" style="flex-wrap:nowrap;gap:12px"><span class="sec-ic ${sec.two_factor ? "on" : ""}">${ic("shield", 22)}</span>
      <div><h3>${t("Two-step login")}</h3><p class="small muted">${sec.two_factor ? t("On. Signing in needs your password and a code from your phone.") : t("Off")}</p></div></div>
      ${sec.two_factor ? `<span class="chip ok">${t("On")}</span>` : ""}</div>
    ${sec.two_factor ? `
      <p class="small ${sec.backup_codes_left <= 2 ? "" : "muted"}" ${sec.backup_codes_left <= 2 ? 'style="color:var(--bad);font-weight:600"' : ""}>${t("{n} backup codes left.", { n: sec.backup_codes_left })}</p>
      <div class="row"><button class="btn btn-sm" data-act="2fa-backup">${ic("key", 16)} ${t("New backup codes")}</button><button class="btn btn-sm btn-ghost btn-danger" data-act="2fa-off">${t("Turn off")}</button></div>`
    : `<p class="small">${t("When you sign in, you'll also type a 6-digit code from an authenticator app on your phone. Even if someone learns your password, they can't get in without your phone.")}</p>
      ${warnOwner ? `<div class="note-box small">${t("Recommended for you: as the owner, your login protects every connected Instagram account.")}</div>` : ""}
      ${sec.can_enable ? `<button class="btn btn-dark btn-sm" data-act="2fa-setup" style="align-self:flex-start">${ic("shield", 16)} ${t("Turn on two-step login")}</button>`
        : `<div class="note-box small">${t("Set SECRET_KEY on the server before turning on two-step login.")}</div>`}`}
  </section>`;
}

function deviceLabel(s) {
  const name = [s.os, s.browser].filter(Boolean).join(" · ");
  return name || t("Unknown device");
}
function devicesCard(sec) {
  const list = sec.sessions || [];
  return `<section class="card" id="devices-card">
    <div><h3>${t("Signed-in devices")}</h3><p class="small muted">${t("Phones and browsers where you're signed in. Sign out any you don't recognise.")}</p></div>
    <ul class="devices">${list.map((s) => `<li>
      <span class="dev-ic">${ic(/iPhone|Android|iPad/.test(s.os) ? "phone" : "laptop", 20)}</span>
      <span style="flex:1;min-width:0"><b>${esc(deviceLabel(s))}</b>
        <span class="small muted" style="display:block">${s.current ? `<span style="color:var(--ok);font-weight:700">${t("This device")}</span>` : t("Active {t}", { t: ago(s.last_seen_at) })}${s.ip ? ` · <bdi dir="ltr">${esc(s.ip)}</bdi>` : ""}</span></span>
      ${s.current ? "" : `<button class="btn btn-sm btn-ghost" data-act="end-session" data-id="${esc(s.id)}">${t("Sign out")}</button>`}</li>`).join("")}</ul>
    ${list.length > 1 ? `<button class="btn btn-sm" data-act="end-other-sessions" style="align-self:flex-start">${ic("out", 16)} ${t("Sign out all other devices")}</button>` : ""}
  </section>`;
}

const codeField = (label, backupOk = false) => `<label class="field"><span>${label}</span>
  <input class="input code-input" id="tf-code" dir="ltr" autocomplete="one-time-code" ${backupOk ? 'maxlength="12" autocapitalize="off" spellcheck="false"' : 'inputmode="numeric" maxlength="6"'} placeholder="${backupOk ? "123456 / xxxx-xxxx" : "••••••"}"></label>`;

function showBackupCodes(codes, title, note = "") {
  const sheet = openSheet(title, `${note ? `<div class="note-box small ok-box">${ic("check", 16, 2.4)} ${esc(note)}</div>` : ""}
    <p>${t("Save these somewhere safe, like a password manager or a note. If you lose your phone, each code lets you sign in once.")}</p>
    <ol class="codes" dir="ltr">${codes.map((c) => `<li>${esc(c)}</li>`).join("")}</ol>
    <p class="small muted">${t("You won't see these again. New codes replace the old ones.")}</p>`,
    `<button class="btn grow" id="copy-codes">${ic("copy", 16)} ${t("Copy all")}</button><button class="btn btn-dark grow" data-act="close">${t("I saved them")}</button>`,
    { onClose: () => route() });
  $("#copy-codes", sheet).onclick = () => copyText(codes.join("\n"));
}

async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast(t("Copied")); }
  catch { toast(t("Couldn't copy. Select the text and copy it yourself."), true); }
}

function openAddAccount() {
  return openSheet(t("Connect an Instagram account"), `
    <ol class="stack small" style="padding-inline-start:18px;gap:6px;margin:0">
      <li>${t("Open your app on <b>developers.facebook.com</b> → Instagram → <b>API setup with Instagram login</b>.")}</li>
      <li>${t("Under <b>Generate access tokens</b>, add the account and tap <b>Generate token</b>.")}</li>
      <li>${t("Copy the token and paste it here.")}</li></ol>
    <label class="field"><span>${t("Access token")}</span><textarea class="input" id="token" rows="3" autocomplete="off" spellcheck="false" dir="ltr" placeholder="IGAA…"></textarea>
      <span class="hint">${t("Stored encrypted. Refreshed automatically before it expires.")}</span></label>
    <div class="row" style="gap:10px"><span style="flex:1;height:1px;background:var(--border)"></span><span class="small muted">${t("or")}</span><span style="flex:1;height:1px;background:var(--border)"></span></div>
    <button class="btn" data-act="add-demo">${ic("spark", 18)} ${t("Try a demo account")}</button>`,
    `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-dark grow" data-act="connect">${t("Connect")}</button>`);
}

// ------------------------------------------------------------------ actions
const ACT = {
  close: closeLayer,
  reload: () => location.reload(),
  "set-lang": (el) => { if (el.dataset.lang !== LANG) setLanguage(el.dataset.lang); },
  theme: (el) => { const dark = document.documentElement.dataset.theme === "dark"; themeTransition(dark ? "light" : "dark", el); },
  "set-theme": (el) => { $$("[data-act=set-theme]").forEach((b) => b.setAttribute("aria-pressed", b === el)); themeTransition(el.dataset.theme, el); },
  accounts: accountMenu,
  "switch-account": (el) => switchAccount(Number(el.dataset.id)),
  "add-account": openAddAccount,
  "add-demo": async () => {
    const acc = await api("/accounts", { method: "POST", body: { demo: true } });
    S.accounts.push(acc); closeLayer(); toast(t("Demo account added")); renderAccountButton(); switchAccount(acc.id);
  },
  connect: async (el) => {
    const token = $("#token").value.trim();
    if (!token) return toast(t("Paste the access token first."), true);
    el.disabled = true; el.textContent = t("Connecting…");
    try {
      const acc = await api("/accounts", { method: "POST", body: { token } });
      S.accounts = await api("/accounts");
      closeLayer(); toast(acc.warning || t("Connected @{u}", { u: acc.username }), !!acc.warning); switchAccount(acc.id);
    } catch { el.disabled = false; el.textContent = t("Connect"); }
  },
  logout: async () => { await api("/logout", { method: "POST" }).catch(() => {}); closeLayer(); S.me = null; boot(); },
  "go-live": async () => {
    if (!(await confirmSheet(t("Go live?"), t("The bot will start replying and sending DMs on Instagram for this account."), t("Go live")))) return;
    await setLive(true);
  },
  "set-live": async (el) => {
    const live = el.dataset.live === "1";
    if (live && !(await confirmSheet(t("Go live?"), t("The bot will start replying and sending DMs on Instagram for this account."), t("Go live")))) return;
    await setLive(live);
  },
  "remove-account": async () => {
    const a = currentAccount();
    if (!(await confirmSheet(t("Remove @{u}?", { u: a.username }), t("Its automations, settings and inbox history are deleted. The Instagram account itself isn't affected."), t("Remove"), true))) return;
    await api(`/accounts/${a.id}`, { method: "DELETE" });
    S.accounts = S.accounts.filter((x) => x.id !== a.id);
    toast(t("Account removed")); switchAccount((S.accounts[0] || {}).id ?? null);
  },
  "post-filter": (el) => { postFilter = el.dataset.f; $$("[data-act=post-filter]").forEach((b) => b.setAttribute("aria-pressed", b === el)); morphList($("#posts-grid"), drawPosts); },
  "reload-posts": async () => { await renderPosts($("#view"), true); toast(t("Posts updated")); },
  "inbox-filter": (el) => { inboxFilter = el.dataset.f; route(); },
  "new-rule": () => openRuleEditor($("#rules-box"), null),
  "rule-edit": (el) => { const box = $("#rules-box"); openRuleEditor(box, box._rules.find((r) => r.id === Number(el.closest(".rule").dataset.id))); },
  "rule-save": () => $(".sheet")._save(),
  "rule-delete": () => $(".sheet")._delete(),
  "rule-move": async (el) => {
    const box = $("#rules-box"), rules = [...box._rules], i = rules.findIndex((r) => r.id === Number(el.closest(".rule").dataset.id)), j = i + Number(el.dataset.dir);
    if (j < 0 || j >= rules.length) return;
    [rules[i], rules[j]] = [rules[j], rules[i]];
    morphList(box, () => {
      drawRules(box, rules);
      $(`.rule[data-id="${rules[j].id}"] [data-dir="${el.dataset.dir}"]`, box)?.focus();
    });
    await api(A("/rules/reorder"), { method: "POST", body: { ids: rules.map((r) => r.id) } });
  },
  "try-preview": async (el) => {
    const text = $("#try-text").value.trim();
    if (!text) return toast(t("Type a comment first."), true);
    $("#try-result").innerHTML = `<p class="small muted">${t("Checking…")}</p>`;
    const d = await api(A("/test"), { method: "POST", body: { text, media_id: el.dataset.media || null } });
    $("#try-result").innerHTML = decisionHtml(d);
  },
  "try-simulate": async (el) => {
    const text = $("#try-text").value.trim();
    if (!text) return toast(t("Type a comment first."), true);
    const c = await api(A("/simulate"), { method: "POST", body: { text, username: "test_user", media_id: el.dataset.media || null } });
    toast(t("Simulated. Opening the inbox…"));
    location.hash = `#/inbox/${encodeURIComponent(c.comment_id)}`;
  },
  "sim-tap": async (el) => {
    await api(A("/simulate-tap"), { method: "POST", body: { comment_id: el.dataset.cid, follows: el.dataset.follows === "1" } });
    route();
  },
  "code-mode": (el) => renderCodeStep(!!el.dataset.backup),
  "cancel-code": async () => { await fetch("/api/login/cancel", { method: "POST", credentials: "same-origin", headers: HEADERS }).catch(() => {}); boot(); },
  "2fa-setup": async () => {
    const d = await api("/2fa/setup", { method: "POST" });
    openSheet(t("Turn on two-step login"), `
      <ol class="steps">
        <li>${t("Install an authenticator app on your phone, like Google Authenticator or Microsoft Authenticator.")}</li>
        <li>${t("Scan this code with the app. On this phone? Tap <b>Open in authenticator app</b> or copy the key.")}</li>
        <li>${t("Type the 6-digit code the app shows.")}</li></ol>
      <div class="qr-wrap"><div class="qr" role="img" aria-label="${esc(t("QR code for your authenticator app"))}">${d.qr}</div>
        <div class="stack" style="gap:10px;min-width:0">
          <a class="btn btn-sm" href="${esc(d.uri)}">${ic("ext", 16)} ${t("Open in authenticator app")}</a>
          <div class="field"><span>${t("Setup key")}</span><div class="keybox" dir="ltr">${esc(d.secret)}</div>
            <button class="btn btn-sm btn-ghost" type="button" id="copy-key" style="align-self:flex-start">${ic("copy", 16)} ${t("Copy key")}</button></div></div></div>
      ${codeField(t("6-digit code"))}`,
      `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-dark grow" data-act="2fa-enable">${t("Turn on")}</button>`);
    $("#copy-key").onclick = () => copyText(d.secret.replace(/\s/g, ""));
    $("#tf-code").addEventListener("keydown", (e) => { if (e.key === "Enter") ACT["2fa-enable"]().catch(() => {}); });
  },
  "2fa-enable": async () => {
    const d = await api("/2fa/enable", { method: "POST", body: { code: $("#tf-code").value } });
    S.me.two_factor = true;
    closeLayer();
    showBackupCodes(d.backup_codes, t("Two-step login is on"), t("Other devices were signed out, so they'll need the code next time."));
  },
  "2fa-off": () => {
    openSheet(t("Turn off two-step login?"), `<p>${t("Signing in will only need your password again.")}</p>${codeField(t("Code from your app or a backup code"), true)}`,
      `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-accent grow" data-act="2fa-off-confirm">${t("Turn off")}</button>`);
  },
  "2fa-off-confirm": async () => {
    await api("/2fa/disable", { method: "POST", body: { code: $("#tf-code").value } });
    S.me.two_factor = false; closeLayer(); toast(t("Two-step login is off")); route();
  },
  "2fa-backup": () => {
    openSheet(t("New backup codes"), `<p>${t("Your old backup codes will stop working.")}</p>${codeField(t("Code from your app or a backup code"), true)}`,
      `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-dark grow" data-act="2fa-backup-confirm">${t("Make new codes")}</button>`);
  },
  "2fa-backup-confirm": async () => {
    const d = await api("/2fa/backup-codes", { method: "POST", body: { code: $("#tf-code").value } });
    closeLayer(); showBackupCodes(d.backup_codes, t("Your new backup codes"));
  },
  "end-session": async (el) => {
    await api(`/sessions/${encodeURIComponent(el.dataset.id)}`, { method: "DELETE" });
    const li = el.closest("li");
    if (li && !REDUCED.matches) await li.animate([{ opacity: 1 }, { opacity: 0, transform: "translateX(12px)" }], { duration: 200, fill: "forwards" }).finished;
    toast(t("Signed out of that device")); route();
  },
  "end-other-sessions": async () => {
    if (!(await confirmSheet(t("Sign out all other devices?"), t("Everywhere except this device will need to sign in again."), t("Sign out"), true))) return;
    await api("/sessions/others", { method: "POST" }); toast(t("Other devices signed out")); route();
  },
  "reset-user-2fa": async (el) => {
    if (!(await confirmSheet(t("Reset two-step login?"), t("Use this if {e} lost their phone. They'll sign in with just their password and can turn it on again.", { e: el.dataset.email }), t("Reset"), true))) return;
    await api(`/users/${el.dataset.id}`, { method: "PATCH", body: { reset_2fa: true } }); toast(t("Two-step login reset")); route();
  },
  "add-user": () => {
    openSheet(t("Add a person"), `<p class="small muted">${t(S.google ? "They'll sign in on their own phone with Google (same Gmail address) or with this email and password. Share a password privately; they can change it in Settings." : "They'll sign in with this email and password on their own phone. Share the password privately; they can change it in Settings.")}</p>
      <label class="field"><span>${t("Email")}</span><input class="input" id="nu-email" type="email" autocomplete="off" dir="ltr"></label>
      <div class="field"><span>${t("Role")}</span><div class="seg" role="group" aria-label="${t("Role")}" id="nu-role">
        <button type="button" data-role="editor" aria-pressed="true">${t("Editor")}</button><button type="button" data-role="viewer" aria-pressed="false">${t("View only")}</button></div>
        <span class="hint" id="nu-role-hint">${t("Can change automations, settings and the inbox.")}</span></div>
      <label class="field"><span>${t("Password")}</span><input class="input" id="nu-pw" type="text" autocomplete="off" minlength="10" dir="ltr"><span class="hint">${t(S.google ? "At least 10 characters. Leave it empty if they'll only use Google with this Gmail." : "At least 10 characters.")}</span></label>`,
      `<button class="btn grow" data-act="close">${t("Cancel")}</button><button class="btn btn-dark grow" data-act="save-user">${t("Add")}</button>`);
    $("#nu-role").onclick = (e) => {
      const b = e.target.closest("button[data-role]"); if (!b) return;
      $$("#nu-role button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      $("#nu-role-hint").textContent = t(b.dataset.role === "viewer" ? "Can see everything but can't change anything." : "Can change automations, settings and the inbox.");
    };
  },
  "save-user": async () => {
    const role = $('#nu-role [aria-pressed="true"]')?.dataset.role || "editor";
    await api("/users", { method: "POST", body: { email: $("#nu-email").value.trim(), password: $("#nu-pw").value, role } });
    closeLayer(); toast(t("Person added")); route();
  },
  "remove-user": async (el) => {
    if (!(await confirmSheet(t("Remove access?"), t("They'll be signed out everywhere."), t("Remove"), true))) return;
    await api(`/users/${el.dataset.id}`, { method: "DELETE" }); toast(t("Access removed")); route();
  },
  "save-context": async () => {
    const mid = decodeURIComponent(location.hash.split("/")[2] || "");
    const p = S.posts.find((x) => x.id === mid);
    const saved = await api(A(`/posts/${encodeURIComponent(mid)}`), { method: "PUT", body: { context: $("#post-context").value, ai_enabled: p.ai_enabled !== false, autoreply_enabled: p.autoreply_enabled !== false } });
    Object.assign(p, saved); toast(t("Saved"));
  },
  "ins-days": (el) => { insDays = Number(el.dataset.d); route(); },
  "aud-dim": (el) => { audDim = el.dataset.k; $$("[data-act=aud-dim]").forEach((b) => b.setAttribute("aria-pressed", b === el)); $("#aud").innerHTML = audienceBars($("#ins-body")._aud || {}); },
  "post-sort": (el) => { postSort = el.dataset.k; $$("[data-act=post-sort]").forEach((b) => b.setAttribute("aria-pressed", b === el)); morphList($("#ranked"), drawRanked); },
  "ins-refresh": async (el) => {
    const body = $("#ins-body"), what = el.dataset.what;
    el.disabled = true;
    try {
      if (what === "account") await insAccount(body, true);
      else if (what === "posts") await insPosts(body, true);
      else await insStories(body, true);
      toast(t("Updated from Instagram"));
    } finally { el.disabled = false; }
  },
  install: async () => { if (!S.installEvt) return; S.installEvt.prompt(); await S.installEvt.userChoice; S.installEvt = null; route(); },
  "toggle-pw": (el) => { const i = el.parentElement.querySelector("input"); i.type = i.type === "password" ? "text" : "password"; el.setAttribute("aria-label", t(i.type === "password" ? "Show password" : "Hide password")); },
};
async function setLive(live) {
  const acc = await api(`/accounts/${S.aid}`, { method: "PATCH", body: { live } });
  const i = S.accounts.findIndex((a) => a.id === S.aid);
  S.accounts[i] = acc;
  toast(t(live ? "Live. Replies and DMs are sent now." : "Back in test mode."));
  route();
}

document.addEventListener("click", async (e) => {
  const el = e.target.closest("[data-act]");
  if (!el || !ACT[el.dataset.act]) return;
  e.preventDefault();
  if (el.dataset.busy) return;
  el.dataset.busy = "1";
  try { await ACT[el.dataset.act](el, e); } catch (err) { if (!["offline", "signed out"].includes(err.message)) console.warn(err); }
  finally { delete el.dataset.busy; }
});

document.addEventListener("change", async (e) => {
  const sel = e.target.closest("[data-role-user]");
  if (sel) {
    try { await api(`/users/${sel.dataset.roleUser}`, { method: "PATCH", body: { role: sel.value } }); toast(t("Role updated")); }
    catch { route(); }
    return;
  }
  const box = e.target.closest("[data-post-toggle]");
  if (!box) return;
  const mid = decodeURIComponent(location.hash.split("/")[2] || "");
  const p = S.posts.find((x) => x.id === mid);
  const key = box.dataset.postToggle;
  const body = { context: p.context || "", ai_enabled: p.ai_enabled !== false, autoreply_enabled: p.autoreply_enabled !== false, [key]: box.checked };
  try {
    Object.assign(p, await api(A(`/posts/${encodeURIComponent(mid)}`), { method: "PUT", body }));
    toast(t(key === "autoreply_enabled" ? (box.checked ? "Auto-reply on" : "Auto-reply paused on this post") : (box.checked ? "AI fallback on" : "AI fallback off")));
  } catch { box.checked = !box.checked; }
});

// ------------------------------------------------------------------ app install
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); S.installEvt = e; });
if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));

boot();
