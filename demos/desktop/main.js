"use strict";

/**
 * Vaelin UI 演示壳 · Desktop-S3（基于 Desktop-S2 本地加深）
 * DEMO · 非生产 · 假数据 · 零 Hermes
 * demo ≠ production · install ≠ enable · 签 ≠ 启用
 * 8766 ≠ Hermes desktop
 *
 * 只提供本目录内拷贝的 S9 静态资源（index.html / css / js / data）。
 * 内嵌静态服只绑定 127.0.0.1。不调用 crashReporter、不装 autoUpdater、
 * 关闭 Chromium 后台联网／组件更新／指标上报。
 *
 * S3 加深：基线回归／硬闸可见化／键位帮助／窗口几何本机记忆／selftest 加固／文档短注。
 * userData 仅 staging .electron-userdata/；禁写 %LocalAppData%\hermes。
 */

const { app, BrowserWindow, session, Tray, Menu, nativeImage, dialog } = require("electron");
const http = require("http");
const fs = require("fs");
const path = require("path");

const HOST = "127.0.0.1";
const PORT_START = 8766;
const PORT_TRIES = 10;
const WINDOW_TITLE = "Vaelin UI 演示壳 · Desktop-S3 · DEMO · 非生产";
const ROOT = __dirname;
const PORT_FILE = path.join(ROOT, ".desktop-s1-port");
const SELFTEST =
  process.env.DESKTOP_S3_SELFTEST === "1" ||
  process.env.DESKTOP_S2_SELFTEST === "1" ||
  process.env.DESKTOP_S1_SELFTEST === "1";
const SELFTEST_OUT =
  process.env.DESKTOP_S3_SELFTEST_OUT ||
  process.env.DESKTOP_S2_SELFTEST_OUT ||
  process.env.DESKTOP_S1_SELFTEST_OUT ||
  "";
const SELFTEST_PNG =
  process.env.DESKTOP_S3_SELFTEST_PNG ||
  process.env.DESKTOP_S2_SELFTEST_PNG ||
  process.env.DESKTOP_S1_SELFTEST_PNG ||
  "";
const USER_DATA_DIR = path.join(ROOT, ".electron-userdata");
const BOUNDS_FILE = path.join(USER_DATA_DIR, "window-bounds.json");
const HARD_GATE_LINES = [
  "签 ≠ 启用",
  "demo ≠ production",
  "install ≠ enable",
  "8766 ≠ Hermes desktop",
  "零 Hermes",
];
const TRAY_OPT_IN =
  process.env.DESKTOP_S2_TRAY === "1" ||
  process.argv.includes("--tray");
const MIN_SCREENS = 5;

app.disableHardwareAcceleration();
app.commandLine.appendSwitch("disable-gpu");
app.commandLine.appendSwitch("disable-gpu-compositing");
app.commandLine.appendSwitch("disable-software-rasterizer");
app.setName("Vaelin UI Demo Desktop-S3");
app.setPath("userData", USER_DATA_DIR);

app.commandLine.appendSwitch("disable-background-networking");
app.commandLine.appendSwitch("disable-component-update");
app.commandLine.appendSwitch("disable-domain-reliability");
app.commandLine.appendSwitch("disable-breakpad");
app.commandLine.appendSwitch("disable-client-side-phishing-detection");
app.commandLine.appendSwitch("disable-sync");
app.commandLine.appendSwitch("no-pings");
app.commandLine.appendSwitch(
  "disable-features",
  [
    "Translate",
    "OptimizationHints",
    "MediaRouter",
    "DialMediaRouteProvider",
    "CalculateNativeWinOcclusion",
    "InterestFeedContentSuggestions",
    "AutofillServerCommunication",
    "CertificateTransparencyComponentUpdater",
    "SafeBrowsing",
  ].join(",")
);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8",
  ".woff2": "font/woff2",
};

const BLOCKED_TOP = new Set([
  "main.js",
  "package.json",
  "package-lock.json",
  "start_desktop.bat",
  "run_selftest.bat",
  "selftest_check.js",
  "README.md",
  ".gitignore",
]);

function logInfo(msg) {
  process.stdout.write("[Desktop-S3] " + msg + "\n");
}

function logErr(msg) {
  process.stderr.write("[Desktop-S3][失败] " + msg + "\n");
}

function listen(server, port, left) {
  return new Promise((resolve, reject) => {
    const onError = (err) => {
      server.removeListener("error", onError);
      if (err && err.code === "EADDRINUSE" && left > 0) {
        logInfo(
          "端口 " +
            port +
            " 占用，顺延试 " +
            (port + 1) +
            "（默认仍从 8766 起；勿改回 8765）"
        );
        resolve(listen(server, port + 1, left - 1));
        return;
      }
      const hint =
        err && err.code === "EADDRINUSE"
          ? "（8766–" +
            (PORT_START + PORT_TRIES - 1) +
            " 均占用；关掉旧桌面窗后重试）"
          : "";
      reject(
        new Error(
          "静态服绑定失败 port=" +
            port +
            " code=" +
            (err && err.code ? err.code : "?") +
            " " +
            String(err && err.message ? err.message : err) +
            hint
        )
      );
    };
    server.once("error", onError);
    server.listen(port, HOST, () => {
      server.removeListener("error", onError);
      resolve(port);
    });
  });
}

function startServer() {
  const rootNorm = path.resolve(ROOT);
  const server = http.createServer((req, res) => {
    try {
      if (req.method !== "GET" && req.method !== "HEAD") {
        res.writeHead(405, { Allow: "GET, HEAD" });
        res.end("method not allowed");
        return;
      }
      const u = new URL(req.url || "/", "http://" + HOST);
      let rel = decodeURIComponent(u.pathname);
      if (rel.includes("\0")) {
        res.writeHead(400);
        res.end("bad path");
        return;
      }
      if (rel === "/") rel = "/index.html";
      const abs = path.resolve(rootNorm, "." + rel);
      const rootWithSep = rootNorm.endsWith(path.sep)
        ? rootNorm
        : rootNorm + path.sep;
      if (abs !== rootNorm && !abs.startsWith(rootWithSep)) {
        res.writeHead(403);
        res.end("forbidden");
        return;
      }
      const relPosix = path.relative(rootNorm, abs).split(path.sep).join("/");
      const top = relPosix.split("/")[0];
      const blocked =
        BLOCKED_TOP.has(relPosix) ||
        top === "node_modules" ||
        top === ".electron-userdata" ||
        top === "assets" ||
        relPosix.startsWith(".desktop-s1") ||
        relPosix.startsWith(".desktop-s2") ||
        relPosix.endsWith(".preDesktopS2-20261021") ||
        relPosix.includes(".preDesktopS3-20261022") ||
        relPosix.startsWith(".desktop-s3");
      if (blocked) {
        res.writeHead(404);
        res.end("not found");
        return;
      }
      fs.stat(abs, (err, st) => {
        if (err || !st.isFile()) {
          res.writeHead(404);
          res.end("not found");
          return;
        }
        const ext = path.extname(abs).toLowerCase();
        res.writeHead(200, {
          "Content-Type": MIME[ext] || "application/octet-stream",
          "Cache-Control": "no-store",
          "X-Content-Type-Options": "nosniff",
          "Referrer-Policy": "no-referrer",
          "Content-Length": st.size,
        });
        if (req.method === "HEAD") {
          res.end();
          return;
        }
        fs.createReadStream(abs).pipe(res);
      });
    } catch (_e) {
      res.writeHead(500);
      res.end("error");
    }
  });
  server.on("connection", (sock) => {
    const addr = sock.remoteAddress || "";
    if (addr !== "127.0.0.1" && addr !== "::ffff:127.0.0.1" && addr !== "::1") {
      sock.destroy();
    }
  });
  return listen(server, PORT_START, PORT_TRIES).then((port) => ({
    server,
    port,
  }));
}

function isLoopbackUrl(raw) {
  try {
    const u = new URL(raw);
    if (u.protocol === "devtools:" || u.protocol === "chrome-extension:")
      return true;
    if (
      u.protocol !== "http:" &&
      u.protocol !== "https:" &&
      u.protocol !== "ws:" &&
      u.protocol !== "wss:"
    ) {
      return false;
    }
    return u.hostname === "127.0.0.1" || u.hostname === "localhost";
  } catch (_e) {
    return false;
  }
}

function probePortHttp(port) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: HOST, port: port, path: "/", timeout: 3000 },
      (res) => {
        let n = 0;
        res.on("data", (c) => {
          n += c.length;
        });
        res.on("end", () => {
          resolve({
            ok: res.statusCode === 200,
            status: res.statusCode,
            bytes: n,
          });
        });
      }
    );
    req.on("error", (e) => {
      resolve({ ok: false, error: String(e && e.message ? e.message : e) });
    });
    req.on("timeout", () => {
      req.destroy();
      resolve({ ok: false, error: "timeout" });
    });
  });
}

let serverRef = null;
let mainWindow = null;
let trayRef = null;
let quitting = false;

function stopServerSync() {
  if (!serverRef) return;
  try {
    serverRef.close();
  } catch (_e) {}
  serverRef = null;
  try {
    if (fs.existsSync(PORT_FILE)) fs.unlinkSync(PORT_FILE);
  } catch (_e) {}
}

function waitLoad(win, timeoutMs) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(
      () => reject(new Error("页面加载超时 " + timeoutMs + "ms（请确认静态服仍在）")),
      timeoutMs
    );
    win.webContents.once("did-finish-load", () => {
      clearTimeout(t);
      resolve();
    });
    win.webContents.once("did-fail-load", (_e, code, desc, url) => {
      clearTimeout(t);
      reject(
        new Error(
          "页面加载失败 code=" + code + " desc=" + desc + " url=" + url
        )
      );
    });
  });
}

function loadTrayIcon() {
  const pngPath = path.join(ROOT, "assets", "tray-demo.png");
  if (fs.existsSync(pngPath)) {
    const img = nativeImage.createFromPath(pngPath);
    if (!img.isEmpty()) return img.resize({ width: 16, height: 16 });
  }
  // 1x1 PNG fallback（演示用；非生产图标）
  const b64 =
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAFUlEQVQ4T2NkYGD4z0ABYBzVMKoaBgD9YQAB0qf0VwAAAABJRU5ErkJggg==";
  return nativeImage.createFromBuffer(Buffer.from(b64, "base64"));
}

function setupTray(win) {
  if (!TRAY_OPT_IN) {
    logInfo("托盘未启用（可选：set DESKTOP_S2_TRAY=1 或传 --tray；仍为演示／非生产）");
    return;
  }
  try {
    const icon = loadTrayIcon();
    trayRef = new Tray(icon);
    trayRef.setToolTip("Vaelin UI 演示壳 · DEMO · 非生产（可退出）");
    const menu = Menu.buildFromTemplate([
      {
        label: "显示演示窗（非生产）",
        click: () => {
          if (win && !win.isDestroyed()) {
            win.show();
            win.focus();
          }
        },
      },
      {
        label: "退出演示壳（关闭即停服 · 非生产）",
        click: () => {
          quitting = true;
          if (win && !win.isDestroyed()) win.close();
          else {
            stopServerSync();
            app.quit();
          }
        },
      },
    ]);
    trayRef.setContextMenu(menu);
    trayRef.on("double-click", () => {
      if (win && !win.isDestroyed()) {
        win.show();
        win.focus();
      }
    });
    logInfo("已启用轻量托盘（演示／非生产 · 非常驻生产服务 · 可退出）");
  } catch (e) {
    logErr("托盘初始化失败（继续无托盘）: " + String(e));
    trayRef = null;
  }
}


function loadWindowBounds() {
  try {
    if (!fs.existsSync(BOUNDS_FILE)) return null;
    const raw = JSON.parse(fs.readFileSync(BOUNDS_FILE, "utf8"));
    if (!raw || typeof raw !== "object") return null;
    const w = Number(raw.width);
    const h = Number(raw.height);
    const x = raw.x == null ? undefined : Number(raw.x);
    const y = raw.y == null ? undefined : Number(raw.y);
    if (!Number.isFinite(w) || !Number.isFinite(h) || w < 960 || h < 640) return null;
    const out = { width: Math.round(w), height: Math.round(h) };
    if (Number.isFinite(x) && Number.isFinite(y)) {
      out.x = Math.round(x);
      out.y = Math.round(y);
    }
    return out;
  } catch (_e) {
    return null;
  }
}

function saveWindowBounds(win) {
  try {
    if (!win || win.isDestroyed()) return;
    const b = win.getBounds();
    if (!fs.existsSync(USER_DATA_DIR)) fs.mkdirSync(USER_DATA_DIR, { recursive: true });
    fs.writeFileSync(
      BOUNDS_FILE,
      JSON.stringify(
        {
          width: b.width,
          height: b.height,
          x: b.x,
          y: b.y,
          note: "Desktop-S3 staging only · not %LocalAppData%\\hermes · demo ≠ production",
        },
        null,
        2
      ),
      "utf8"
    );
  } catch (e) {
    logErr("窗口几何保存失败（继续）: " + String(e));
  }
}

function showHardGateAbout() {
  const body =
    "Vaelin UI 演示壳 · Desktop-S3 · DEMO · 非生产\\n\\n" +
    HARD_GATE_LINES.join("\\n") +
    "\\n\\n本窗＠127.0.0.1:8766＝演示 stage，不是生产 Hermes 桌面。\\n假数据 fixture · 零接线生产 · 签 ≠ 启用。";
  dialog.showMessageBoxSync({
    type: "info",
    title: "Desktop-S3 硬闸／About（非生产）",
    message: "签 ≠ 启用 · DEMO · 非生产",
    detail: body,
    buttons: ["知道了"],
    noLink: true,
  });
}

async function createWindow(port) {
  const saved = loadWindowBounds();
  const win = new BrowserWindow({
    width: (saved && saved.width) || 1280,
    height: (saved && saved.height) || 840,
    ...(saved && Number.isFinite(saved.x) && Number.isFinite(saved.y)
      ? { x: saved.x, y: saved.y }
      : {}),
    minWidth: 960,
    minHeight: 640,
    show: true,
    title: WINDOW_TITLE,
    autoHideMenuBar: true,
    backgroundColor: "#1c1b19",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      spellcheck: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      devTools: false,
    },
  });
  mainWindow = win;
  win.setTitle(WINDOW_TITLE);
  win.on("page-title-updated", (e) => {
    e.preventDefault();
    win.setTitle(WINDOW_TITLE);
  });
  // 最小化：默认普通最小化到任务栏；托盘开启时隐藏到托盘（仍可退出，非常驻生产）
  win.on("minimize", (e) => {
    if (TRAY_OPT_IN && trayRef) {
      e.preventDefault();
      win.hide();
    }
  });
  win.on("close", (e) => {
    if (TRAY_OPT_IN && trayRef && !quitting && !SELFTEST) {
      // 托盘模式下点关闭＝退出演示（非最小化常驻）；明确退出以符合「禁常驻生产级服务」
      quitting = true;
    }
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (e, url) => {
    if (!isLoopbackUrl(url)) e.preventDefault();
  });
  win.webContents.on("will-redirect", (e, url) => {
    if (!isLoopbackUrl(url)) e.preventDefault();
  });
  const loadP = waitLoad(win, 20000);
  await win.loadURL("http://" + HOST + ":" + port + "/");
  await loadP;
  win.setTitle(WINDOW_TITLE);
  setupTray(win);
  let saveTimer = null;
  const scheduleSave = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => saveWindowBounds(win), 400);
  };
  win.on("resize", scheduleSave);
  win.on("move", scheduleSave);
  win.on("close", () => saveWindowBounds(win));
  try {
    const menu = Menu.buildFromTemplate([
      {
        label: "演示",
        submenu: [
          {
            label: "硬闸／About（签≠启用）",
            accelerator: "CmdOrCtrl+Shift+A",
            click: () => showHardGateAbout(),
          },
          {
            label: "键位帮助（F1）",
            accelerator: "F1",
            click: () => {
              if (win && !win.isDestroyed()) {
                win.webContents.executeJavaScript(
                  "window.__desktopS3ToggleHelp && window.__desktopS3ToggleHelp();",
                  true
                ).catch(() => {});
              }
            },
          },
          { type: "separator" },
          {
            label: "退出演示壳（关闭即停服）",
            accelerator: "CmdOrCtrl+Q",
            click: () => {
              quitting = true;
              if (win && !win.isDestroyed()) win.close();
              else {
                stopServerSync();
                app.quit();
              }
            },
          },
        ],
      },
    ]);
    Menu.setApplicationMenu(menu);
  } catch (e) {
    logErr("菜单初始化失败（继续）: " + String(e));
  }
  return win;
}

function installRequestGate() {
  session.defaultSession.webRequest.onBeforeRequest(
    { urls: ["*://*/*", "ws://*/*", "wss://*/*"] },
    (details, cb) => {
      cb({ cancel: !isLoopbackUrl(details.url) });
    }
  );
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, callback) => {
    callback(false);
  });
  session.defaultSession.setPermissionCheckHandler(() => false);
}

function evaluateDomSelftest(info, title, port, httpProbe) {
  const userDataPath = app.getPath("userData");
  const checks = {
    titleHasDemo:
      title.indexOf("演示") >= 0 ||
      title.indexOf("DEMO") >= 0 ||
      title.toLowerCase().indexOf("demo") >= 0,
    titleHasNonProd: title.indexOf("非生产") >= 0,
    titleHasDesktopS3: title.indexOf("Desktop-S3") >= 0,
    textHasNonProd: !!info.textHasNonProd,
    textHasDemo: !!info.textHasDemo,
    textHasZeroHermes: !!info.textHasZeroHermes,
    textHasSignNotEnable: !!info.textHasSignNotEnable,
    textHas8766NotHermes: !!info.textHas8766NotHermes,
    screensEnough: Array.isArray(info.screens) && info.screens.length >= MIN_SCREENS,
    portDefaultOrDoc: port >= PORT_START && port < PORT_START + PORT_TRIES,
    portNot8765Default: PORT_START === 8766,
    httpReachable: !!(httpProbe && httpProbe.ok),
    userDataInStaging:
      typeof userDataPath === "string" &&
      userDataPath.indexOf(".electron-userdata") >= 0 &&
      userDataPath.toLowerCase().indexOf("\\hermes") < 0 &&
      userDataPath.toLowerCase().indexOf("/hermes") < 0,
  };
  const failed = Object.keys(checks).filter((k) => !checks[k]);
  return { checks, failed, pass: failed.length === 0, userDataPath };
}

app.whenReady().then(async () => {
  installRequestGate();
  let started;
  try {
    started = await startServer();
  } catch (bindErr) {
    logErr(String(bindErr && bindErr.stack ? bindErr.stack : bindErr));
    if (SELFTEST_OUT) {
      try {
        fs.writeFileSync(
          SELFTEST_OUT,
          JSON.stringify(
            {
              ok: false,
              error: String(bindErr),
              stack: bindErr && bindErr.stack ? bindErr.stack : null,
            },
            null,
            2
          ),
          "utf8"
        );
      } catch (_e) {}
    }
    app.exit(1);
    return;
  }
  serverRef = started.server;
  try {
    fs.writeFileSync(PORT_FILE, String(started.port), "utf8");
  } catch (wErr) {
    logErr("写端口文件失败（继续）: " + String(wErr));
  }
  logInfo(
    "DEMO · 非生产 · http://" +
      HOST +
      ":" +
      started.port +
      "/ · 零 Hermes · 无公网遥测 · 关闭窗口即停服"
  );
  if (started.port !== PORT_START) {
    logInfo(
      "注意：实际端口为 " +
        started.port +
        "（默认 8766 被占用顺延；桌面默认仍非 8765）"
    );
  }

  const win = await createWindow(started.port);

  if (SELFTEST) {
    await new Promise((r) => setTimeout(r, 300));
    const info = await win.webContents.executeJavaScript(
      "(() => {" +
        "const text = document.body ? document.body.innerText : '';" +
        "const ids = Array.from(document.querySelectorAll('[id^=\"screen-\"]')).map(el => el.id);" +
        "const title = document.title;" +
        "const banner = document.querySelector('.np-text, .nonprod, [data-nonprod]');" +
        "return {" +
        "docTitle: title," +
        "textHasNonProd: text.indexOf('\u975e\u751f\u4ea7') >= 0," +
        "textHasDemo: text.indexOf('\u6f14\u793a') >= 0," +
        "textHasZeroHermes: text.indexOf('\u96f6 Hermes') >= 0 || text.indexOf('\u96f6\u63a5 Hermes') >= 0," +
        "textHasSignNotEnable: text.indexOf('\u7b7e\u2260\u542f\u7528') >= 0 || text.indexOf('\u7b7e \u2260 \u542f\u7528') >= 0 || text.indexOf('\u7b7e\u4e0d\u7b49\u4e8e\u542f\u7528') >= 0," +
        "textHas8766NotHermes: text.indexOf('8766') >= 0 && text.indexOf('Hermes') >= 0 && (text.indexOf('Hermes desktop') >= 0 || text.indexOf('\u2260') >= 0 || text.indexOf('≠') >= 0)," +
        "modes: ['\u6c27\u6c14','\u51ef\u6492','\u73a5'].filter(m => text.indexOf(m) >= 0)," +
        "gray: text.indexOf('\u7070\u6001') >= 0," +
        "screens: ids," +
        "screenCount: ids.length," +
        "bannerText: banner ? (banner.textContent || '').slice(0, 120) : null," +
        "len: text.length" +
        "};" +
      "})()",
      true
    );
    const httpProbe = await probePortHttp(started.port);
    const title = win.getTitle();
    const evaled = evaluateDomSelftest(info, title, started.port, httpProbe);
    const out = {
      ok: evaled.pass,
      stage: "Desktop-S3",
      title: title,
      port: started.port,
      url: "http://" + HOST + ":" + started.port + "/",
      defaultPort: PORT_START,
      httpProbe: httpProbe,
      info: info,
      checks: evaled.checks,
      failed: evaled.failed,
      trayOptIn: TRAY_OPT_IN,
      demoNotProduction: true,
      installNotEnable: true,
      signNotEnable: true,
      portNotHermesDesktop: true,
      userDataPath: evaled.userDataPath,
      hardGateLines: HARD_GATE_LINES,
    };
    if (SELFTEST_OUT) {
      fs.writeFileSync(SELFTEST_OUT, JSON.stringify(out, null, 2), "utf8");
    }
    if (SELFTEST_PNG) {
      try {
        const img = await win.webContents.capturePage();
        fs.writeFileSync(SELFTEST_PNG, img.toPNG());
      } catch (capErr) {
        process.stderr.write(
          "[Desktop-S3][selftest] capture skipped: " + String(capErr) + "\n"
        );
      }
    }
    process.stdout.write("[Desktop-S3][selftest] " + JSON.stringify(out) + "\n");
    quitting = true;
    setTimeout(() => {
      stopServerSync();
      app.exit(evaled.pass ? 0 : 2);
    }, 400);
  }
}).catch((err) => {
  const msg = err && err.stack ? err.stack : String(err);
  logErr(msg);
  if (SELFTEST_OUT) {
    try {
      fs.writeFileSync(
        SELFTEST_OUT,
        JSON.stringify({
          ok: false,
          error: String(err),
          stack: err && err.stack ? err.stack : null,
        }),
        "utf8"
      );
    } catch (_e) {}
  }
  stopServerSync();
  app.exit(1);
});

app.on("window-all-closed", () => {
  quitting = true;
  if (trayRef) {
    try {
      trayRef.destroy();
    } catch (_e) {}
    trayRef = null;
  }
  stopServerSync();
  app.quit();
});

app.on("before-quit", () => {
  quitting = true;
  if (trayRef) {
    try {
      trayRef.destroy();
    } catch (_e) {}
    trayRef = null;
  }
  stopServerSync();
});
