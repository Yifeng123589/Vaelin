"use strict";
/** Desktop-S2 selftest JSON checker · DEMO · 非生产 · 零 Hermes */
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
console.log("[selftest_check] title:", data.title);
console.log("[selftest_check] port:", data.port, "default:", data.defaultPort);
console.log("[selftest_check] screens:", data.info && data.info.screenCount);
console.log("[selftest_check] http:", JSON.stringify(data.httpProbe));
console.log("[selftest_check] checks:", JSON.stringify(checks));
if (!data.ok || failed.length) {
  console.error("[selftest_check] FAIL keys:", failed.join(", ") || "(ok=false)");
  process.exit(2);
}
if (data.defaultPort !== 8766) {
  console.error("[selftest_check] FAIL: defaultPort 必须为 8766");
  process.exit(2);
}
console.log("[selftest_check] PASS");
process.exit(0);
