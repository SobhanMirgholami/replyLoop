// Applies the saved theme before the page paints (no flash of the wrong theme).
(function () {
  var pref = "system";
  try { pref = localStorage.getItem("rl_theme") || "system"; } catch (e) {}
  var dark = pref === "dark" || (pref === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  var lang = "fa";
  try { lang = localStorage.getItem("rl_lang") || "fa"; } catch (e) {}
  lang = lang.indexOf("en") === 0 ? "en" : "fa";
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "fa" ? "rtl" : "ltr";
})();
