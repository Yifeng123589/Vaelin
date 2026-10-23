"use strict";
/**
 * Desktop Hermes 沙箱适配 · H-SBX-A · DEMO
 * 沙箱真启用 · ≠ 生产 · 零改 %LocalAppData%\hermes
 * 签 ≠ 启用 · demo ≠ production · install ≠ enable · 8766 ≠ 生产 Hermes · PUB ≠ 生产 enable
 * 仅读本地 /sandbox-hermes-status.json；不接生产 IPC；不写生产目录。
 */
(function () {
  var GATE_TEXT =
    "签 ≠ 启用 · demo ≠ production · install ≠ enable · 8766 ≠ 生产 Hermes · 沙箱真启用 · ≠ 生产";

  function $(id) {
    return document.getElementById(id);
  }

  function reinforce() {
    var gate = $("desktop-s3-gate");
    if (gate) {
      gate.setAttribute("data-nonprod", "1");
      gate.setAttribute("data-hermes-sandbox", "1");
      var t = gate.querySelector(".np-text");
      if (t) t.textContent = GATE_TEXT;
      var sub = gate.querySelector(".sub");
      if (sub) {
        sub.textContent =
          "沙箱 HERMES_HOME＝_hermes_sandbox_stub · 零改 LocalAppData\\hermes · 8766＝stage ≠ 生产 Hermes";
      }
    }
    var bannerSub = document.querySelector("#np-banner .sub");
    if (bannerSub) {
      bannerSub.textContent =
        "沙箱真启用 · ≠ 生产 Hermes · 签 ≠ 启用 · 8766 ≠ 生产 Hermes · fixture · H-SBX-A";
    }
    var foot = document.querySelector("footer.app-foot");
    if (foot) {
      foot.textContent =
        "demos/desktop · Desktop-S3 · 沙箱Hermes真启用 · Electron＠8766 · 8766 ≠ 生产 Hermes · ≠ LocalAppData\\hermes · 签 ≠ 启用 · PUB≠生产 enable · 未宣称生产启用";
    }
    var chip = document.querySelector(".chip.ok");
    if (chip && /零\s*Hermes|零接\s*Hermes/.test(chip.textContent || "")) {
      chip.textContent = "沙箱Hermes · ≠生产";
    }
  }

  function applyStatus(st) {
    window.__desktopHermesSandbox = st || null;
    var el = $("desktop-hermes-sbx-status");
    if (!el) {
      var gate = $("desktop-s3-gate");
      if (gate) {
        el = document.createElement("span");
        el.id = "desktop-hermes-sbx-status";
        el.className = "sub";
        gate.appendChild(el);
      }
    }
    if (el && st) {
      el.textContent =
        "H-SBX-A · enabled=" +
        !!st.enabled +
        " · productionTouched=" +
        !!st.productionTouched +
        " · home=sandbox";
    }
    reinforce();
  }

  function boot() {
    reinforce();
    setTimeout(reinforce, 0);
    setTimeout(reinforce, 200);
    fetch("/sandbox-hermes-status.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("status " + r.status);
        return r.json();
      })
      .then(applyStatus)
      .catch(function () {
        applyStatus({
          ok: false,
          enabled: false,
          mode: "sandbox-probe-miss",
          productionTouched: false,
          message: "status.json 未达 · 仍零改生产 hermes",
        });
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
