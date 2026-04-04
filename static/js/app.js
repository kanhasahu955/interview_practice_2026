/* Theme toggle + JS hook for styling */
document.documentElement.classList.add("js-ready");

(function () {
  var root = document.documentElement;
  var key = "mo_theme";
  try {
    var stored = localStorage.getItem(key);
    if (stored === "light" || stored === "dark") {
      root.setAttribute("data-theme", stored);
    }
  } catch (_) {}

  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  btn.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem(key, next);
    } catch (_) {}
  });
})();
