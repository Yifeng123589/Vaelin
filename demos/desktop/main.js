"use strict";

/**
 * Vaelin UI 演示壳 · Desktop-S1
 * DEMO · 非生产 · 假数据 · 零 Hermes
 * demo ≠ production
 *
 * 只提供本目录内拷贝的 S9 静态资源（index.html / css / js / data）。
 * 内嵌静态服只绑定 127.0.0.1。不调用 crashReporter、不装 autoUpdater、
 * 关闭 Chromium 后台联网／组件更新／指标上报。
 */

const { app, BrowserWindow, session } = require("electron");
const http = require("http");
const fs = require("fs");
const path = require("path");

const HOST = "127.0.0.1";
const PORT_START = 8766;
const PORT_TRIES = 10;
const WINDOW_TITLE = "Vaelin UI 演示壳 · Desktop-S1 · DEMO · 非生产";
const ROOT = __dirname;

app.disableHardwareAcceleration();
app.commandLine.appendSwitch("disable-gpu");
app.commandLine.appendSwitch("disable-gpu-compositing");
app.commandLine.appendSwitch("disable-software-rasterizer");
app.setName("Vaelin UI Demo Desktop-S1");
app.setPath("userData", path.join(ROOT, ".electron-userdata"));

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
  "README.md",
  ".gitignore",
]);

function listen(server, port, left) {
  return new Promise((resolve, reject) => {
    const onError = (err) => {
      server.removeListener("error", onError);
      if (err && err.code === "EADDRINUSE" && left > 0) {
        resolve(listen(server, port + 1, left - 1));
        return;
      }
      reject(err);
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
      const rootWithSep = rootNorm.endsWith(path.sep) ? rootNorm : rootNorm + path.sep;
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
        relPosix.startsWith(".desktop-s1");
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
  return listen(server, PORT_START, PORT_TRIES).then((port) => ({ server, port }));
}

function isLoopbackUrl(raw) {
  try {
    const u = new URL(raw);
    if (u.protocol === "devtools:" || u.protocol === "chrome-extension:") return true;
    if (u.protocol !== "http:" && u.protocol !== "https:" && u.protocol !== "ws:" && u.protocol !== "wss:") {
      return false;
    }
    return u.hostname === "127.0.0.1" || u.hostname === "localhost";
  } catch (_e) {
    return false;
  }
}

let serverRef = null;

function waitLoad(win, timeoutMs) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error("load timeout")), timeoutMs);
    win.webContents.once("did-finish-load", () => {
      clearTimeout(t);
      resolve();
    });
    win.webContents.once("did-fail-load", (_e, code, desc, url) => {
      clearTimeout(t);
      reject(new Error("did-fail-load " + code + " " + desc + " " + url));
    });
  });
}

async function createWindow(port) {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
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
  win.setTitle(WINDOW_TITLE);
  win.on("page-title-updated", (e) => {
    e.preventDefault();
    win.setTitle(WINDOW_TITLE);
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

app.whenReady().then(async () => {
  installRequestGate();
  const started = await startServer();
  serverRef = started.server;
  fs.writeFileSync(path.join(ROOT, ".desktop-s1-port"), String(started.port), "utf8");
  process.stdout.write(
    "[Desktop-S1] DEMO · 非生产 · http://" + HOST + ":" + started.port + "/ · 零 Hermes · 无公网遥测\n"
  );
  const win = await createWindow(started.port);

  if (process.env.DESKTOP_S1_SELFTEST === "1") {
    const info = await win.webContents.executeJavaScript(
      "(() => {" +
        "const text = document.body ? document.body.innerText : '';" +
        "const ids = Array.from(document.querySelectorAll('[id^=\"screen-\"]')).map(el => el.id);" +
        "const title = document.title;" +
        "return {" +
        "docTitle: title," +
        "textHasNonProd: text.indexOf('\u975e\u751f\u4ea7') >= 0," +
        "textHasDemo: text.indexOf('\u6f14\u793a') >= 0," +
        "textHasZeroHermes: text.indexOf('\u96f6 Hermes') >= 0 || text.indexOf('\u96f6\u63a5 Hermes') >= 0," +
        "modes: ['\u6c27\u6c14','\u51ef\u6492','\u73a5'].filter(m => text.indexOf(m) >= 0)," +
        "gray: text.indexOf('\u7070\u6001') >= 0," +
        "screens: ids," +
        "len: text.length" +
        "};" +
      "})()",
      true
    );
    const out = {
      title: win.getTitle(),
      port: started.port,
      url: "http://" + HOST + ":" + started.port + "/",
      info: info,
    };
    if (process.env.DESKTOP_S1_SELFTEST_OUT) {
      fs.writeFileSync(process.env.DESKTOP_S1_SELFTEST_OUT, JSON.stringify(out, null, 2), "utf8");
    }
    const shot = process.env.DESKTOP_S1_SELFTEST_PNG;
    if (shot) {
      try {
        const img = await win.webContents.capturePage();
        fs.writeFileSync(shot, img.toPNG());
      } catch (capErr) {
        process.stderr.write("[Desktop-S1][selftest] capture skipped: " + String(capErr) + "\n");
      }
    }
    process.stdout.write("[Desktop-S1][selftest] " + JSON.stringify(out) + "\n");
    setTimeout(() => app.exit(0), 400);
  }
}).catch((err) => {
  const msg = err && err.stack ? err.stack : String(err);
  process.stderr.write("[Desktop-S1][失败] " + msg + "\n");
  if (process.env.DESKTOP_S1_SELFTEST_OUT) {
    try {
      fs.writeFileSync(
        process.env.DESKTOP_S1_SELFTEST_OUT,
        JSON.stringify({ error: String(err), stack: err && err.stack ? err.stack : null }),
        "utf8"
      );
    } catch (_e) {}
  }
  app.exit(1);
});

app.on("window-all-closed", () => {
  if (serverRef) serverRef.close();
  app.quit();
});

app.on("before-quit", () => {
  if (serverRef) {
    try {
      serverRef.close();
    } catch (_e) {}
  }
});
