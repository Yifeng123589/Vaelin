#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""shortlist.py —— 关系网 · S3 短名单生成器

规则（精简版 §8.1 / 工程提炼 §2.1）：
  短名单 = 组长的 knows ∩ available  →  score = weight^τ × bias  →  排序 + ε 探索
  · 资格走 available 门（不可用节点对组长不可见）；偏好走 bias（乘性，编译产出）
  · 选择语义：P(选 B) ∝ weight^τ × bias；另有 ε 概率均匀随机挑一个（防赢家通吃）
  · 权重取法（v0.5 简化，注释留档）：① 组长 frontmatter 的出边映射 `weight`
    （设计 v1.11 B6 定稿键；兼容旧键 `weights`；单行 {A: 0.5} 与多行块均可）
    → ② 节点自身 weight → ③ 默认 0.3（认识但没合作过）；全默认时输出 warnings 告警（审读 M6）

用法：
  python shortlist.py <vault_dir> [--lead 组长_日常] [--tau 1.0] [--eps 0.1]
                      [--seed N] [--pick] [--json] [--out FILE]

输出（--json 或 --out）：{lead, tau, eps, ranked:[{node,weight,bias,score}], excluded:[{node,reason}], pick?}
本脚本只产出候选与抽样，不写 vault（单一写者原则）。
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

try:  # Windows 控制台默认 GBK：统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from compile_nodes import split_frontmatter, get_val  # noqa: E402

DEFAULT_WEIGHT = 0.3   # 认识但没合作过（设计 §8.1）
DEFAULT_BIAS = 1.0


def parse_knows(fm_lines: list[str]) -> list[str]:
    raw = get_val(fm_lines, "knows") or ""
    names = re.findall(r"\[\[([^\]|]+)\]\]", raw)
    if not names:
        names = [s.strip().strip("\"'") for s in raw.strip("[]").split(",")]
    return [n.strip() for n in names if n.strip()]


def _parse_map_pairs(raw: str) -> dict:
    out: dict[str, float] = {}
    for k, v in re.findall(r"([^,\s{}]+)\s*:\s*([0-9]*\.?[0-9]+)", raw or ""):
        try:
            out[k.strip().strip("\"'")] = float(v)
        except ValueError:
            pass
    return out


def _parse_block_map(fm_lines: list[str]) -> dict:
    """多行块形态：
        weight:
          陪伴者: 0.8
          助理: 0.5
    """
    out: dict[str, float] = {}
    collecting = False
    for raw_ln in fm_lines:
        ln = raw_ln.rstrip("\r\n")
        if not collecting:
            if re.match(r"^\s*(?:weight|weights)\s*:\s*$", ln):
                collecting = True
            continue
        m = re.match(r"^\s+([^:#]+?)\s*:\s*([0-9]*\.?[0-9]+)\s*$", ln)
        if m:
            out[m.group(1).strip().strip("\"'")] = float(m.group(2))
            continue
        if ln.strip() == "" or ln.startswith((" ", "\t")):
            continue            # 空行/其它缩进行：块内继续
        collecting = False      # 顶层新键 → 块结束
    return out


def parse_weights_map(fm_lines: list[str]) -> dict:
    """组长出边权重映射。设计定稿键 = `weight`（v1.11 B6：与 knows 同向、⊆knows）；
    兼容旧键 `weights`。单行与多行块均可（审读 M6：get_val 只读单行值，多行块需专门解析）。"""
    raw = get_val(fm_lines, "weight")
    if raw is None:
        raw = get_val(fm_lines, "weights")
    out = _parse_map_pairs(raw) if raw else {}
    if not out:
        out = _parse_block_map(fm_lines)
    return out


def parse_bool(raw, default: bool = True) -> bool:
    if raw is None:
        return default
    return str(raw).strip().strip("\"'").lower() in ("true", "1", "yes")


def find_nodes(vault: Path) -> dict[str, Path]:
    nodes: dict[str, Path] = {}
    for md in sorted(vault.rglob("*.md")):
        try:
            fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        except Exception:
            continue
        if fm is None:
            continue
        if (get_val(fm, "type") or "").strip() == "index":
            continue
        nodes.setdefault(md.stem, md)
    return nodes


def _read_fm(path: Path) -> list[str]:
    fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return fm or []


def pick(ranked: list[dict], eps: float, rng: random.Random):
    if not ranked:
        return None
    if rng.random() < eps:
        return {"node": rng.choice(ranked)["node"], "how": "ε 探索（均匀随机）"}
    total = sum(r["score"] for r in ranked) or 1.0
    x = rng.random() * total
    acc = 0.0
    for r in ranked:
        acc += r["score"]
        if x <= acc:
            return {"node": r["node"], "how": "加权抽样（P ∝ weight^τ × bias）"}
    return {"node": ranked[-1]["node"], "how": "加权抽样（尾）"}


def build(vault: Path, lead_name: str, tau: float = 1.0, eps: float = 0.1,
          seed=None, with_pick: bool = False) -> dict:
    nodes = find_nodes(vault)
    if lead_name not in nodes:
        raise SystemExit("找不到组长节点: %s（vault=%s）" % (lead_name, vault))
    lead_fm = _read_fm(nodes[lead_name])
    knows = parse_knows(lead_fm)
    wmap = parse_weights_map(lead_fm)

    ranked, excluded = [], []
    for name in knows:
        if name == lead_name:
            continue
        if name not in nodes:
            excluded.append({"node": name, "reason": "文件不存在"})
            continue
        fm = _read_fm(nodes[name])
        if not parse_bool(get_val(fm, "available"), default=True):
            excluded.append({"node": name, "reason": "available=false（资格取消）"})
            continue
        w = wmap.get(name)
        if w is None:
            raw_w = get_val(fm, "weight")
            try:
                w = float(str(raw_w).strip().strip("\"'")) if raw_w is not None else DEFAULT_WEIGHT
            except ValueError:
                w = DEFAULT_WEIGHT
        try:
            bias = float(str(get_val(fm, "bias") or DEFAULT_BIAS).strip().strip("\"'"))
        except ValueError:
            bias = DEFAULT_BIAS
        cap = str(get_val(fm, "capability") or "").strip().strip("\"'")
        score = (max(0.0, w) ** float(tau)) * bias
        ranked.append({"node": name, "weight": round(w, 4), "bias": round(bias, 4),
                       "score": round(score, 6), "capability": cap or None})

    ranked.sort(key=lambda r: (-r["score"], r["node"]))
    warnings: list[str] = []
    if not wmap:
        warnings.append("未找到组长出边权重映射（weight/weights）：候选权重回退到节点自身 "
                        "weight / 默认 %.1f（审读 M6 告警）" % DEFAULT_WEIGHT)
    result = {"lead": lead_name, "tau": tau, "eps": eps,
              "ranked": ranked, "excluded": excluded, "warnings": warnings}
    if with_pick:
        rng = random.Random(seed)
        result["pick"] = pick(ranked, eps, rng)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--lead", default="组长_日常")
    ap.add_argument("--tau", type=float, default=1.0)
    ap.add_argument("--eps", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--pick", action="store_true", help="附带一次选择抽样（可复现：--seed）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None, help="把结果 JSON 写入文件（给组长注入用）")
    args = ap.parse_args()

    result = build(Path(args.vault), args.lead, tau=args.tau, eps=args.eps,
                   seed=args.seed, with_pick=args.pick)

    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("短名单 · lead=%s · tau=%s · eps=%s" % (result["lead"], result["tau"], result["eps"]))
    for w in result.get("warnings", []):
        print("  ⚠ %s" % w)
    if not result["ranked"]:
        print("  （空——没有可见候选）")
    for i, r in enumerate(result["ranked"], 1):
        cap = ("｜%s" % r["capability"]) if r.get("capability") else ""
        print("  %d. %-10s weight=%.2f bias=%.2f score=%.3f%s" %
              (i, r["node"], r["weight"], r["bias"], r["score"], cap))
    for e in result["excluded"]:
        print("  排除: %s（%s）" % (e["node"], e["reason"]))
    if "pick" in result and result["pick"]:
        print("  pick → %s（%s）" % (result["pick"]["node"], result["pick"]["how"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
