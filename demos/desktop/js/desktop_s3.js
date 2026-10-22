"use strict";
/**
 * Desktop-S3 stage-only helpers · DEMO · 非生产 · 零 Hermes
 * 签 ≠ 启用 · demo ≠ production · install ≠ enable · 8766 ≠ Hermes desktop
 * 不接生产命令／Hermes IPC；仅本机 UX。
 */
(function () {
  function $(id) {
    return document.getElementById(id);
  }

  function ensureStyles() {
    if (document.getElementById("desktop-s3-style")) return;
    var s = document.createElement("style");
    s.id = "desktop-s3-style";
    s.textContent =
      ".desktop-s3-gate{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;" +
      "padding:.35rem .75rem;background:#2a2418;border-bottom:1px solid #6b5a2a;color:#f0e6c8;font-size:.82rem}" +
      ".desktop-s3-gate .sub{opacity:.85;font-size:.78rem}" +
      ".desktop-s3-help{position:fixed;inset:12% 18%;z-index:9999;background:#1c1b19;color:#f0e6c8;" +
      "border:1px solid #6b5a2a;border-radius:8px;padding:1.25rem 1.5rem;box-shadow:0 12px 40px rgba(0,0,0,.55)}" +
      ".desktop-s3-help[hidden]{display:none!important}" +
      ".desktop-s3-help h2{margin:0 0 .5rem;font-size:1.1rem}" +
      ".desktop-s3-help .help-keymap{margin:.75rem 0;padding-left:1.1rem;line-height:1.7}" +
      ".desktop-s3-help kbd{background:#333;border:1px solid #666;border-radius:3px;padding:0 .35rem;font-size:.85em}" +
      ".desktop-s3-help #desktop-s3-help-ok{margin-top:.75rem;padding:.35rem .9rem;cursor:pointer}";
    document.head.appendChild(s);
  }

  function setOpen(open) {
    var panel = $("desktop-s3-help");
    if (!panel) return;
    if (open) panel.removeAttribute("hidden");
    else panel.setAttribute("hidden", "");
  }

  function toggle() {
    var panel = $("desktop-s3-help");
    if (!panel) return;
    setOpen(panel.hasAttribute("hidden"));
  }

  window.__desktopS3ToggleHelp = toggle;

  function onKey(e) {
    if (!e) return;
    var t = e.target;
    var tag = t && t.tagName ? t.tagName.toLowerCase() : "";
    if (tag === "input" || tag === "textarea" || (t && t.isContentEditable)) return;
    if (e.key === "F1") {
      e.preventDefault();
      toggle();
      return;
    }
    if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.altKey) {
      // 不抢导览已有 ?；若导览帮助未开则开桌面帮助
      var tourHelp = $("tour-help-panel");
      if (tourHelp && !tourHelp.hasAttribute("hidden")) return;
      e.preventDefault();
      toggle();
    }
  }

  function reinforceHardGate() {
    var gate = $("desktop-s3-gate");
    if (gate) {
      gate.setAttribute("data-nonprod", "1");
      var t = gate.querySelector(".np-text");
      if (t) {
        t.textContent =
          "签 ≠ 启用 · demo ≠ production · install ≠ enable · 8766 ≠ Hermes desktop · 零 Hermes";
      }
    }
    var sub = document.querySelector("#np-banner .sub");
    if (sub && sub.textContent.indexOf("8766") < 0) {
      sub.textContent =
        "零接 Hermes · 签 ≠ 启用 · 8766 ≠ Hermes desktop · 假数据 fixture · S9→Desktop";
    }
    var foot = document.querySelector("footer.app-foot");
    if (foot && foot.textContent.indexOf("8766 ≠ Hermes") < 0) {
      foot.textContent =
        "staging · _ui_desktop_stage · Desktop-S3 · Electron＠8766 · 8766 ≠ Hermes desktop · 零接 Hermes · 签 ≠ 启用 · 默不 push";
    }
  }

  function boot() {
    ensureStyles();
    reinforceHardGate();
    setTimeout(reinforceHardGate, 0);
    setTimeout(reinforceHardGate, 200);
    var ok = $("desktop-s3-help-ok");
    if (ok) ok.addEventListener("click", function () { setOpen(false); });
    document.addEventListener("keydown", onKey);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
