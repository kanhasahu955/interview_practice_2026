/**
 * Live cookie consent: banner, POST /api/v1/consent/cookies, localStorage mirror,
 * CustomEvent + storage for same-tab and cross-tab updates.
 */
(function () {
  "use strict";

  var STORAGE_KEY = "mo_cookie_consent_v1";
  var EVENT_NAME = "mo:cookie-consent";

  function apiBase() {
    var el = document.documentElement;
    var p = (el && el.dataset && el.dataset.apiPrefix) || "/api/v1";
    return String(p).replace(/\/$/, "");
  }

  function consentUrl() {
    return apiBase() + "/consent/cookies";
  }

  function parseStored(raw) {
    if (!raw) return null;
    try {
      var o = JSON.parse(raw);
      if (o && typeof o === "object" && o.decided_at) return o;
    } catch (_) {}
    return null;
  }

  function readLocal() {
    try {
      return parseStored(localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return null;
    }
  }

  function writeLocal(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (_) {}
  }

  function clearLocal() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (_) {}
  }

  function broadcast(state) {
    try {
      window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: state }));
    } catch (_) {}
  }

  function getState() {
    return readLocal();
  }

  var root = null;
  var panel = null;
  var customBlock = null;
  var chkFunctional = null;
  var chkAnalytics = null;
  var openBtn = null;

  function setVisible(show) {
    if (!root) return;
    root.hidden = !show;
    if (show) {
      root.classList.add("cookie-consent-root--open");
      root.setAttribute("aria-hidden", "false");
    } else {
      root.classList.remove("cookie-consent-root--open");
      root.setAttribute("aria-hidden", "true");
    }
  }

  function setCustomize(open) {
    if (!customBlock) return;
    customBlock.hidden = !open;
    customBlock.classList.toggle("cookie-consent-custom--open", open);
  }

  function applyCheckboxes(state) {
    if (chkFunctional) chkFunctional.checked = !!(state && state.functional);
    if (chkAnalytics) chkAnalytics.checked = !!(state && state.analytics);
  }

  function hideBanner() {
    setVisible(false);
    setCustomize(false);
  }

  function showBanner(opts) {
    opts = opts || {};
    setVisible(true);
    var s = opts.prefill || readLocal();
    if (s) applyCheckboxes(s);
    else {
      if (chkFunctional) chkFunctional.checked = false;
      if (chkAnalytics) chkAnalytics.checked = false;
    }
    if (opts.expandCustomize) setCustomize(true);
    else if (!opts.prefill) setCustomize(false);
  }

  function postConsent(body) {
    return fetch(consentUrl(), {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    }).then(function (res) {
      if (!res.ok) throw new Error("consent_save_failed");
      return res.json();
    });
  }

  function saveAndClose(state) {
    writeLocal(state);
    broadcast(state);
    hideBanner();
  }

  function onAcceptAll() {
    postConsent({ action: "accept_all" }).then(saveAndClose).catch(function () {
      var s = {
        essential: true,
        analytics: true,
        functional: true,
        version: 1,
        decided_at: new Date().toISOString(),
      };
      saveAndClose(s);
    });
  }

  function onRejectOptional() {
    postConsent({ action: "reject_optional" }).then(saveAndClose).catch(function () {
      var s = {
        essential: true,
        analytics: false,
        functional: false,
        version: 1,
        decided_at: new Date().toISOString(),
      };
      saveAndClose(s);
    });
  }

  function onSaveCustom() {
    var functional = chkFunctional ? chkFunctional.checked : false;
    var analytics = chkAnalytics ? chkAnalytics.checked : false;
    postConsent({ action: "save", functional: functional, analytics: analytics })
      .then(saveAndClose)
      .catch(function () {
        var s = {
          essential: true,
          analytics: analytics,
          functional: functional,
          version: 1,
          decided_at: new Date().toISOString(),
        };
        saveAndClose(s);
      });
  }

  function syncFromServer() {
    return fetch(consentUrl(), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) return null;
        return res.json();
      })
      .then(function (data) {
        if (data && data.decided_at) {
          writeLocal(data);
          broadcast(data);
          return data;
        }
        return null;
      })
      .catch(function () {
        return null;
      });
  }

  function withdraw() {
    return fetch(consentUrl(), { method: "DELETE", credentials: "same-origin" })
      .then(function () {
        clearLocal();
        broadcast(null);
        applyCheckboxes(null);
        showBanner({ expandCustomize: false });
      })
      .catch(function () {
        clearLocal();
        broadcast(null);
        showBanner({ expandCustomize: false });
      });
  }

  function buildUi() {
    root = document.getElementById("cookie-consent-root");
    if (!root) return;

    root.innerHTML =
      '<div class="cookie-consent-backdrop" data-dismiss="1" aria-hidden="true"></div>' +
      '<div class="cookie-consent-panel" role="dialog" aria-modal="true" aria-labelledby="cookie-consent-title">' +
      '  <div class="cookie-consent-card">' +
      '    <h2 id="cookie-consent-title" class="cookie-consent-title">Cookies &amp; privacy</h2>' +
      '    <p class="cookie-consent-lead">We use essential cookies to run this site. You can accept optional cookies for analytics and preferences, or reject them. You can change this anytime from <strong>Cookie settings</strong> in the header.</p>' +
      '    <div class="cookie-consent-actions">' +
      '      <button type="button" class="btn btn-ghost" data-cc="reject">Reject optional</button>' +
      '      <button type="button" class="btn btn-ghost" data-cc="customize">Customize</button>' +
      '      <button type="button" class="btn btn-primary" data-cc="accept">Accept all</button>' +
      "    </div>" +
      '    <div class="cookie-consent-custom" hidden>' +
      "      <p class=\"cookie-consent-hint\">Optional categories:</p>" +
      '      <label class="cookie-consent-toggle"><input type="checkbox" data-cc-cat="functional" /> <span>Functional</span> <small>Remember UI choices</small></label>' +
      '      <label class="cookie-consent-toggle"><input type="checkbox" data-cc-cat="analytics" /> <span>Analytics</span> <small>Measure usage (example)</small></label>' +
      '      <div class="cookie-consent-actions cookie-consent-actions--sub">' +
      '        <button type="button" class="btn btn-secondary" data-cc="save">Save choices</button>' +
      '        <button type="button" class="btn btn-text" data-cc="withdraw">Clear &amp; show banner again</button>' +
      "      </div>" +
      "    </div>" +
      "  </div>" +
      "</div>";

    panel = root.querySelector(".cookie-consent-panel");
    customBlock = root.querySelector(".cookie-consent-custom");
    chkFunctional = root.querySelector('input[data-cc-cat="functional"]');
    chkAnalytics = root.querySelector('input[data-cc-cat="analytics"]');

    root.addEventListener("click", function (e) {
      var t = e.target;
      if (t && t.getAttribute && t.getAttribute("data-dismiss") === "1") hideBanner();
    });

    root.addEventListener("click", function (e) {
      var btn = e.target.closest && e.target.closest("[data-cc]");
      if (!btn) return;
      var a = btn.getAttribute("data-cc");
      if (a === "accept") onAcceptAll();
      else if (a === "reject") onRejectOptional();
      else if (a === "customize") setCustomize(true);
      else if (a === "save") onSaveCustom();
      else if (a === "withdraw") withdraw();
    });

    openBtn = document.getElementById("cookie-settings-open");
    if (openBtn) {
      openBtn.addEventListener("click", function () {
        showBanner({ prefill: readLocal(), expandCustomize: !!readLocal() });
      });
    }
  }

  function init() {
    buildUi();
    if (!root) return;

    var local = readLocal();
    if (local) {
      hideBanner();
      return;
    }

    syncFromServer().then(function (remote) {
      if (remote) {
        hideBanner();
        return;
      }
      showBanner();
    });
  }

  window.addEventListener("storage", function (e) {
    if (e.key !== STORAGE_KEY) return;
    var next = parseStored(e.newValue);
    broadcast(next);
    if (next) hideBanner();
    else showBanner();
  });

  window.MO_COOKIE_CONSENT = {
    getState: getState,
    /** Same event name listeners can use: `window.addEventListener('mo:cookie-consent', …)` */
    eventName: EVENT_NAME,
    openPreferences: function () {
      showBanner({ prefill: readLocal(), expandCustomize: true });
    },
    hasAnalytics: function () {
      var s = readLocal();
      return !!(s && s.analytics);
    },
    hasFunctional: function () {
      var s = readLocal();
      return !!(s && s.functional);
    },
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
