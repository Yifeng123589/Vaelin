"use strict";
/**
 * Desktop 节点门可视化旁路屏 · UI-only · 假数据
 * 读 data/nodegate_fixture.json（自 _nodegate_sandbox out／fixtures 裁剪）
 * 禁 Hermes IPC／真会话／写回沙箱旗 · DEMO≠产 · 签≠启用 · 零会话 · 零碰生产 Hermes
 */
(function () {
  function $(sel, el) { return (el || document).querySelector(sel); }
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function badge(label, val, ok) {
    var cls = ok === true ? "ng-badge ok" : ok === false ? "ng-badge bad" : "ng-badge";
    return '<span class="' + cls + '"><b>' + esc(label) + "</b> " + esc(val) + "</span>";
  }
  function render(data) {
    var root = $("#nodegate-viz-root");
    if (!root) return;
    if (!data) {
      root.innerHTML = '<p class="load-fail">节点门假数据未加载（旁路 fixture）</p>';
      return;
    }
    var ht = data.hermes_touch === false;
    var top =
      '<div class="ng-top" role="status">' +
      badge("stage", data.stage, true) +
      badge("live_wire", String(data.live_wire), !!data.live_wire) +
      badge("hermes_touch", String(data.hermes_touch), ht) +
      "</div>";
    var sum =
      '<div class="ng-summary">' +
      '<div class="ng-sum-item"><span class="k">PASS</span><span class="v">' +
      esc(data.pass ? "是" : "否") +
      "</span></div>" +
      '<div class="ng-sum-item"><span class="k">ok／total</span><span class="v">' +
      esc(data.ok) +
      "/" +
      esc(data.total) +
      "</span></div>" +
      '<div class="ng-sum-item"><span class="k">bounce_n</span><span class="v">' +
      esc(data.bounce_n) +
      "</span></div>" +
      "</div>";
    var m = data.metrics || {};
    var metrics =
      '<div class="ng-metrics" aria-label="指标卡">' +
      [
        ["mixed_hunk_rate", m.mixed_hunk_rate],
        ["mixed_hunk_rate_ref_cap", m.mixed_hunk_rate_ref_cap],
        ["mainline_gate_red_rate", m.mainline_gate_red_rate],
        ["bounce_rounds_avg", m.bounce_rounds_avg],
        ["bounce_n_cap", m.bounce_n_cap],
      ]
        .map(function (pair) {
          return (
            '<div class="ng-metric"><div class="k">' +
            esc(pair[0]) +
            '</div><div class="v">' +
            esc(pair[1]) +
            "</div></div>"
          );
        })
        .join("") +
      "</div>";
    var logs = data.matrix_log_sample || [];
    var logHtml =
      '<div class="ng-block"><h3>矩阵日志样例 <span class="muted">count=' +
      esc(data.matrix_log_count) +
      '</span></h3><ul class="ng-log">' +
      logs
        .map(function (x) {
          return (
            "<li><code>" +
            esc(x.case) +
            "</code> · " +
            esc(x.line) +
            "</li>"
          );
        })
        .join("") +
      "</ul></div>";
    var rows = data.results || [];
    var table =
      '<div class="ng-block"><h3>用例表（假数据 · 只读）</h3>' +
      '<div class="ng-table-wrap"><table class="ng-table"><thead><tr>' +
      "<th>id</th><th>route</th><th>expected</th><th>ok</th><th>bounce</th><th>gate</th><th>notes</th>" +
      "</tr></thead><tbody>" +
      rows
        .map(function (r) {
          return (
            '<tr class="' +
            (r.ok ? "ok" : "bad") +
            '">' +
            "<td><code>" +
            esc(r.id) +
            "</code></td>" +
            "<td>" +
            esc(r.route) +
            "</td>" +
            "<td>" +
            esc(r.expected_route) +
            "</td>" +
            "<td>" +
            (r.ok ? "✓" : "✗") +
            "</td>" +
            "<td>" +
            esc(r.bounce_rounds) +
            "</td>" +
            "<td>" +
            esc(r.snapshot_gate == null ? "—" : r.snapshot_gate) +
            "</td>" +
            "<td>" +
            esc(r.notes || "") +
            "</td>" +
            "</tr>"
          );
        })
        .join("") +
      "</tbody></table></div></div>";
    var obs = data.observe_window_footnote || {};
    var foot =
      '<p class="ng-footnote" role="note">②观察窗仍 <code>live_wire=' +
      esc(obs.live_wire) +
      "</code>／<code>hermes_touch=" +
      esc(obs.hermes_touch) +
      "</code> · UI≠接线 · " +
      esc(obs.note || "") +
      "</p>";
    var gates = (data.hard_gate_copy || [])
      .map(function (t) {
        return '<span class="ng-chip">' + esc(t) + "</span>";
      })
      .join("");
    var hard = '<div class="ng-hard" aria-label="硬闸文案">' + gates + "</div>";
    root.innerHTML = top + sum + metrics + logHtml + table + foot + hard;
    if (data.hermes_touch !== false) {
      var warn = document.createElement("p");
      warn.className = "load-fail";
      warn.textContent = "FAIL 口径：hermes_touch 必须显 false（本 fixture 异常）";
      root.prepend(warn);
    }
  }
  function boot() {
    fetch("data/nodegate_fixture.json", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(render)
      .catch(function (e) {
        var root = $("#nodegate-viz-root");
        if (root) {
          root.innerHTML =
            '<p class="load-fail">节点门假数据加载失败：' +
            esc(e && e.message) +
            " · 仍零会话／零碰 Hermes</p>";
        }
      });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
