"use strict";
/** Desktop-S3 + H-SBX-A selftest JSON checker · 沙箱真启用 · ≠ 生产 */
const fs = require("fs");
const path = process.argv[2] || "selftest-out.json";
let raw;
try {
  raw = fs.readFileSync(path, "utf8");
} catch (e) {
  console.error("[selftest_check] 读失败:", path, String(e));
  process.exit(1);
}
let data;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.error("[selftest_check] JSON 无效:", String(e));
  process.exit(1);
}
if (data.error && !data.ok) {
  console.error("[selftest_check] FAIL runtime:", data.error);
  process.exit(2);
}
const failed = Array.isArray(data.failed) ? data.failed : [];
const checks = data.checks || {};
console.log("[selftest_check] stage:", data.stage);
console.log("[selftest_check] title:", data.title);
console.log("[selftest_check] port:", data.port, "default:", data.defaultPort);
console.log("[selftest_check] screens:", data.info && data.info.screenCount);
console.log("[selftest_check] http:", JSON.stringify(data.httpProbe));
console.log("[selftest_check] userData:", data.userDataPath);
console.log("[selftest_check] hermesSandboxHome:", data.hermesSandboxHome);
console.log("[selftest_check] hermesScheme:", data.hermesScheme);
console.log("[selftest_check] productionHermesTouched:", data.productionHermesTouched);
console.log("[selftest_check] checks:", JSON.stringify(checks));
if (!data.ok || failed.length) {
  console.error("[selftest_check] FAIL keys:", failed.join(", ") || "(ok=false)");
  process.exit(2);
}
if (data.defaultPort !== 8766) {
  console.error("[selftest_check] FAIL: defaultPort 必须为 8766");
  process.exit(2);
}
if (!data.title || data.title.indexOf("Desktop-S3") < 0) {
  console.error("[selftest_check] FAIL: 标题须含 Desktop-S3");
  process.exit(2);
}
if (!checks.titleHasDesktopS3 || !checks.textHasSignNotEnable || !checks.userDataInStaging) {
  console.error("[selftest_check] FAIL: S3 硬闸／标题／userData 条件未过");
  process.exit(2);
}
if (!checks.hermesHomeIsSandbox || !checks.hermesHomeNotProd || !checks.sandboxMarkerPresent) {
  console.error("[selftest_check] FAIL: 沙箱 HERMES_HOME／marker 条件未过");
  process.exit(2);
}
if (checks.textHasSandboxGate === false) {
  console.error("[selftest_check] FAIL: 硬闸未含沙箱口径");
  process.exit(2);
}
const ud = String(data.userDataPath || "");
if (/[\\/]hermes([\\/]|$)/i.test(ud)) {
  console.error("[selftest_check] FAIL: userData 路径含有 hermes 路径");
  process.exit(2);
}
const hh = String(data.hermesSandboxHome || "");
if (!hh || /appdata[\\/]local[\\/]hermes/i.test(hh)) {
  console.error("[selftest_check] FAIL: hermesSandboxHome 无效或指向生产");
  process.exit(2);
}
if (data.productionHermesTouched) {
  console.error("[selftest_check] FAIL: productionHermesTouched 必须为 false");
  process.exit(2);
}
console.log("[selftest_check] PASS Desktop-S3 + H-SBX-A sandbox");
process.exit(0);
