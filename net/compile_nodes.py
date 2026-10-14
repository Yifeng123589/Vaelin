# -*- coding: utf-8 -*-
"""compile_nodes.py —— 关系网 v0.5 · 资格与偏置编译（§5.5）

读 env_snapshot.json + vault 节点 frontmatter 的 requires →
  不可用 → available: false（踢出候选集）
  可用   → available: true，bias 按规则编译（乘性、默认 1.0、edge 系且 Edge 为默认浏览器 → 1.1、钳 [0.9, 1.1]）
探测清单 = 各节点 requires 的并集（★v1.14）；复跑 probe + compile 整体重算。

frontmatter 采用**外科手术式**行级读写：只增改 available/bias 两行，其余原样保留——
为将来 Obsidian 人机共写留余地（机器字段将来迁移 _relations.json 旁车，见审读意见）。

写路径（2026-09-29 审读 H4）：主流程（带 vault 参数）一律走 vault_write 网关
（文件锁 + 原子写）；`git=False`——vault 独立 git 尚未启用（防嵌套主仓，v1.14 迁移时改 True）。
只编译 `type: agent` 的节点（审读 L7：剧本/记忆等不再被写入 available/bias 噪音）。

用法：
  python compile_nodes.py <vault_dir> [env_snapshot.json]
  python compile_nodes.py --scaffold [vault_dir]   # 建 §2 种子 vault（首次用）
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import vault_write as vw  # noqa: E402

try:  # Windows 控制台默认 GBK：防 ✓/✗ 打印崩溃（S1 适配）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BIAS_MIN, BIAS_MAX = 0.9, 1.1
BIAS_DEFAULT = 1.0
BIAS_EDGE_DEFAULT = 1.1

SEED_NODES = {
    "_index.md": "---\ntype: index\n---\n\n# 总目录（MOC）\n\n组长先读我。节点长大后再补分区索引。\n",
    "00_组长/组长_日常.md": """---
type: agent
form: lead
dept: 00_组长
tools: []
requires: {python: any}
model: null
knows: ["[[陪伴者]]", "[[助理]]", "[[论文检索员]]"]
version: 1
---

# 组长_日常

（冷启动种子：职责=接单→查网选人→定工作流→分发。决策=纯函数 f(vault, workflow_log, 任务单, seed)，无会话上下文。待你手写细化。）
""",
    "10_专家/论文检索员.md": """---
type: agent
form: real_subagent
dept: 10_专家
tools: [web_search]
requires: {python: any, browser: any}
model: flash
knows: ["[[组长_日常]]"]
version: 1
---

# 论文检索员

（真子智能体位：独立会话跑检索。待你手写细化。）
""",
    "20_角色/陪伴者.md": """---
type: agent
form: character_card
dept: 20_角色
tools: []
requires: {python: any}
model: null
knows: ["[[组长_日常]]"]
version: 1
---

# 陪伴者

（角色卡：对应回复层的主动陪伴。⚠️ 角色卡必须带不同的工具清单与剧本——干不同的活，不是换嗓音。待你手写细化。）
""",
    "20_角色/助理.md": """---
type: agent
form: character_card
dept: 20_角色
tools: [file_write]
requires: {python: any}
model: null
knows: ["[[组长_日常]]"]
version: 1
---

# 助理

（角色卡：任务型日常协助。待你手写细化。）
""",
}


def scaffold(vault: Path) -> None:
    for rel, content in SEED_NODES.items():
        f = vault / rel
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
    for d in ("30_剧本", "40_经验", "90_归档"):
        (vault / d).mkdir(parents=True, exist_ok=True)
    print(f"seed vault scaffolded: {vault}")


def split_frontmatter(text: str):
    """返回 (frontmatter行列表, 其余全文)。无 frontmatter 返回 (None, 原文)。"""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "".join(lines[i + 1:])
    return None, text


def get_val(fm_lines: list[str], key: str):
    for ln in fm_lines:
        m = re.match(rf"^{key}\s*:\s*(.+?)\s*$", ln)
        if m:
            return m.group(1)
    return None


def requires_of(fm_lines: list[str]) -> dict:
    raw = get_val(fm_lines, "requires")
    if not raw:
        return {}
    pairs = re.findall(r"(\w+)\s*:\s*([\w.]+)", raw.strip("{} "))
    return {k: v for k, v in pairs}


def resolve(require: dict, env: dict):
    """返回 (available: bool, bias: float)。资格走 available 门，偏好走 bias。"""
    for key, want in require.items():
        if key == "browser":
            have = [b for b in ("edge", "chrome") if env.get(b, {}).get("available")]
            if want == "any":
                ok = bool(have)
            else:
                ok = want in have
        elif key == "python":
            ok = bool(env.get("python", {}).get("available"))
        elif key == "venv":
            ok = bool(env.get("venv", {}).get("available"))
        else:
            ok = bool(env.get(key, {}).get("available"))
        if not ok:
            return False, BIAS_DEFAULT
    bias = BIAS_DEFAULT
    if require.get("browser") == "edge" and env.get("default_browser") == "edge":
        bias = BIAS_EDGE_DEFAULT
    return True, max(BIAS_MIN, min(BIAS_MAX, bias))


def upsert_line(fm_lines: list[str], key: str, value: str) -> list[str]:
    pat = re.compile(rf"^{key}\s*:")
    for i, ln in enumerate(fm_lines):
        if pat.match(ln):
            fm_lines[i] = f"{key}: {value}\n"
            return fm_lines
    fm_lines.append(f"{key}: {value}\n")
    return fm_lines


def compile_node(path: Path, env: dict, vault: Path | None = None):
    """编译单个节点。vault 非空 → 写走 vault_write 网关（锁+原子写）；否则直写（独立/测试用）。
    只处理 `type: agent`（index/剧本/记忆等一律跳过）。"""
    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        return None
    if (get_val(fm, "type") or "").strip() != "agent":
        return None  # 审读 L7：非 agent 节点不写 available/bias
    require = requires_of(fm)
    available, bias = resolve(require, env)
    fm = upsert_line(fm, "available", "true" if available else "false")
    fm = upsert_line(fm, "bias", f"{bias:.2f}" if available else f"{BIAS_DEFAULT:.2f}")
    new_text = "---\n" + "".join(fm) + "---\n" + body
    if vault is not None:
        rel = str(Path(path).resolve().relative_to(Path(vault).resolve()))
        # H4：单一写者——走网关（v0.5 暂不启 vault 独立 git：git=False，防嵌套主仓）
        vw.write_node(Path(vault), rel, new_text, reason="compile", actor="compile", git=False)
    else:
        path.write_text(new_text, encoding="utf-8")
    return {"node": path.name, "available": available, "bias": bias, "requires": require}


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if args and args[0] == "--scaffold":
        vault = Path(args[1]) if len(args) > 1 else Path.home() / "Desktop" / "agent_vault"
        scaffold(vault)
        return 0
    vault = Path(args[0]) if args else Path.home() / "Desktop" / "agent_vault"
    snap_path = Path(args[1]) if len(args) > 1 else Path(__file__).parent / "env_snapshot.json"
    if not snap_path.exists():
        print(f"env_snapshot 不存在（先跑 probe_env.py）：{snap_path}")
        return 1
    env = json.loads(snap_path.read_text(encoding="utf-8"))
    results = []
    for md in sorted(vault.rglob("*.md")):
        r = compile_node(md, env, vault=vault)
        if r:
            results.append(r)
    print(f"编译完成：{len(results)} 个节点（vault={vault}，快照 ts={env.get('ts')}）")
    for r in results:
        flag = "✓" if r["available"] else "✗"
        print(f"  [{flag}] {r['node']:<24} bias={r['bias']:.2f}  requires={r['requires']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
