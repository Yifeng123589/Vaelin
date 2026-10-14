#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""net/handoff.py —— v1d handoff 工具本体（熔断器 live 消费面 + executor 生产接入）

设计依据（工程提炼 §2.5）：
  · 转交必须走工具调用 `handoff(to=...)`——纯文本转交脚本看不见；写进每个角色卡剧本；
  · **组长是唯一路由器**：组员→组员转交禁止（横向只准咨询），改道必须 handoff 回组长；
  · 熔断计数（连续无行动轮数，按 wf+chain 分键）由 tool_gate 的 pre_tool_call 在本工具
    调用**之前**现算（handoff +1 / action 清零）并完成 handoff 落账——本模块**不重复落
    handoff 行**（单写者=tool_gate，v1d 双实现合并）。

本模块职责（工具的执行面）：
  1. 拓扑守门（组长是唯一路由器）：转交目标 ∈ 组长（组长_日常 / main）∪ **任务单路由面**
     （slip 里出现过的 to——组长拆单时已授权的节点）。调用者的角色状态只是"马甲"
     （主 agent 执行 step1 时注入为该角色，其随后的 handoff 本质是组长路由），不作判定依据；
     不在路由面的组员→组员 = 越权横向转交，拒绝（e2e 发现项，2026-10-05）；
  2. →组长/main（reroute）：改道请求落账即达（handoff 行已由 tool_gate 落）——
     清调用者角色状态（inactive），返回重路由指引，不 spawn（组长路由不产 artifact）；
  3. 路由面内的接力（execute）：executor 单步——写目标角色状态（step 感知 + 一次性口令）→
     backend（生产/沙箱 = hermes chat 子进程，即 executor 生产接入）→ 产物落盘 + action 行
     （清熔断计数；executor 单实现，dispatch_ge2=False——handoff 行已是路由记录）。
失败：不落 action（防"失败也算清账"）；返回 {"ok": False, "error": ...}。

from 的判定：角色状态 active 且新鲜（relnet_inject 同源）→ state.role；否则 main（主 agent）。
（from 只用于落账署名与 executor 的 lead_name，不参与拓扑判定。）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import executor as ex  # noqa: E402
import lead_proactive as lp  # noqa: E402

LEAD_NODES = {"组长_日常", "main"}
_TO_MAX = 64


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slip_targets(wf: str, slip_dir: Path | None = None) -> set:
    """任务单路由面：该 wf 的 slip 里出现过的 to 集合（组长拆单时已授权的节点）。
    slip 文件 = <slip_dir>/<wf>.json（lead.run 的落盘约定）。缺文件 = 空集（严格模式：
    只准转交组长）。e2e 发现（2026-10-05）：拓扑判定不能看调用者的角色状态"马甲"——
    主 agent 执行 step1 时注入为该角色，其随后的 handoff 本质是组长路由；
    以 slip 路由面为准才不误伤合法接力，也才拦得住越权横向转交。"""
    try:
        base = Path(slip_dir) if slip_dir else (lp.RELNET_HOME / "workflows")
        data = json.loads((base / ("%s.json" % wf)).read_text(encoding="utf-8"))
        return {str(st.get("to") or "").strip()
                for st in (data.get("steps") or []) if str(st.get("to") or "").strip()}
    except Exception:
        return set()


def _caller_role(state_path: Path | None) -> str:
    """调用者身份：角色状态 active 且新鲜（TTL 与 relnet_inject/ledger 同源：
    RELNET_ROLE_TTL_SECONDS，缺省 3600）→ 其 role；否则 main（主 agent）。"""
    try:
        sp = Path(state_path) if state_path else lp.role_state_path()
        import json
        import os
        state = json.loads(sp.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or not state.get("active"):
            return "main"
        ts = state.get("ts")
        if ts:
            from datetime import datetime
            try:
                ttl = max(0, int(os.environ.get("RELNET_ROLE_TTL_SECONDS", "3600")))
            except Exception:
                ttl = 3600
            age = (datetime.now().astimezone() - datetime.fromisoformat(str(ts))).total_seconds()
            if not (0 <= age <= ttl):
                return "main"
        return str(state.get("role") or "main").strip()[:_TO_MAX] or "main"
    except Exception:
        return "main"


def run(args: dict, *, vault: Path, log_path: Path, artifact_dir: Path,
        backend=None, state_path: Path | None = None,
        slip_dir: Path | None = None) -> dict:
    """handoff 工具执行入口。返回 dict（工具结果序列化后回给模型）。"""
    args = args if isinstance(args, dict) else {}
    wf = str(args.get("wf") or "").strip()
    to = str(args.get("to") or "").strip()[:_TO_MAX]
    work = str(args.get("work") or "").strip()
    if not wf or not to or not work:
        return {"ok": False, "error": "handoff 需要 wf / to / work 三个字段（转交必须落单）"}

    chain = str(args.get("chain") or "").strip()[:64] or None
    try:
        step = int(args.get("step") or 0)
    except (TypeError, ValueError):
        step = 0
    if step < 1:
        step = 1
    frm = _caller_role(state_path)

    # 拓扑守门（组长是唯一路由器）：目标 ∈ 组长 ∪ 任务单路由面（slip 里出现过的 to）。
    # 调用者的角色状态只是"马甲"（主 agent 执行 step1 时注入为该角色），不作判定依据。
    allowed = LEAD_NODES | slip_targets(wf, slip_dir)
    if to not in allowed:
        return {"ok": False, "error": (
            "转交目标 %s 不在任务单路由内（组长是唯一路由器，组员→组员横向转交禁止）。"
            "请 handoff 回组长（%s）重新路由；或确认 wf=%s 的任务单确实派给了 %s。"
            % (to, "组长_日常", wf, to))}

    # →组长/main：改道落账即达（handoff 行由 tool_gate 落，这里只给指引）；
    # 同时清调用者的角色状态（转交后旧角色不再注入，下一轮回到组长身份）
    if to in LEAD_NODES:
        try:
            lp._write_role_state({"active": False, "ts": _now_iso(), "wf": wf,
                                  "reason": "handed_off_to_%s" % to},
                                 Path(state_path) if state_path else None)
        except Exception:
            pass
        return {"ok": True, "mode": "reroute",
                "wf": wf, "from": frm, "to": to, "step": step,
                "message": ("改道请求已落账（handoff 行），下一轮由组长（%s）重新路由："
                            "重新规划剩余步骤或按任务单 fallback 独立完成。" % to)}

    # 组长→组员：executor 单步生产执行（handoff 行已由 tool_gate 落；不重复 dispatch）
    if backend is None:
        backend = ex.hermes_chat_backend()
    slip = {"wf": wf, "chain": chain,
            "steps": [{"step": step, "to": to, "work": work,
                       "require": args.get("require")}]}
    try:
        result = ex.run_slip(slip, backend, vault=Path(vault), log_path=Path(log_path),
                             state_path=state_path, artifact_dir=Path(artifact_dir),
                             lead_name=frm, dispatch_ge2=False)
    except Exception as exc:
        return {"ok": False, "error": "handoff 执行异常：%s" % exc}
    if not result.get("ok"):
        return {"ok": False, "wf": wf, "step": step, "error": result.get("error") or "executor 失败"}
    return {"ok": True, "mode": "execute", "wf": wf, "step": step, "by": to,
            "artifact": (result.get("artifacts") or [""])[0],
            "message": "step %d 已由「%s」完成，产物见 %s（action 行已落账，熔断计数清零）。"
                       % (step, to, (result.get("artifacts") or [""])[0])}


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().astimezone().isoformat(timespec="seconds")


def register_schema() -> dict:
    """工具 schema（供插件 register_tool 使用）。"""
    return {
        "name": "handoff",
        "description": ("关系网转交：把当前工作转交给网内另一节点。"
                        "组长是唯一路由器——组员只能 handoff 回组长（组长_日常/main），"
                        "组员→组员被拒绝；转交按 wf+chain 计入空跳熔断计数"
                        "（连续 N 次无实质产出会被拦截并要求按 fallback 独立完成）。"
                        "组长→组员的转交会同步触发该节点单步执行并返回产物。"),
        "parameters": {
            "type": "object",
            "properties": {
                "wf": {"type": "string", "description": "任务单号（必填，转交必须落单）"},
                "to": {"type": "string", "description": "转交给谁（组长_日常 / main / 短名单内角色）"},
                "work": {"type": "string", "description": "要做什么（一句话）"},
                "step": {"type": "integer", "description": "步骤号（缺省 1）"},
                "require": {"type": "string", "description": "引用的剧本/能力名（可空）"},
                "chain": {"type": "string", "description": "任务单链（并行分片用，缺省=主链）"},
            },
            "required": ["wf", "to", "work"],
        },
    }
