# -*- coding: utf-8 -*-
"""_test_env_compile.py —— 关系网 v0.5 验收（§13.5）：探测编译管线，沙箱隔离。
ⓝ 已随关系网归档进 net/（设计暂缓，主线=情绪模块 B3）。"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # 本文件已移入 net/
import compile_nodes as cn  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" —— {detail}" if detail else ""))


NODE = """---
type: agent
form: character_card
dept: 20_角色
tools: []
requires: {browser: %s}
version: 1
---

# 测试节点
"""

FIXTURE_ENV = {
    "schema": "env-snapshot/v1", "ts": "2026-09-27T00:00:00",
    "python": {"available": True, "path": "F:/python.exe"},
    "venv": {"available": False, "path": None},
    "edge": {"available": True, "path": "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"},
    "chrome": {"available": False, "path": None},
    "default_browser": "edge",
}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="envcompile_"))
    (tmp / "20_角色").mkdir(parents=True)
    for name, browser in [("chrome需要者.md", "chrome"), ("edge需要者.md", "edge"), ("任意浏览器.md", "any")]:
        (tmp / "20_角色" / name).write_text(NODE % browser, encoding="utf-8")
    (tmp / "未知依赖.md").write_text(
        NODE.replace("{browser: %s}", "{quantum_computer: yes}"), encoding="utf-8")

    print("── 资格与偏置编译 ──")
    r1 = cn.compile_node(tmp / "20_角色" / "chrome需要者.md", FIXTURE_ENV)
    check("chrome 缺席 → 资格取消（available=false）", r1["available"] is False, str(r1))
    r2 = cn.compile_node(tmp / "20_角色" / "edge需要者.md", FIXTURE_ENV)
    check("edge 在且为默认浏览器 → bias 1.10", r2["available"] is True and abs(r2["bias"] - 1.10) < 1e-9)
    r3 = cn.compile_node(tmp / "20_角色" / "任意浏览器.md", FIXTURE_ENV)
    check("browser:any → 可用，bias 1.00（非 edge 系不加成）",
          r3["available"] is True and abs(r3["bias"] - 1.00) < 1e-9)
    r4 = cn.compile_node(tmp / "未知依赖.md", FIXTURE_ENV)
    check("探测清单外的依赖 → 不可用（清单=requires 并集的失败模式防护）", r4["available"] is False)

    print("── 幂等性 ──")
    cn.compile_node(tmp / "20_角色" / "edge需要者.md", FIXTURE_ENV)
    text2 = (tmp / "20_角色" / "edge需要者.md").read_text(encoding="utf-8")
    check("复跑不重复插行（available/bias 各一行）",
          text2.count("available:") == 1 and text2.count("bias:") == 1)
    check("frontmatter 外正文原样保留", "# 测试节点" in text2)

    print("── 网关写路径 + 类型过滤（审读 H4/L7）──")
    r5 = cn.compile_node(tmp / "20_角色" / "edge需要者.md", FIXTURE_ENV, vault=tmp)
    check("走网关写成功（无 .git 初始化/无锁残留）",
          r5 is not None and not (tmp / ".git").exists() and not (tmp / ".vault_lock").exists(), str(r5))
    script_node = tmp / "20_角色" / "剧本节点.md"
    script_node.write_text("---\ntype: script\nrequires: {browser: any}\n---\n\n# 剧本\n", encoding="utf-8")
    r6 = cn.compile_node(script_node, FIXTURE_ENV, vault=tmp)
    check("非 agent 节点跳过（不写 available/bias）",
          r6 is None and "available:" not in script_node.read_text(encoding="utf-8"), str(r6))

    print("── 脚手架 ──")
    vault = tmp / "seed_vault"
    cn.scaffold(vault)
    for d in ("00_组长", "10_专家", "20_角色", "30_剧本", "40_经验", "90_归档"):
        check(f"目录存在：{d}", (vault / d).is_dir())
    check("组长节点存在", (vault / "00_组长" / "组长_日常.md").is_file())

    print()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"结果：{passed}/{len(RESULTS)} 通过")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
