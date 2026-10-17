/* Vaelin UI demo shell S8 — fake data only · zero Hermes · scene preview / timer / talk print / a11y */
(function () {
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const VALID_SCREENS = [
    "screen-home",
    "screen-chat",
    "screen-status",
    "screen-settings",
    "screen-public",
    "screen-pitch",
    "screen-about",
    "screen-decl",
  ];
  let DATA = null;
  let currentSid = null;
  let currentScreen = "screen-home";
  let darkOn = false;
  let compactOn = false;
  let contrastOn = false;
  let watermarkOn = true;
  let filterQ = "";
  let filterTag = "全部";
  let msgQ = "";
  let msgRole = "全部";
  let tourOn = false;
  let tourIdx = 0;
  let helpOn = false;
  let demoState = "normal";
  let presenterOpen = false;
  let hashSilent = false;
  let toastTimer = null;
  let cleanOn = false;
  let cleanSaved = null; // { watermark, compact } when entering clean mode
  const LS_KEY = "vaelin.uiDemo.s7.prefs";
  const LS_KEY_S8 = "vaelin.uiDemo.s8.prefs";
  let persistEnabled = true;
  let timerSec = 0;
  let timerRunning = false;
  let timerHandle = null;
  let previewScreenId = null;

  function showScreen(id, opts) {
    opts = opts || {};
    if (!id || VALID_SCREENS.indexOf(id) < 0) id = "screen-home";
    currentScreen = id;
    $$(".screen").forEach((s) => s.classList.toggle("active", s.id === id));
    $$("nav button[data-screen]").forEach((b) =>
      b.classList.toggle("active", b.dataset.screen === id)
    );
    if (!opts.skipHash) {
      const want = "#" + id;
      if (location.hash !== want) {
        hashSilent = true;
        location.hash = want;
        setTimeout(() => {
          hashSilent = false;
        }, 0);
      }
    }
    syncPresenterNote();
    if (tourOn) syncTourHighlight();
  }

  function applyHash() {
    if (hashSilent) return;
    let raw = (location.hash || "").replace(/^#/, "").trim();
    if (!raw) {
      showScreen("screen-home", { skipHash: true });
      return;
    }
    if (VALID_SCREENS.indexOf(raw) < 0) {
      showScreen("screen-home", { skipHash: false });
      return;
    }
    showScreen(raw, { skipHash: true });
  }

  function showToast(msg, ok) {
    const el = $("#demo-toast");
    if (!el) return;
    el.hidden = false;
    el.textContent = msg || "";
    el.classList.toggle("ok", !!ok);
    el.classList.toggle("fail", ok === false);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.hidden = true;
      el.textContent = "";
    }, 1800);
  }


  function readPrefs() {
    if (!persistEnabled) return null;
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (!raw) return null;
      const o = JSON.parse(raw);
      return o && typeof o === "object" ? o : null;
    } catch (e) {
      return null;
    }
  }

  function writePrefs() {
    if (!persistEnabled) return;
    try {
      const o = {
        dark: darkOn,
        compact: compactOn,
        contrast: contrastOn,
        watermark: watermarkOn,
        presenterOpen: presenterOpen,
        clean: cleanOn,
      };
      localStorage.setItem(LS_KEY, JSON.stringify(o));
    } catch (e) {
      /* privacy / quota — stay in-memory */
    }
  }

  function clearPrefs() {
    try {
      localStorage.removeItem(LS_KEY);
    } catch (e) {}
    showToast("已清除本壳偏好", true);
  }

  function syncCleanButtons() {
    $$(".clean-toggle").forEach((btn) => {
      btn.setAttribute("aria-pressed", cleanOn ? "true" : "false");
      btn.textContent = cleanOn ? "干净模式（开）· 点此还原" : "开启干净模式";
    });
    document.body.classList.toggle("clean-mode", cleanOn);
  }

  function applyCleanMode(on, opts) {
    opts = opts || {};
    on = !!on;
    if (on === cleanOn && !opts.force) {
      syncCleanButtons();
      return;
    }
    if (on) {
      cleanSaved = { watermark: watermarkOn, compact: compactOn };
      cleanOn = true;
      applyWatermark(false, { skipCleanExit: true, skipPersist: true });
      applyCompact(true, { skipCleanExit: true, skipPersist: true });
      syncCleanButtons();
      if (!opts.silent) showToast("干净模式：水印关 · 紧凑开", true);
    } else {
      const saved = cleanSaved || { watermark: true, compact: false };
      cleanOn = false;
      cleanSaved = null;
      applyWatermark(!!saved.watermark, { skipCleanExit: true, skipPersist: true });
      applyCompact(!!saved.compact, { skipCleanExit: true, skipPersist: true });
      syncCleanButtons();
      if (!opts.silent) showToast("已还原干净模式前状态", true);
    }
    if (!opts.skipPersist) writePrefs();
  }

  function applyTheme(on, opts) {
    opts = opts || {};
    darkOn = !!on;
    document.body.classList.toggle("theme-dark", darkOn);
    $$(".theme-toggle").forEach((btn) => {
      btn.setAttribute("aria-pressed", darkOn ? "true" : "false");
      btn.textContent = darkOn ? "暗色（当页）" : "浅色（当页）";
    });
    if (!opts.skipPersist) writePrefs();
  }

  function applyCompact(on, opts) {
    opts = opts || {};
    compactOn = !!on;
    document.body.classList.toggle("density-compact", compactOn);
    $$(".density-toggle").forEach((btn) => {
      btn.setAttribute("aria-pressed", compactOn ? "true" : "false");
      btn.textContent = compactOn ? "紧凑（当页）" : "标准（当页）";
    });
    if (cleanOn && !opts.skipCleanExit) {
      cleanOn = false;
      cleanSaved = null;
      syncCleanButtons();
    }
    if (!opts.skipPersist) writePrefs();
  }

  function applyContrast(on, opts) {
    opts = opts || {};
    contrastOn = !!on;
    document.body.classList.toggle("contrast-high", contrastOn);
    $$(".contrast-toggle").forEach((btn) => {
      btn.setAttribute("aria-pressed", contrastOn ? "true" : "false");
      btn.textContent = contrastOn ? "高对比（开）" : "高对比（关）";
    });
    if (!opts.skipPersist) writePrefs();
  }

  function applyWatermark(on, opts) {
    opts = opts || {};
    watermarkOn = !!on;
    document.body.classList.toggle("wm-on", watermarkOn);
    const wm = $("#demo-watermark");
    if (wm) {
      const text =
        (DATA && DATA.watermark && DATA.watermark.text) ||
        "演示 · 非生产 · 无真实用户数据";
      wm.textContent = text;
      wm.hidden = !watermarkOn;
      wm.setAttribute("aria-hidden", watermarkOn ? "false" : "true");
    }
    $$(".watermark-toggle").forEach((btn) => {
      btn.setAttribute("aria-pressed", watermarkOn ? "true" : "false");
      btn.textContent = watermarkOn ? "水印（开）" : "水印（关）";
    });
    if (cleanOn && !opts.skipCleanExit) {
      cleanOn = false;
      cleanSaved = null;
      syncCleanButtons();
    }
    if (!opts.skipPersist) writePrefs();
  }

  function setDemoState(mode) {
    demoState = mode || "normal";
    const err = $("#boot-err");
    const empty = $("#empty-hint");
    document.body.classList.toggle("demo-show-empty", demoState === "empty");
    document.body.classList.toggle("demo-show-fail", demoState === "fail");
    if (err) {
      if (demoState === "fail") {
        err.hidden = false;
        err.textContent =
          "（演示开关）加载失败样式预览 · 不影响真实 fixture 路径 · 点「恢复正常」关闭";
      } else if (DATA) {
        err.hidden = true;
      }
    }
    if (empty) {
      empty.hidden = demoState !== "empty";
      if (demoState === "empty") empty.textContent = "暂无内容（演示空态 · 当页开关）";
    }
    const be = $("#btn-demo-empty");
    const bf = $("#btn-demo-fail");
    if (be) be.setAttribute("aria-pressed", demoState === "empty" ? "true" : "false");
    if (bf) bf.setAttribute("aria-pressed", demoState === "fail" ? "true" : "false");
  }

  function sessionMatches(s) {
    const q = filterQ.trim().toLowerCase();
    const tags = s.tags || [];
    if (filterTag && filterTag !== "全部" && tags.indexOf(filterTag) < 0) {
      return false;
    }
    if (!q) return true;
    const hay = [s.title || "", s.preview || "", tags.join(" ")].join(" ").toLowerCase();
    return hay.indexOf(q) >= 0;
  }

  function msgMatches(m) {
    if (msgRole && msgRole !== "全部" && m.role !== msgRole) return false;
    const q = msgQ.trim().toLowerCase();
    if (!q) return true;
    return (m.text || "").toLowerCase().indexOf(q) >= 0;
  }

  function renderTagChips() {
    const box = $("#sess-tags");
    if (!box) return;
    const tags = (DATA && DATA.filter_tags) || ["全部"];
    box.innerHTML = "";
    tags.forEach((t) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tag-chip" + (t === filterTag ? " on" : "");
      b.textContent = t;
      b.setAttribute("aria-pressed", t === filterTag ? "true" : "false");
      b.addEventListener("click", () => {
        filterTag = t;
        renderTagChips();
        renderSessions();
      });
      box.appendChild(b);
    });
  }

  function renderMsgRoleChips() {
    const box = $("#msg-roles");
    if (!box) return;
    const roles = (DATA && DATA.msg_filter_roles) || ["全部", "user", "assistant"];
    box.innerHTML = "";
    roles.forEach((r) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tag-chip" + (r === msgRole ? " on" : "");
      b.textContent = r;
      b.setAttribute("aria-pressed", r === msgRole ? "true" : "false");
      b.addEventListener("click", () => {
        msgRole = r;
        renderMsgRoleChips();
        if (currentSid) selectSession(currentSid);
      });
      box.appendChild(b);
    });
  }

  function renderSessions() {
    const list = $("#sesslist");
    list.innerHTML = "";
    if (!DATA.sessions || !DATA.sessions.length) {
      const empty = document.createElement("div");
      empty.className = "empty-inline";
      empty.textContent = "暂无会话（演示空态）";
      list.appendChild(empty);
      $("#flow").innerHTML = "";
      return;
    }
    const matched = DATA.sessions.filter(sessionMatches);
    if (!matched.length) {
      const empty = document.createElement("div");
      empty.className = "empty-inline";
      empty.textContent = "无匹配会话（假过滤 · 客户端）";
      list.appendChild(empty);
      return;
    }
    matched.forEach((s, i) => {
      const d = document.createElement("div");
      d.className = "sess" + (s.id === currentSid || (!currentSid && i === 0) ? " on" : "");
      d.dataset.id = s.id;
      d.tabIndex = 0;
      d.innerHTML =
        '<span class="t"></span><span class="p"></span><span class="u"></span><div class="tags"></div>';
      d.querySelector(".t").textContent = s.title;
      d.querySelector(".p").textContent = s.preview;
      d.querySelector(".u").textContent = s.updated;
      const tagsEl = d.querySelector(".tags");
      (s.tags || []).forEach((tg) => {
        const sp = document.createElement("span");
        sp.textContent = tg;
        tagsEl.appendChild(sp);
      });
      d.addEventListener("click", () => selectSession(s.id));
      d.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectSession(s.id);
        }
      });
      list.appendChild(d);
    });
    const keep =
      currentSid && matched.some((s) => s.id === currentSid)
        ? currentSid
        : matched[0].id;
    selectSession(keep);
  }

  function selectSession(id) {
    currentSid = id;
    $$(".sess").forEach((el) =>
      el.classList.toggle("on", el.dataset.id === id)
    );
    const flow = $("#flow");
    flow.innerHTML = "";
    const sys = document.createElement("div");
    sys.className = "msg sys";
    sys.textContent =
      "演示会话 · 假数据 fixture · 输入框只读 · 未接 Hermes／vault · 列表／消息过滤＝客户端";
    flow.appendChild(sys);
    const msgs = (DATA.messages && DATA.messages[id]) || [];
    if (!msgs.length) {
      const empty = document.createElement("div");
      empty.className = "msg sys";
      empty.textContent = "此会话暂无消息（演示空态）";
      flow.appendChild(empty);
      return;
    }
    const filtered = msgs.filter(msgMatches);
    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.className = "msg sys";
      empty.textContent = "无匹配消息（会话内假过滤 · 客户端）";
      flow.appendChild(empty);
      return;
    }
    filtered.forEach((m) => {
      const d = document.createElement("div");
      d.className = "msg " + m.role;
      d.textContent = m.text;
      flow.appendChild(d);
    });
    flow.scrollTop = flow.scrollHeight;
  }

  function renderModesRail() {
    const rail = $("#modes-rail-body");
    rail.innerHTML = "";
    DATA.modes.forEach((m) => {
      const d = document.createElement("div");
      d.className = "mode-card";
      d.innerHTML =
        '<div class="name"></div><div class="st"></div><div class="note"></div>';
      d.querySelector(".name").textContent = m.label;
      d.querySelector(".st").textContent = m.state;
      d.querySelector(".note").textContent = m.note;
      rail.appendChild(d);
    });
  }

  function renderStatus() {
    const st = DATA.status;
    const map = {
      "st-env": st.env,
      "st-hermes": st.hermes,
      "st-cev": st.cev,
      "st-data": st.data,
      "st-push": st.push,
    };
    Object.entries(map).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    });
    const row = $("#modes-status-row");
    row.innerHTML = "";
    DATA.modes.forEach((m) => {
      const d = document.createElement("div");
      d.className = "mode-card";
      d.innerHTML =
        '<div class="name"></div><div class="st"></div><div class="note"></div>';
      d.querySelector(".name").textContent = m.label;
      d.querySelector(".st").textContent = m.state;
      d.querySelector(".note").textContent = m.note;
      row.appendChild(d);
    });
    renderCompare($("#compare-status"));
  }

  function renderCompare(box) {
    if (!box) return;
    const c = DATA.compare || {};
    box.innerHTML = "";
    if (!c.title) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const h = document.createElement("h2");
    h.textContent = c.title;
    const sub = document.createElement("div");
    sub.className = "sub";
    sub.textContent = c.subtitle || "";
    const grid = document.createElement("div");
    grid.className = "compare-cols";
    const colA = document.createElement("div");
    colA.className = "compare-col ok";
    const ha = document.createElement("h3");
    ha.textContent = c.demo_label || "演示壳允许";
    const ula = document.createElement("ul");
    (c.demo || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      ula.appendChild(li);
    });
    colA.appendChild(ha);
    colA.appendChild(ula);
    const colB = document.createElement("div");
    colB.className = "compare-col ban";
    const hb = document.createElement("h3");
    hb.textContent = c.ban_label || "硬禁";
    const ulb = document.createElement("ul");
    (c.ban || []).forEach((t) => {
      const li = document.createElement("li");
      li.textContent = t;
      ulb.appendChild(li);
    });
    colB.appendChild(hb);
    colB.appendChild(ulb);
    grid.appendChild(colA);
    grid.appendChild(colB);
    box.appendChild(h);
    box.appendChild(sub);
    box.appendChild(grid);
  }

  function copyText(text, btn) {
    const done = () => {
      if (btn) {
        const old = btn.textContent;
        btn.textContent = "已复制";
        setTimeout(() => {
          btn.textContent = old;
        }, 1200);
      }
      showToast("已复制到剪贴板（客户端 · 无上报）", true);
    };
    const fail = () => showToast("复制失败（请手动选择文案）", false);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => {
        try {
          fallbackCopy(text, done);
        } catch (e) {
          fail();
        }
      });
    } else {
      try {
        fallbackCopy(text, done);
      } catch (e) {
        fail();
      }
    }
  }

  function fallbackCopy(text, done) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      if (done) done();
    } catch (e) {
      console.warn(e);
      throw e;
    }
    document.body.removeChild(ta);
  }

  function buildExportMarkdown() {
    const p = DATA.pitch || {};
    const c = DATA.compare || {};
    const brand = DATA.brand || {};
    const lines = [];
    lines.push("# " + ((DATA.export_pitch && DATA.export_pitch.title) || p.title || "Pitch"));
    lines.push("");
    lines.push("> 本页为演示 · 非生产 · 无真实用户数据");
    lines.push("");
    lines.push("**版本：** " + (brand.version || "S6"));
    lines.push("");
    lines.push(p.brand_line || "");
    lines.push("");
    lines.push("## Chips");
    (p.chips || []).forEach((x) => lines.push("- " + x));
    lines.push("");
    lines.push("## 硬闸");
    (p.gates || []).forEach((x) => lines.push("- " + x));
    lines.push("");
    if (c.title) {
      lines.push("## " + c.title);
      lines.push("");
      lines.push("### " + (c.demo_label || "演示壳允许"));
      (c.demo || []).forEach((x) => lines.push("- " + x));
      lines.push("");
      lines.push("### " + (c.ban_label || "硬禁"));
      (c.ban || []).forEach((x) => lines.push("- " + x));
      lines.push("");
    }
    lines.push("## 口径句");
    (DATA.copy_lines || []).forEach((cl) => {
      lines.push("- **" + cl.label + "：** " + cl.text);
    });
    lines.push("");
    lines.push(p.footer || "");
    lines.push("");
    lines.push("---");
    lines.push("本地假导出 · 无上传 · 零 Hermes · 默不 push · 不得写成已同批上仓／CEV 已验收");
    lines.push("");
    return lines.join("\n");
  }

  function fakeExportMd() {
    try {
      const md = buildExportMarkdown();
      const name =
        (DATA.export_pitch && DATA.export_pitch.filename) ||
        "vaelin-ui-demo-pitch-S6.md";
      const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 500);
      showToast("已假导出 " + name + "（本地下载 · 无上传）", true);
    } catch (e) {
      console.warn(e);
      showToast("假导出失败", false);
    }
  }

  function renderCopyLines(box) {
    if (!box) return;
    const lines = DATA.copy_lines || [];
    box.innerHTML = "";
    if (!lines.length) return;
    const h = document.createElement("h2");
    h.textContent = "可复制口径（客户端）";
    box.appendChild(h);
    const note = document.createElement("p");
    note.className = "muted";
    note.textContent = "纯客户端复制；无上报、无后端。成功后短暂 toast。";
    box.appendChild(note);
    lines.forEach((cl) => {
      const row = document.createElement("div");
      row.className = "copy-row";
      const meta = document.createElement("div");
      meta.className = "copy-meta";
      const lab = document.createElement("div");
      lab.className = "copy-label";
      lab.textContent = cl.label || "";
      const tx = document.createElement("div");
      tx.className = "copy-text";
      tx.textContent = cl.text || "";
      meta.appendChild(lab);
      meta.appendChild(tx);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "copy-btn";
      btn.textContent = "复制";
      btn.addEventListener("click", () => copyText(cl.text || "", btn));
      row.appendChild(meta);
      row.appendChild(btn);
      box.appendChild(row);
    });
  }

  function renderChangelog(box) {
    if (!box) return;
    const cl = DATA.changelog || {};
    const items = cl.items || [];
    box.innerHTML = "";
    if (!items.length) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const h = document.createElement("h2");
    h.textContent = cl.title || "加深时间线";
    const sub = document.createElement("p");
    sub.className = "muted";
    sub.textContent = cl.subtitle || "";
    const ul = document.createElement("ul");
    ul.className = "changelog-list";
    items.forEach((it) => {
      const li = document.createElement("li");
      const ver = document.createElement("span");
      ver.className = "cl-ver";
      ver.textContent = it.ver || "";
      const meta = document.createElement("div");
      meta.className = "cl-meta";
      const title = document.createElement("div");
      title.className = "cl-title";
      title.textContent = (it.title || "") + (it.date ? " · " + it.date : "");
      const note = document.createElement("div");
      note.className = "cl-note";
      note.textContent = it.note || "";
      meta.appendChild(title);
      meta.appendChild(note);
      li.appendChild(ver);
      li.appendChild(meta);
      ul.appendChild(li);
    });
    box.appendChild(h);
    box.appendChild(sub);
    box.appendChild(ul);
  }

  function renderSettings() {
    const box = $("#settings-list");
    if (!box) return;
    box.innerHTML = "";
    const settings = DATA.settings || {};
    const keys = Object.keys(settings);
    if (!keys.length) {
      box.innerHTML = '<div class="empty-inline">暂无设置项（演示空态）</div>';
      return;
    }
    keys.forEach((k) => {
      const s = settings[k];
      const row = document.createElement("div");
      row.className = "setting-row" + (s.editable ? "" : " locked");
      const left = document.createElement("div");
      left.className = "setting-meta";
      const lab = document.createElement("div");
      lab.className = "setting-label";
      lab.textContent = s.label || k;
      left.appendChild(lab);
      if (s.gate) {
        const gate = document.createElement("div");
        gate.className = "setting-gate";
        gate.textContent = s.gate;
        left.appendChild(gate);
      }
      const right = document.createElement("div");
      right.className = "setting-ctrl";
      if (k === "hermes_connect" || k === "vault_access") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.disabled = true;
        btn.className = "btn-disabled";
        btn.title = s.gate || "演示禁用";
        btn.textContent = s.value || "禁用";
        right.appendChild(btn);
      } else if (s.toggle === "theme") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "theme-toggle";
        btn.setAttribute("aria-pressed", darkOn ? "true" : "false");
        btn.textContent = darkOn ? "暗色（当页）" : "浅色（当页）";
        btn.addEventListener("click", () => applyTheme(!darkOn));
        right.appendChild(btn);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "假切换";
        right.appendChild(tag);
      } else if (s.toggle === "density") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "density-toggle";
        btn.setAttribute("aria-pressed", compactOn ? "true" : "false");
        btn.textContent = compactOn ? "紧凑（当页）" : "标准（当页）";
        btn.addEventListener("click", () => applyCompact(!compactOn));
        right.appendChild(btn);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "假切换";
        right.appendChild(tag);
      } else if (s.toggle === "contrast") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "contrast-toggle";
        btn.setAttribute("aria-pressed", contrastOn ? "true" : "false");
        btn.textContent = contrastOn ? "高对比（开）" : "高对比（关）";
        btn.addEventListener("click", () => applyContrast(!contrastOn));
        right.appendChild(btn);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "假切换";
        right.appendChild(tag);
      } else if (s.toggle === "watermark") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "watermark-toggle";
        btn.setAttribute("aria-pressed", watermarkOn ? "true" : "false");
        btn.textContent = watermarkOn ? "水印（开）" : "水印（关）";
        btn.addEventListener("click", () => applyWatermark(!watermarkOn));
        right.appendChild(btn);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "假切换";
        right.appendChild(tag);
      } else if (s.toggle === "clean") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "clean-toggle";
        btn.setAttribute("aria-pressed", cleanOn ? "true" : "false");
        btn.textContent = cleanOn ? "干净模式（开）· 点此还原" : "开启干净模式";
        btn.addEventListener("click", () => applyCleanMode(!cleanOn));
        right.appendChild(btn);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "S7";
        right.appendChild(tag);
      } else {
        const val = document.createElement("span");
        val.className = "setting-value";
        val.textContent = s.value || "—";
        right.appendChild(val);
        const tag = document.createElement("span");
        tag.className = "setting-tag";
        tag.textContent = "只读";
        right.appendChild(tag);
      }
      row.appendChild(left);
      row.appendChild(right);
      box.appendChild(row);
    });
  }

  function syncPresenterNote() {
    const bar = $("#presenter-bar");
    const noteEl = $("#presenter-note");
    const trackEl = $("#talk-track");
    if (!bar || !DATA) return;
    const pn = DATA.presenter_notes || {};
    const by = pn.by_screen || {};
    const note = by[currentScreen] || "";
    bar.hidden = false;
    if (noteEl) {
      noteEl.innerHTML = "";
      if (!note) {
        noteEl.textContent = "（本屏暂无讲者备注）";
      } else if (typeof note === "string") {
        noteEl.textContent = note;
      } else {
        const goal = document.createElement("div");
        goal.className = "pn-goal";
        goal.textContent = note.goal || "";
        noteEl.appendChild(goal);
        const ul = document.createElement("ul");
        ul.className = "pn-points";
        (note.points || []).forEach((t) => {
          const li = document.createElement("li");
          li.textContent = t;
          ul.appendChild(li);
        });
        noteEl.appendChild(ul);
        if (note.warn) {
          const w = document.createElement("div");
          w.className = "pn-warn";
          w.textContent = note.warn;
          noteEl.appendChild(w);
        }
      }
    }
    if (trackEl) {
      trackEl.innerHTML = "";
      const tt = DATA.talk_track || {};
      (tt.steps || []).forEach((s) => {
        const li = document.createElement("li");
        li.textContent = s;
        trackEl.appendChild(li);
      });
    }
    const tog = $("#presenter-toggle");
    if (tog) tog.textContent = (pn.title || "讲者备注") + (presenterOpen ? " ▾" : " ▸");
  }

  function setPresenterOpen(on, opts) {
    opts = opts || {};
    presenterOpen = !!on;
    const body = $("#presenter-body");
    const tog = $("#presenter-toggle");
    if (body) body.hidden = !presenterOpen;
    if (tog) {
      tog.setAttribute("aria-expanded", presenterOpen ? "true" : "false");
      const pn = (DATA && DATA.presenter_notes) || {};
      tog.textContent = (pn.title || "讲者备注") + (presenterOpen ? " ▾" : " ▸");
    }
    if (!opts.skipPersist) writePrefs();
  }

  function renderAbout() {
    const a = DATA.about || {};
    const title = $("#about-title");
    const summary = $("#about-summary");
    const bounds = $("#about-boundaries");
    const docs = $("#about-docs");
    const note = $("#about-note");
    if (title) title.textContent = a.title || "关于／边界";
    if (summary) summary.textContent = a.summary || "";
    if (bounds) {
      bounds.innerHTML = "";
      (a.boundaries || []).forEach((t) => {
        const li = document.createElement("li");
        li.textContent = t;
        bounds.appendChild(li);
      });
    }
    if (docs) {
      docs.innerHTML = "";
      (a.doc_paths || []).forEach((p) => {
        const li = document.createElement("li");
        const code = document.createElement("code");
        code.textContent = p;
        li.appendChild(code);
        docs.appendChild(li);
      });
    }
    if (note) note.textContent = a.note || "";
    renderCopyLines($("#copy-lines-about"));
    renderChangelog($("#changelog-about"));
  }

  function renderStoryboard() {
    const box = $("#storyboard-home");
    if (!box) return;
    const sb = DATA.storyboard || {};
    const steps = sb.steps || [];
    box.innerHTML = "";
    if (!steps.length) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const h2 = document.createElement("h2");
    h2.textContent = sb.title || "录屏故事板";
    const sub = document.createElement("div");
    sub.className = "sub";
    sub.textContent = sb.subtitle || "";
    const grid = document.createElement("div");
    grid.className = "storyboard-steps";
    steps.forEach((st, i) => {
      const d = document.createElement("div");
      d.className = "sb-step" + (tourOn && i === tourIdx ? " on" : "");
      d.dataset.step = String(i);
      d.innerHTML = '<span class="n"></span><span class="t"></span><span class="h"></span>';
      d.querySelector(".n").textContent = String(st.n);
      d.querySelector(".t").textContent = st.title || "";
      d.querySelector(".h").textContent = st.hint || "";
      d.tabIndex = 0;
      d.addEventListener("click", () => {
        openTour(i);
      });
      d.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openTour(i);
        }
      });
      grid.appendChild(d);
    });
    box.appendChild(h2);
    box.appendChild(sub);
    box.appendChild(grid);
  }

  function renderPitch() {
    const box = $("#pitch-body");
    if (!box) return;
    const p = DATA.pitch || {};
    const sb = DATA.storyboard || {};
    box.innerHTML = "";
    const h1 = document.createElement("h1");
    h1.textContent = p.title || "一页讲完 · Pitch";
    const brand = document.createElement("p");
    brand.className = "pitch-brand";
    brand.textContent = p.brand_line || "";
    const chips = document.createElement("div");
    chips.className = "pitch-chips";
    (p.chips || []).forEach((c, i) => {
      const sp = document.createElement("span");
      sp.className = "chip" + (i < 3 ? " ok" : "");
      sp.textContent = c;
      chips.appendChild(sp);
    });
    const actions = document.createElement("div");
    actions.className = "pitch-actions";
    const btnCopy = document.createElement("button");
    btnCopy.type = "button";
    btnCopy.textContent = "复制对外口径句";
    btnCopy.addEventListener("click", () => {
      const line =
        (DATA.copy_lines && DATA.copy_lines[0] && DATA.copy_lines[0].text) ||
        (DATA.brand && DATA.brand.disclaimer) ||
        "本页为演示 · 非生产 · 无真实用户数据";
      copyText(line, btnCopy);
    });
    const btnExport = document.createElement("button");
    btnExport.type = "button";
    btnExport.className = "ghost";
    btnExport.textContent = "假导出 pitch Markdown";
    btnExport.addEventListener("click", () => fakeExportMd());
    actions.appendChild(btnCopy);
    actions.appendChild(btnExport);
    const gatesBlock = document.createElement("div");
    gatesBlock.className = "panel-block";
    gatesBlock.style.maxWidth = "none";
    gatesBlock.style.margin = "0 0 0";
    const gh = document.createElement("h2");
    gh.textContent = "硬闸（演示壳内可见）";
    const ul = document.createElement("ul");
    ul.className = "pitch-gates";
    (p.gates || []).forEach((g) => {
      const li = document.createElement("li");
      li.textContent = g;
      ul.appendChild(li);
    });
    gatesBlock.appendChild(gh);
    gatesBlock.appendChild(ul);
    const cmp = document.createElement("div");
    cmp.className = "compare-card nested";
    renderCompare(cmp);
    const sbWrap = document.createElement("div");
    sbWrap.className = "storyboard pitch-sb";
    const sh = document.createElement("h2");
    sh.textContent = sb.title || "故事板步骤";
    const ssub = document.createElement("div");
    ssub.className = "sub";
    ssub.textContent = sb.subtitle || "";
    const grid = document.createElement("div");
    grid.className = "storyboard-steps";
    (sb.steps || []).forEach((st) => {
      const d = document.createElement("div");
      d.className = "sb-step";
      d.innerHTML = '<span class="n"></span><span class="t"></span><span class="h"></span>';
      d.querySelector(".n").textContent = String(st.n);
      d.querySelector(".t").textContent = st.title || "";
      d.querySelector(".h").textContent = st.hint || "";
      grid.appendChild(d);
    });
    sbWrap.appendChild(sh);
    sbWrap.appendChild(ssub);
    sbWrap.appendChild(grid);
    const clBox = document.createElement("div");
    clBox.className = "changelog nested";
    renderChangelog(clBox);
    const foot = document.createElement("div");
    foot.className = "pitch-foot";
    foot.textContent = p.footer || "";
    const notice = document.createElement("div");
    notice.className = "notice";
    notice.innerHTML =
      "<strong>非生产黄条常驻。</strong>本页可截图／打印手出／假导出；不得写成已接 Hermes 生产或 CEV 已上仓验收。假导出＝本地下载，无上传。hash 深链可直达本屏。";
    box.appendChild(h1);
    box.appendChild(brand);
    box.appendChild(chips);
    box.appendChild(actions);
    box.appendChild(gatesBlock);
    box.appendChild(cmp);
    box.appendChild(sbWrap);
    box.appendChild(clBox);
    box.appendChild(foot);
    box.appendChild(notice);
  }

  function renderPublic() {
    const pl = DATA.public_links || {};
    const title = $("#public-title");
    const intro = $("#public-intro");
    const groupsEl = $("#public-groups");
    const footer = $("#public-footer");
    if (title) title.textContent = pl.title || "已公开叙事／边界索引";
    if (intro) intro.textContent = pl.intro || "";
    if (footer) footer.textContent = pl.footer || "";
    if (!groupsEl) return;
    groupsEl.innerHTML = "";
    const items = pl.items || [];
    if (!items.length) {
      groupsEl.innerHTML = '<div class="empty-inline">暂无公开叙事条目（演示空态）</div>';
      return;
    }
    const byGroup = {};
    items.forEach((it) => {
      const g = it.group || "其他";
      if (!byGroup[g]) byGroup[g] = [];
      byGroup[g].push(it);
    });
    Object.keys(byGroup).forEach((g) => {
      const sec = document.createElement("div");
      sec.className = "public-group";
      const h2 = document.createElement("h2");
      h2.textContent = g;
      const cards = document.createElement("div");
      cards.className = "public-cards";
      byGroup[g].forEach((it) => {
        const card = document.createElement("div");
        card.className = "public-card";
        const lab = document.createElement("div");
        lab.className = "label";
        lab.textContent = it.label || "";
        const code = document.createElement("code");
        code.textContent = it.path || "";
        const note = document.createElement("div");
        note.className = "note";
        note.textContent = it.note || "";
        card.appendChild(lab);
        card.appendChild(code);
        if (it.note) card.appendChild(note);
        cards.appendChild(card);
      });
      sec.appendChild(h2);
      sec.appendChild(cards);
      groupsEl.appendChild(sec);
    });
  }

  function tourSteps() {
    return (DATA && DATA.storyboard && DATA.storyboard.steps) || [];
  }

  function clearSpotlight() {
    $$(".tour-spotlight").forEach((el) => el.classList.remove("tour-spotlight"));
    document.body.classList.remove("tour-dim");
  }

  function applySpotlight(st) {
    clearSpotlight();
    if (!tourOn || !st) return;
    const sel = st.spotlight;
    if (!sel) return;
    let el = null;
    try {
      el = document.querySelector(sel);
    } catch (e) {
      el = null;
    }
    if (!el) return;
    document.body.classList.add("tour-dim");
    el.classList.add("tour-spotlight");
  }

  function renderTourDots() {
    const box = $("#tour-dots");
    if (!box) return;
    const steps = tourSteps();
    box.innerHTML = "";
    steps.forEach((st, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tour-dot" + (i === tourIdx ? " on" : "");
      b.setAttribute("aria-label", "跳到步骤 " + st.n + " · " + (st.title || ""));
      b.title = (st.n || i + 1) + ". " + (st.title || "");
      b.addEventListener("click", () => openTour(i));
      box.appendChild(b);
    });
  }

  function syncTourHighlight() {
    const steps = tourSteps();
    const st = steps[tourIdx];
    const label = $("#tour-step-label");
    const hint = $("#tour-step-hint");
    if (label) {
      label.textContent = st
        ? "步骤 " + st.n + "／" + steps.length + " · " + (st.title || "")
        : "—";
    }
    if (hint) hint.textContent = st ? st.hint || "" : "";
    $$(".sb-step").forEach((el) => {
      const i = parseInt(el.dataset.step || "-1", 10);
      el.classList.toggle("on", tourOn && i === tourIdx);
    });
    const prev = $("#tour-prev");
    const next = $("#tour-next");
    if (prev) prev.disabled = tourIdx <= 0;
    if (next) next.disabled = tourIdx >= steps.length - 1;
    renderTourDots();
    applySpotlight(st);
  }

  function goTour(delta) {
    const steps = tourSteps();
    if (!steps.length) return;
    tourIdx = Math.max(0, Math.min(steps.length - 1, tourIdx + delta));
    const st = steps[tourIdx];
    if (st && st.screen) showScreen(st.screen);
    syncTourHighlight();
  }

  function openTour(idx) {
    const steps = tourSteps();
    if (!steps.length) return;
    tourOn = true;
    tourIdx = typeof idx === "number" ? idx : 0;
    tourIdx = Math.max(0, Math.min(steps.length - 1, tourIdx));
    const bar = $("#tour-bar");
    if (bar) bar.hidden = false;
    const st = steps[tourIdx];
    if (st && st.screen) showScreen(st.screen);
    syncTourHighlight();
  }

  function closeTour() {
    tourOn = false;
    const bar = $("#tour-bar");
    if (bar) bar.hidden = true;
    $$(".sb-step").forEach((el) => el.classList.remove("on"));
    clearSpotlight();
    setHelp(false);
  }

  function setHelp(on) {
    helpOn = !!on;
    const panel = $("#tour-help-panel");
    if (panel) panel.hidden = !helpOn;
    if (helpOn) {
      const body = $("#tour-help-body");
      const list = $("#tour-help-list");
      const tour = (DATA && DATA.demo_tour) || {};
      if (body) {
        body.textContent =
          tour.help ||
          "←／→ 步进 · ? 帮助 · Esc 关闭 · g 干净模式 · p 讲者条 · #screen-pitch 深链";
      }
      if (list) {
        list.innerHTML = "";
        const km = tour.keymap || [
          { key: "← / →", action: "导览步进" },
          { key: "?", action: "帮助" },
          { key: "Esc", action: "关闭帮助／导览" },
          { key: "g", action: "截图干净模式" },
          { key: "p", action: "讲者备注" },
        ];
        km.forEach((row) => {
          const li = document.createElement("li");
          const k = document.createElement("kbd");
          k.textContent = row.key || "";
          li.appendChild(k);
          li.appendChild(document.createTextNode(" — " + (row.action || "")));
          list.appendChild(li);
        });
      }
    }
  }


  function formatTimer(sec) {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
  }

  function syncTimerUI() {
    const el = $("#timer-display");
    if (el) el.textContent = formatTimer(timerSec);
    const cfg = (DATA && DATA.presenter_timer) || {};
    const tgt = $("#timer-target");
    if (tgt) {
      const ts = cfg.target_seconds;
      tgt.textContent = ts ? "目标 " + ts + "s" : "";
    }
    const start = $("#timer-start");
    if (start) start.textContent = timerRunning ? "计时中…" : "开始";
  }

  function timerTick() {
    timerSec += 1;
    syncTimerUI();
  }

  function timerStart() {
    if (timerRunning) return;
    timerRunning = true;
    timerHandle = setInterval(timerTick, 1000);
    syncTimerUI();
    showToast("讲者计时开始", true);
  }

  function timerPause() {
    if (!timerRunning) return;
    timerRunning = false;
    if (timerHandle) clearInterval(timerHandle);
    timerHandle = null;
    syncTimerUI();
    showToast("讲者计时暂停", true);
  }

  function timerReset() {
    timerPause();
    timerSec = 0;
    syncTimerUI();
  }

  function timerToggle() {
    if (timerRunning) timerPause();
    else timerStart();
  }

  function nextScreenId() {
    const order = VALID_SCREENS;
    const i = order.indexOf(currentScreen);
    if (i < 0) return order[0];
    return order[(i + 1) % order.length];
  }

  function previewMeta(sid) {
    const map = (DATA && DATA.scene_previews && DATA.scene_previews.by_screen) || {};
    const hit = map[sid] || {};
    const labels = {
      "screen-home": "首页",
      "screen-chat": "会话占位",
      "screen-status": "状态／模式",
      "screen-settings": "设置",
      "screen-public": "公开叙事",
      "screen-pitch": "一页 pitch",
      "screen-about": "关于／边界",
      "screen-decl": "非生产声明",
    };
    return {
      id: sid,
      title: hit.title || labels[sid] || sid,
      hint: hit.hint || "",
    };
  }

  function showScenePreview(sid) {
    sid = sid || nextScreenId();
    previewScreenId = sid;
    const meta = previewMeta(sid);
    const box = $("#scene-preview");
    if (!box) return;
    box.hidden = false;
    const t = $("#scene-preview-title");
    const h = $("#scene-preview-hint");
    if (t) t.textContent = meta.title;
    if (h) h.textContent = meta.hint;
  }

  function hideScenePreview() {
    const box = $("#scene-preview");
    if (box) box.hidden = true;
    previewScreenId = null;
  }

  function toggleScenePreview() {
    const box = $("#scene-preview");
    if (box && !box.hidden) hideScenePreview();
    else showScenePreview(nextScreenId());
  }

  function buildTalkScriptHtml() {
    const ts = (DATA && DATA.talk_script) || {};
    const parts = [];
    parts.push("<p><strong>" + (ts.title || "演示讲稿") + "</strong></p>");
    if (ts.subtitle) parts.push("<p class='muted'>" + ts.subtitle + "</p>");
    const by = (DATA.presenter_notes && DATA.presenter_notes.by_screen) || {};
    VALID_SCREENS.forEach((sid) => {
      const note = by[sid];
      if (!note) return;
      const meta = previewMeta(sid);
      parts.push("<h3>" + meta.title + "</h3>");
      if (typeof note === "string") {
        parts.push("<p>" + note + "</p>");
      } else {
        if (note.goal) parts.push("<p>" + note.goal + "</p>");
        if (note.points && note.points.length) {
          parts.push("<ul>" + note.points.map((p) => "<li>" + p + "</li>").join("") + "</ul>");
        }
        if (note.warn) parts.push("<p><em>" + note.warn + "</em></p>");
      }
    });
    const track = (DATA.talk_track && DATA.talk_track.steps) || [];
    if (track.length) {
      parts.push("<h3>" + ((DATA.talk_track && DATA.talk_track.title) || "口头轨") + "</h3>");
      parts.push("<ol>" + track.map((s) => "<li>" + s + "</li>").join("") + "</ol>");
    }
    const lines = (DATA.copy_lines || []).slice(0, 3);
    if (lines.length) {
      parts.push("<h3>对外口径</h3><ul>");
      lines.forEach((L) => {
        parts.push("<li>" + (L.text || L) + "</li>");
      });
      parts.push("</ul>");
    }
    if (ts.footer) parts.push("<p class='muted'>" + ts.footer + "</p>");
    return parts.join("\n");
  }

  function openTalkScript() {
    const panel = $("#talk-script-panel");
    if (!panel) return;
    const ts = (DATA && DATA.talk_script) || {};
    const title = $("#talk-script-title");
    const sub = $("#talk-script-sub");
    const body = $("#talk-script-body");
    if (title) title.textContent = ts.title || "演示讲稿";
    if (sub) sub.textContent = ts.subtitle || "";
    if (body) body.innerHTML = buildTalkScriptHtml();
    panel.hidden = false;
    document.body.classList.add("talk-script-open");
    const closeBtn = $("#talk-script-close");
    if (closeBtn) closeBtn.focus();
  }

  function closeTalkScript() {
    const panel = $("#talk-script-panel");
    if (panel) panel.hidden = true;
    document.body.classList.remove("talk-script-open");
  }

  function downloadTalkScript() {
    const htmlDoc =
      "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>Vaelin 演示讲稿 S8</title>" +
      "<style>body{font-family:sans-serif;max-width:40rem;margin:2rem auto;line-height:1.55}" +
      "h3{margin-top:1.2rem}.muted{opacity:.7}</style></head><body>" +
      buildTalkScriptHtml() +
      "</body></html>";
    const blob = new Blob([htmlDoc], { type: "text/html;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "vaelin-demo-talk-script-s8.html";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 500);
    showToast("已下载讲稿 HTML（可浏览器打开后打印为 PDF）", true);
  }

  function printTalkScript() {
    openTalkScript();
    setTimeout(() => window.print(), 120);
  }

  function wireNav() {
    $$("nav button[data-screen]").forEach((b) => {
      b.addEventListener("click", () => showScreen(b.dataset.screen));
    });
    $$("[data-goto]").forEach((b) => {
      b.addEventListener("click", () => showScreen(b.dataset.goto));
    });
    const btnTour = $("#btn-tour");
    if (btnTour) btnTour.addEventListener("click", () => (tourOn ? closeTour() : openTour(0)));
    const ctaTour = $("#cta-tour");
    if (ctaTour) ctaTour.addEventListener("click", () => openTour(0));
    const prev = $("#tour-prev");
    const next = $("#tour-next");
    const close = $("#tour-close");
    const help = $("#tour-help");
    const helpOk = $("#tour-help-ok");
    if (prev) prev.addEventListener("click", () => goTour(-1));
    if (next) next.addEventListener("click", () => goTour(1));
    if (close) close.addEventListener("click", () => closeTour());
    if (help) help.addEventListener("click", () => setHelp(!helpOn));
    if (helpOk) helpOk.addEventListener("click", () => setHelp(false));
    const q = $("#sess-q");
    if (q) {
      q.addEventListener("input", () => {
        filterQ = q.value || "";
        renderSessions();
      });
    }
    const mq = $("#msg-q");
    if (mq) {
      mq.addEventListener("input", () => {
        msgQ = mq.value || "";
        if (currentSid) selectSession(currentSid);
      });
    }
    const be = $("#btn-demo-empty");
    const bf = $("#btn-demo-fail");
    const bn = $("#btn-demo-normal");
    if (be) be.addEventListener("click", () => setDemoState(demoState === "empty" ? "normal" : "empty"));
    if (bf) bf.addEventListener("click", () => setDemoState(demoState === "fail" ? "normal" : "fail"));
    if (bn) bn.addEventListener("click", () => setDemoState("normal"));
    const pt = $("#presenter-toggle");
    if (pt) pt.addEventListener("click", () => setPresenterOpen(!presenterOpen));
    const btnClean = $("#btn-clean-mode");
    if (btnClean) btnClean.addEventListener("click", () => applyCleanMode(!cleanOn));
    const btnClear = $("#btn-clear-prefs");
    if (btnClear)
      btnClear.addEventListener("click", () => {
        clearPrefs();
      });
    const tStart = $("#timer-start");
    const tPause = $("#timer-pause");
    const tReset = $("#timer-reset");
    if (tStart) tStart.addEventListener("click", () => timerStart());
    if (tPause) tPause.addEventListener("click", () => timerPause());
    if (tReset) tReset.addEventListener("click", () => timerReset());
    const btnTalk = $("#btn-talk-script");
    if (btnTalk) btnTalk.addEventListener("click", () => openTalkScript());
    const btnPrev = $("#btn-scene-preview");
    if (btnPrev) btnPrev.addEventListener("click", () => toggleScenePreview());
    const spGo = $("#scene-preview-go");
    const spClose = $("#scene-preview-close");
    if (spGo)
      spGo.addEventListener("click", () => {
        const sid = previewScreenId || nextScreenId();
        hideScenePreview();
        showScreen(sid);
      });
    if (spClose) spClose.addEventListener("click", () => hideScenePreview());
    const tourPrev = $("#tour-preview");
    if (tourPrev)
      tourPrev.addEventListener("click", () => {
        const steps = tourSteps();
        const st = steps[Math.min(tourIdx + 1, Math.max(0, steps.length - 1))];
        const sid = (st && st.screen) || nextScreenId();
        showScenePreview(sid);
      });
    const tsPrint = $("#talk-script-print");
    const tsDl = $("#talk-script-download");
    const tsClose = $("#talk-script-close");
    if (tsPrint) tsPrint.addEventListener("click", () => printTalkScript());
    if (tsDl) tsDl.addEventListener("click", () => downloadTalkScript());
    if (tsClose) tsClose.addEventListener("click", () => closeTalkScript());
    window.addEventListener("hashchange", () => applyHash());
    document.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) || "";
      const typing =
        tag === "INPUT" || tag === "TEXTAREA" || (e.target && e.target.isContentEditable);
      if (e.key === "?" && !typing) {
        e.preventDefault();
        if (!tourOn) openTour(tourIdx);
        setHelp(!helpOn);
        return;
      }
      if (e.key === "Escape") {
        if (helpOn) {
          setHelp(false);
          return;
        }
        const tsp = $("#talk-script-panel");
        if (tsp && !tsp.hidden) {
          closeTalkScript();
          return;
        }
        const sp = $("#scene-preview");
        if (sp && !sp.hidden) {
          hideScenePreview();
          return;
        }
        if (tourOn) {
          closeTour();
          return;
        }
      }
      if (typing) return;
      if (e.key === "g" || e.key === "G") {
        e.preventDefault();
        applyCleanMode(!cleanOn);
        return;
      }
      if ((e.key === "p" || e.key === "P") && e.shiftKey) {
        e.preventDefault();
        const panel = $("#talk-script-panel");
        if (panel && !panel.hidden) closeTalkScript();
        else openTalkScript();
        return;
      }
      if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        setPresenterOpen(!presenterOpen);
        return;
      }
      if (e.key === "t" || e.key === "T") {
        e.preventDefault();
        if (!presenterOpen) setPresenterOpen(true);
        timerToggle();
        return;
      }
      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        toggleScenePreview();
        return;
      }
      if (e.key === "ArrowRight") {
        if (!tourOn) openTour(0);
        else goTour(1);
        e.preventDefault();
      } else if (e.key === "ArrowLeft") {
        if (!tourOn) openTour(0);
        else goTour(-1);
        e.preventDefault();
      }
    });
  }

  async function boot() {
    const err = $("#boot-err");
    try {
      const r = await fetch("data/fixture.json", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      DATA = await r.json();
    } catch (e) {
      console.error(e);
      if (err) {
        err.hidden = false;
        err.textContent =
          "无法加载 data/fixture.json（加载失败）。请用本地 HTTP 服务打开（见 README start_demo.bat），勿直接 file://。错误：" +
          (e && e.message ? e.message : String(e));
      }
      return;
    }
    if (err) err.hidden = true;
    $("#brand-name").textContent = DATA.brand.name;
    $("#brand-tag").textContent = DATA.brand.tagline;
    $$(".np-text").forEach((el) => {
      el.textContent = DATA.brand.disclaimer;
    });
    renderTagChips();
    renderMsgRoleChips();
    renderSessions();
    renderModesRail();
    renderStatus();
    renderSettings();
    renderAbout();
    renderStoryboard();
    renderPitch();
    renderPublic();
    wireNav();
    const prefs = readPrefs() || {};
    const wmDefault =
      DATA.watermark && typeof DATA.watermark.default_on === "boolean"
        ? DATA.watermark.default_on
        : true;
    applyTheme(!!prefs.dark, { skipPersist: true });
    applyCompact(!!prefs.compact, { skipPersist: true });
    applyContrast(!!prefs.contrast, { skipPersist: true });
    const wmInit =
      typeof prefs.watermark === "boolean" ? prefs.watermark : wmDefault;
    applyWatermark(wmInit, { skipPersist: true, skipCleanExit: true });
    setDemoState("normal");
    const collapsed =
      DATA.presenter_notes && DATA.presenter_notes.default_collapsed !== false;
    const presenterInit =
      typeof prefs.presenterOpen === "boolean" ? prefs.presenterOpen : !collapsed;
    setPresenterOpen(presenterInit, { skipPersist: true });
    if (prefs.clean) {
      applyCleanMode(true, { silent: true, skipPersist: true, force: true });
    } else {
      syncCleanButtons();
    }
    syncPresenterNote();
    // bump banner sub to S7 if static
    $$(".sub").forEach((el) => {
      if (el.textContent && el.textContent.indexOf("S6") >= 0) {
        el.textContent = el.textContent.replace(/S6/g, "S7");
      }
    });
    if (location.hash) applyHash();
    else showScreen("screen-home");
  }

  boot();
})();
