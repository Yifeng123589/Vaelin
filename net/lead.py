#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""lead.py —— 关系网 · S4 组长手动闭环（v0.5）

流程：任务单 → 组装输入（短名单/剧本/日志摘录）→ 组长模型 → 工作流单 JSON → 校验 → 落盘+落账
校验（写时校验，设计 §10）：to 必须出自短名单；步骤 1..n 有序；fallback 必填；wf/seed 必填；
wf 白名单 `^[\\w\\-]{1,64}$`（审读 L2：防 `--wf ../../x` 写出目录）。
日志：把首步 dispatch 落 workflow_log.jsonl（from = 组长节点名，默认 组长_日常；审读 L5。
执行期的后续脚步骤由 v1 的 hook 接续落账）。
重试：真模型路径校验失败自动重试（默认 1 次；审读 L3）；mock/call_fn 路径不重试。

用法：
  python lead.py --vault fixtures/vault_seed --task "把这页文档整理成三条修改建议"
      [--wf wf_20260929_01] [--config <agent_config.json>] [--slot small_model]
      [--dry-run]          # 只打印将发送的提示词，不调模型、不落盘
      [--mock <slip.json>] # 跳过模型，用现成工作流单走完整下游（测试/演示用）

约定：决策 = f(vault, workflow_log, 任务单, seed)；本脚本不写 vault（单一写者原则）。
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认 GBK：统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hermes_hooks"))

import shortlist as sl          # noqa: E402
import workflow_log as wl       # noqa: E402
import hermes_common as hc      # noqa: E402

DEFAULT_CONFIG = Path(os.environ["HERMES_AGENT_CONFIG"]) if os.environ.get("HERMES_AGENT_CONFIG") else (HERE / "agent_config.example.json")
DEFAULT_LOG = HERE / "workflow_log.jsonl"
DEFAULT_SLIP_DIR = HERE / "workflows"
LEAD_TIMEOUT = 60  # 组长是人工触发的 CLI（不受 hook 60s 预算约束），≠ 小模型在 hook 里的 8s 限时

LEAD_SYSTEM = """你是「关系网」的组长：把一件任务拆成工作流，交给网内的角色执行。
决策不看会话历史，只依据给出的材料；随机性由 seed 决定（seed 是输入的一部分）。

硬规则：
1. 只能从【候选短名单】里选人——不能发明新名字、不能绕过资格（不可用节点对你不可见）；
2. 步骤从 1 开始按序编号，每步写清：to（交给谁）、work（要什么产出）、require（引用剧本/能力名，没有就 null）；
3. 必须给 fallback：出现连续空跳时由谁独立兜底（**必须选一个有能力独立完成该任务的候选**，或 "main" 表示主 agent）；
4. 步骤要少而具体（能一步干完就别拆两步；**同一执行者能连续完成的小步骤请合并为一步**）；有剧本可引用时优先引用；
5. 只输出 JSON，不要输出其它文字。

输出格式：
{"wf": "<同输入 wf>", "seed": <同输入 seed>, "steps": [{"step": 1, "to": "<候选名>", "work": "<一句话>", "require": null}], "fallback": {"to": "<候选名或 main>"}, "why": "<一句话，可选>"}"""


def derive_seed(wf: str) -> int:
    return int(hashlib.sha256(wf.encode("utf-8")).hexdigest()[:8], 16)


def load_slot(config_path: Path, slot_name: str = "small_model") -> dict:
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    slot = cfg.get(slot_name)
    if not isinstance(slot, dict):
        raise SystemExit("配置里没有模型槽: %s（%s）" % (slot_name, config_path))
    return slot


def assemble_inputs(vault: Path, task: str, wf: str,
                    lead_name: str = "组长_日常", log_path: Path = DEFAULT_LOG) -> dict:
    # eps 仅在 with_pick=True 时参与抽样；此处只取排序（审读 L4），传 0.0 不影响候选顺序
    sl_result = sl.build(vault, lead_name, tau=1.0, eps=0.0, with_pick=False)
    scripts = sorted(p.stem for p in (Path(vault) / "30_剧本").glob("*.md")) if (Path(vault) / "30_剧本").exists() else []
    log_excerpt = []
    if Path(log_path).exists():
        lines = [l for l in Path(log_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        for line in lines[-8:]:
            try:
                log_excerpt.append(json.loads(line))
            except Exception:
                pass
    knowledge = _coupling_knowledge(vault)
    return {"task": task, "wf": wf, "seed": derive_seed(wf),
            "candidates": sl_result["ranked"], "excluded": sl_result["excluded"],
            "scripts": scripts, "log_excerpt": log_excerpt, "knowledge": knowledge}


COUPLING_DEPT = "60_耦合"
KNOWLEDGE_NODE_MAX = 700      # 单节点摘要上限
KNOWLEDGE_TOTAL_MAX = 1600    # 全部耦合知识总上限（保护组长小模型输入）


def _coupling_knowledge(vault: Path) -> list[dict]:
    """查耦合图接缝（v1d 后续 / C 臂 §2）：60_耦合/ 的规范知识节点摘要进任务包。
    节点是 available=false 的参考资料（不进短名单），由本接缝确定性拼入——
    组长"查耦合图"不靠模型自觉。压白 + 截断，总量受 KNOWLEDGE_TOTAL_MAX 钳制。"""
    out: list[dict] = []
    dept = Path(vault) / COUPLING_DEPT
    if not dept.is_dir():
        return out
    total = 0
    for p in sorted(dept.glob("*.md")):
        try:
            fm, body = sl.split_frontmatter(p.read_text(encoding="utf-8"))
            body = " ".join((body or "").split())
            if not body:
                continue
            excerpt = body[:KNOWLEDGE_NODE_MAX] + ("…（截断）" if len(body) > KNOWLEDGE_NODE_MAX else "")
            if total + len(excerpt) > KNOWLEDGE_TOTAL_MAX:
                break
            total += len(excerpt)
            out.append({"node": p.stem, "excerpt": excerpt})
        except Exception:
            continue
    return out


def build_prompt(inp: dict) -> tuple[str, str]:
    cand_lines = []
    for i, c in enumerate(inp["candidates"], 1):
        cap = ("｜%s" % c["capability"]) if c.get("capability") else ""
        cand_lines.append("%d. %s（weight=%.2f bias=%.2f score=%.3f%s）"
                          % (i, c["node"], c["weight"], c["bias"], c["score"], cap))
    if not cand_lines:
        cand_lines.append("（空——没有可见候选，必须给 fallback: main）")
    scripts = "、".join(inp["scripts"]) if inp["scripts"] else "无"
    log_ex = "无" if not inp["log_excerpt"] else "\n".join(
        json.dumps(r, ensure_ascii=False) for r in inp["log_excerpt"])
    know_ex = ""
    if inp.get("knowledge"):
        know_ex = "\n\n【耦合知识】\n" + "\n".join(
            "· %s：%s" % (k["node"], k["excerpt"]) for k in inp["knowledge"])
    user = ("【任务】\n%s\n\n【候选短名单】（只能从这里选）\n%s\n\n【可用剧本】\n%s%s\n\n"
            "【最近工作流日志】\n%s\n\n【wf】%s　【seed】%s（写进你的输出）"
            % (inp["task"], "\n".join(cand_lines), scripts, know_ex, log_ex, inp["wf"], inp["seed"]))
    return LEAD_SYSTEM, user


def extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        raise ValueError("模型输出里找不到 JSON")
    return json.loads(m.group(0))


def validate_slip(slip: dict, candidate_names: list[str]) -> tuple[bool, list[str]]:
    errs: list[str] = []
    if not isinstance(slip, dict):
        return False, ["slip 不是 dict"]
    wf = str(slip.get("wf") or "").strip()
    if not wf:
        errs.append("缺 wf")
    elif not re.fullmatch(r"[\w\-]{1,64}", wf):
        errs.append("wf 非法（仅限字母/数字/下划线/连字符，≤64）: %r" % wf)
    if not isinstance(slip.get("seed"), int):
        errs.append("缺 seed（必须是整数）")
    steps = slip.get("steps")
    if not isinstance(steps, list) or not steps:
        errs.append("steps 必须是非空列表")
    else:
        for i, st in enumerate(steps, 1):
            if not isinstance(st, dict):
                errs.append("steps[%d] 不是对象" % i)
                continue
            if st.get("step") != i:
                errs.append("steps[%d].step 应为 %d" % (i, i))
            if str(st.get("to") or "") not in candidate_names:
                errs.append("steps[%d].to 不在短名单: %r" % (i, st.get("to")))
            if not str(st.get("work") or "").strip():
                errs.append("steps[%d] 缺 work" % i)
    fb = slip.get("fallback")
    if not isinstance(fb, dict) or str(fb.get("to") or "") not in (candidate_names + ["main"]):
        errs.append("fallback.to 必须是候选名或 main")
    return (not errs), errs


def normalize_slip(slip: dict) -> dict:
    """确定性归一（脚本兜底，不依赖模型听话）：
    相邻两步 to 相同且 require 相同（含同为 None）→ 合并为一步，work 以「；」连接；
    随后重编号。返回新 dict（不改输入）。"""
    steps = slip.get("steps") or []
    merged: list[dict] = []
    for st in steps:
        if (merged
                and merged[-1].get("to") == st.get("to")
                and merged[-1].get("require") == st.get("require")):
            prev = merged[-1]
            prev["work"] = (str(prev.get("work") or "").rstrip("。；; ").strip()
                            + "；" + str(st.get("work") or "").strip()).strip("； ")
        else:
            merged.append({"step": st.get("step"), "to": st.get("to"),
                           "work": st.get("work"), "require": st.get("require")})
    for i, st in enumerate(merged, 1):
        st["step"] = i
    out = dict(slip)
    out["steps"] = merged
    return out


def compose_injection(setting: str = "", script: str = "", modulation: str = "") -> str:
    """注入包顺序（设计 §3 v1 定稿）：设定 → 剧本 → 调制。空段跳过。"""
    parts = []
    if (setting or "").strip():
        parts.append("【设定】\n" + setting.strip())
    if (script or "").strip():
        parts.append("【剧本】\n" + script.strip())
    if (modulation or "").strip():
        parts.append("【调制】\n" + modulation.strip())
    return "\n\n".join(parts)


def run(vault: Path, task: str, wf: str, *, config: Path = DEFAULT_CONFIG,
        slot_name: str = "small_model", log_path: Path = DEFAULT_LOG,
        slip_dir: Path = DEFAULT_SLIP_DIR, mock_text: str = None,
        call_fn=None, retries: int = 1, lead_name: str = "组长_日常") -> dict:
    inp = assemble_inputs(vault, task, wf, lead_name=lead_name, log_path=log_path)
    system, user = build_prompt(inp)
    cand_names = [c["node"] for c in inp["candidates"]]

    fixed_attempt = mock_text is not None or call_fn is not None
    attempts = 1 if fixed_attempt else max(1, 1 + int(retries))
    slip, last_err = None, "组长模型调用失败: empty"
    for _ in range(attempts):
        if mock_text is not None:
            raw = mock_text
        elif call_fn is not None:
            raw = call_fn(system, user)
        else:
            slot = load_slot(config, slot_name)
            raw = hc.call_model(slot, system, user, max_tokens=500, timeout=LEAD_TIMEOUT)
        if not raw:
            last_err = "组长模型调用失败: %s" % (hc.LAST_MODEL_ERROR or "empty")
            continue
        try:
            cand = extract_json(raw)
            ok, errs = validate_slip(cand, cand_names)
            if not ok:
                last_err = "工作流单校验失败: " + "; ".join(errs)
                continue
            cand = normalize_slip(cand)              # 脚本兜底：同执行者连续小步骤合并
            ok2, errs2 = validate_slip(cand, cand_names)
            if not ok2:
                last_err = "工作流单归一后校验失败: " + "; ".join(errs2)
                continue
            slip = cand
            break
        except ValueError as exc:                    # 找不到 JSON 等
            last_err = str(exc)
            continue
    if slip is None:
        raise SystemExit(last_err)                   # 审读 L3：真模型路径已自动重试

    slip_dir.mkdir(parents=True, exist_ok=True)
    slip_file = slip_dir / ("%s.json" % wf)
    slip_file.write_text(json.dumps(slip, ensure_ascii=False, indent=2), encoding="utf-8")

    first = slip["steps"][0]
    wl.append_dispatch(log_path, wf, first["step"], lead_name, first["to"],
                       first["work"], require=first.get("require"))
    return {"inputs": inp, "slip": slip, "slip_file": str(slip_file), "log": str(log_path)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=str(HERE / "agent_vault"))
    ap.add_argument("--task", required=True)
    ap.add_argument("--wf", default=None)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--slot", default="small_model")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", default=None, help="用现成工作流单 JSON 跳过模型（测试/演示）")
    args = ap.parse_args()

    wf = args.wf or ("wf_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    vault = Path(args.vault)

    if args.dry_run:
        inp = assemble_inputs(vault, args.task, wf)
        system, user = build_prompt(inp)
        print("=== SYSTEM ===\n%s\n\n=== USER ===\n%s" % (system, user))
        print("\n（dry-run：未调模型、未落盘）")
        return 0

    mock_text = Path(args.mock).read_text(encoding="utf-8") if args.mock else None
    result = run(vault, args.task, wf, config=Path(args.config), slot_name=args.slot,
                 mock_text=mock_text)
    slip = result["slip"]
    print("工作流单 %s → %s" % (wf, result["slip_file"]))
    for st in slip["steps"]:
        print("  step %d → %-10s | %s | require=%s" %
              (st["step"], st["to"], st["work"], st.get("require")))
    print("  fallback → %s" % slip["fallback"]["to"])
    print("首步已 dispatch 落账：%s" % result["log"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
