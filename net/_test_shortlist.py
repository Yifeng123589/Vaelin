# -*- coding: utf-8 -*-
"""_test_shortlist.py —— S3 验收测试（沙箱在系统 temp，零仓库写入）

覆盖（工程提炼 §2.1 / 精简版 §8.1）：
  1. 资格过滤：available=false 与文件不存在 → 不进候选（对组长不可见）
  2. 排序：score = weight^τ × bias；并列时按名稳定排序
  3. 权重三层取法：组长 weights 映射 > 节点自身 weight > 默认 0.3
  4. τ 生效：weight^τ
  5. 抽样：同 seed 可复现；ε=1 时必为均匀路径；空候选 → None
  6. CLI：--json 输出可解析、顺序正确
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import shortlist as sl  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [PASS] %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s  %s" % (name, detail))


def make_vault(tmp: Path) -> Path:
    vault = tmp / "vault"
    (vault / "00_组长").mkdir(parents=True)
    (vault / "20_角色").mkdir(parents=True)

    (vault / "00_组长" / "组长_日常.md").write_text(
        "---\ntype: agent\nform: lead\ntools: []\nrequires: {python: any}\n"
        "knows: [\"[[A]]\", \"[[B]]\", \"[[C]]\", \"[[D]]\", \"[[E]]\"]\n"
        "weights: {A: 0.5}\nversion: 1\n---\n\n# 组长_日常\n", encoding="utf-8")
    (vault / "20_角色" / "A.md").write_text(
        "---\ntype: agent\nform: character_card\ncapability: 写草稿\nweight: 0.8\nbias: 1.1\n"
        "available: true\n---\n\n# A\n", encoding="utf-8")
    (vault / "20_角色" / "B.md").write_text(
        "---\ntype: agent\nform: character_card\nweight: 0.3\navailable: true\n---\n\n# B\n",
        encoding="utf-8")
    (vault / "20_角色" / "C.md").write_text(
        "---\ntype: agent\nform: character_card\nweight: 0.9\navailable: false\n---\n\n# C\n",
        encoding="utf-8")
    (vault / "20_角色" / "D.md").write_text(
        "---\ntype: agent\nform: character_card\navailable: true\n---\n\n# D\n", encoding="utf-8")
    # E 故意不存在（只在 knows 里）
    return vault


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="shortlist_"))
    vault = make_vault(tmp)

    print("== 1/2/3. 资格过滤 + 排序 + 权重三层 ==")
    r = sl.build(vault, "组长_日常", tau=1.0, eps=0.1)
    names = [x["node"] for x in r["ranked"]]
    check("候选 = [A, B, D]", names == ["A", "B", "D"], str(names))
    excl = {e["node"]: e["reason"] for e in r["excluded"]}
    check("C 被资格取消", "C" in excl and "available" in excl["C"], str(excl))
    check("E 文件不存在", "E" in excl and "不存在" in excl["E"], str(excl))
    a = r["ranked"][0]
    check("A 用组长 weights 映射（0.5×1.1=0.55）", abs(a["score"] - 0.55) < 1e-6, str(a))
    b = [x for x in r["ranked"] if x["node"] == "B"][0]
    d = [x for x in r["ranked"] if x["node"] == "D"][0]
    check("B=0.3、D=默认 0.3（并列，B 先）", b["score"] == 0.3 and d["score"] == 0.3, str([b, d]))
    check("capability 透传（A=写草稿，D=None）", a.get("capability") == "写草稿" and d.get("capability") is None, str(a))

    print("== 4. τ 生效（去掉映射，用节点自身 weight）==")
    # 临时去掉组长 weights 行 → A 回到 0.8^2×1.1
    lead = vault / "00_组长" / "组长_日常.md"
    lead.write_text(lead.read_text(encoding="utf-8").replace("weights: {A: 0.5}\n", ""),
                    encoding="utf-8")
    r2 = sl.build(vault, "组长_日常", tau=2.0)
    a2 = r2["ranked"][0]
    check("A: 0.8^2×1.1 = 0.704", abs(a2["score"] - 0.704) < 1e-6, str(a2))

    print("== 3b. 权重映射：单数键 / 多行块 / 告警（审读 M6）==")
    lead = vault / "00_组长" / "组长_日常.md"
    lead.write_text("---\ntype: agent\nform: lead\n"
                    "knows: [\"[[A]]\", \"[[B]]\"]\n"
                    "weight: {A: 0.7}\nversion: 1\n---\n\n# 组长\n", encoding="utf-8")
    r5 = sl.build(vault, "组长_日常")
    a5 = [x for x in r5["ranked"] if x["node"] == "A"][0]
    check("单数键 weight 映射生效（0.7×1.1=0.77）", abs(a5["score"] - 0.77) < 1e-6, str(a5))
    lead.write_text("---\ntype: agent\nform: lead\n"
                    "knows: [\"[[A]]\", \"[[B]]\"]\n"
                    "weight:\n  A: 0.6\n  B: 0.4\nversion: 1\n---\n\n# 组长\n", encoding="utf-8")
    r6 = sl.build(vault, "组长_日常")
    a6 = [x for x in r6["ranked"] if x["node"] == "A"][0]
    b6 = [x for x in r6["ranked"] if x["node"] == "B"][0]
    check("多行块映射生效（A=0.6×1.1、B=0.4）",
          abs(a6["score"] - 0.66) < 1e-6 and abs(b6["score"] - 0.4) < 1e-6, str([a6, b6]))
    check("有映射 → 无告警", r6.get("warnings") == [], str(r6.get("warnings")))
    lead.write_text("---\ntype: agent\nform: lead\nknows: [\"[[A]]\"]\nversion: 1\n---\n\n# 组长\n",
                    encoding="utf-8")
    r7 = sl.build(vault, "组长_日常")
    check("无映射 → 告警出现（防静默降级）", bool(r7.get("warnings")), str(r7.get("warnings")))
    # 恢复 section 4 之后的组长文件形态（knows A–E、无映射），供后续小节使用
    lead.write_text("---\ntype: agent\nform: lead\ntools: []\nrequires: {python: any}\n"
                    "knows: [\"[[A]]\", \"[[B]]\", \"[[C]]\", \"[[D]]\", \"[[E]]\"]\n"
                    "version: 1\n---\n\n# 组长_日常\n", encoding="utf-8")

    print("== 5. 抽样可复现 + 空候选 ==")
    p1 = sl.build(vault, "组长_日常", eps=0.0, seed=7, with_pick=True)["pick"]
    p2 = sl.build(vault, "组长_日常", eps=0.0, seed=7, with_pick=True)["pick"]
    check("同 seed 两次一致", p1 == p2, "%s vs %s" % (p1, p2))
    p3 = sl.build(vault, "组长_日常", eps=1.0, seed=7, with_pick=True)["pick"]
    check("ε=1 → 必在候选中且走均匀路径", p3["node"] in names and "ε" in p3["how"], str(p3))
    (vault / "00_组长" / "组长_日常.md").write_text(
        "---\ntype: agent\nform: lead\nknows: []\nversion: 1\n---\n\n# 空\n", encoding="utf-8")
    r3 = sl.build(vault, "组长_日常", with_pick=True)
    check("空候选 → ranked=[] 且 pick=None", r3["ranked"] == [] and r3["pick"] is None, str(r3))

    print("== 6. CLI --json ==")
    (vault / "00_组长" / "组长_日常.md").write_text(
        "---\ntype: agent\nform: lead\nknows: [\"[[A]]\", \"[[B]]\"]\nversion: 1\n---\n\n# 组长\n",
        encoding="utf-8")
    out = tmp / "shortlist.json"
    r4 = subprocess.run([sys.executable, str(HERE / "shortlist.py"), str(vault),
                         "--lead", "组长_日常", "--json", "--pick", "--seed", "3", "--out", str(out)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok_cli = False
    try:
        data = json.loads(r4.stdout)
        ok_cli = data["ranked"][0]["node"] == "A" and out.exists()
    except Exception as exc:
        detail = "%s / %s" % (r4.stdout[:200], r4.stderr[:200])
    else:
        detail = ""
    check("CLI 输出 JSON 且头部为 A、--out 落盘", ok_cli, detail)

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
