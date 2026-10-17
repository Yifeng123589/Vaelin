#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""net/executor.py —— v1c 多步执行器（沙箱可跑；生产接入留 v1d）

职责（v1c 方案 §B）：把"只跑 step 1"升级为"逐步执行 + 机器落账"，让熔断器的
**action 清零面真实存在**。真模型链路（沙箱）：陪伴者起草 → 助理润色 →
日志序列 dispatch(1), action(1), dispatch(2), action(2)（dispatch(1) 由 lead.py 落，本模块不重复）。

流程（对 slip["steps"] 逐步）：
  step≥2 进入时先补 dispatch 行（from=组长节点名，L5）
  → 写角色状态（step 感知 + 一次性口令 marker；复用 lead_proactive 单实现）
  → backend(step, briefing, state) -> str（沙箱=hermes chat 子进程；单测=stub）
  → 产物落盘：主链 artifact_dir/<wf>_step{N}.md；有 chain 时 <wf>__c_<safe>_step{N}.md（**非空校验**；空产出=失败）
  → action 行（by=step.to，did="artifact:<文件>"，duration_s=backend 耗时）
  → 全部完成：状态置 inactive（防陈旧泄漏）
失败：**不落 action**（防"失败也算清账"）；置 inactive；中止返回 {"ok": False,...}

backend 接口：callable(step: dict, briefing: str, state: dict) -> str
便利工厂：hermes_chat_backend(hermes_home=None) —— hermes chat --oneshot 子进程。
"""
from __future__ import annotations

import os
import re
import secrets
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import workflow_log as wl  # noqa: E402
import lead_proactive as lp  # noqa: E402  # 复用卡文/工具/状态写入的单一实现

_PRODUCING_ARTIFACT_OK = re.compile(r"\S")   # 产物非空校验


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")



def _artifact_name(wf: str, step: int, chain: str | None = None) -> str:
    """产物文件名：主链（chain 空）保持旧名 <wf>_step{N}.md；
    非空 chain → <wf>__c_<safe>_step{N}.md（safe=仅 [A-Za-z0-9._-]，其余→_ ，长度封顶 64）。"""
    if not chain:
        return "%s_step%d.md" % (wf, step)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(chain))[:64] or "_"
    return "%s__c_%s_step%d.md" % (wf, safe, step)


def _nonce() -> str:
    return secrets.token_hex(4)


def _briefing(wf: str, step_no: int, role: str, work: str, nonce: str,
              prev_text: str | None = None) -> str:
    """交 backend 的任务书：口令在首行（relnet_inject 以最后一条 user 消息匹配）；
    多步链把上一步产物带给依赖它的下一步（e2e 实测：不传则下游只能正确地抱怨缺料）。"""
    out = ["【工作流 %s · step %d · 口令 %s】" % (wf, step_no, nonce),
           "任务：%s" % work]
    if prev_text:
        capped = prev_text if len(prev_text) <= 4000 else prev_text[:4000] + "…（截断）"
        out.append("【上一步产出（待你处理）】\n%s" % capped)
    out.append("（按「%s」的行为规范输出；只输出产出本身。）" % role)
    return "\n".join(out)


def run_slip(slip: dict, backend, *, vault: Path, log_path: Path,
             state_path: Path | None = None, artifact_dir: Path,
             lead_name: str = "组长_日常", dispatch_ge2: bool = True) -> dict:
    """v1d 增补：slip 可携带可选 `chain`（任务单链，熔断分键用，缺省=主链），
    dispatch/action 行与角色状态都会带上；`dispatch_ge2=False` 供 handoff 单步执行用
    （handoff 行已是路由记录，不重复落 dispatch）。"""
    wf = str((slip or {}).get("wf") or "").strip()
    steps = (slip or {}).get("steps") or []
    if not wf or not steps:
        raise ValueError("slip 缺 wf/steps")
    chain = str((slip or {}).get("chain") or "").strip()[:64] or None

    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    sp = Path(state_path) if state_path else lp.role_state_path()
    artifacts: list[str] = []
    prev_text: str | None = None

    for st in steps:
        n = int(st.get("step") or 0)
        role = str(st.get("to") or "").strip()
        work = str(st.get("work") or "").strip()
        if n < 1 or not role or not work:
            return _abort(sp, wf, n, "步骤字段缺失（step/to/work）")

        if n >= 2 and dispatch_ge2:
            # step≥2 进入时补 dispatch（step 1 由 lead.py 落，不重复）
            wl.append_dispatch(log_path, wf, n, lead_name, role, work,
                               require=st.get("require"), chain=chain)

        nonce = _nonce()
        state = {
            "active": True, "ts": _now_iso(), "wf": wf, "role": role,
            "step": n, "marker": nonce, "chain": chain,
            "setting": lp._card_excerpt(Path(vault), role),
            "script": "工作流 %s · step %d：%s" % (wf, n, work),
            "tone": "",
            "tools": lp._card_tools(Path(vault), role),
            "placement": "mid_user",
        }
        lp._write_role_state(state, sp)

        briefing = _briefing(wf, n, role, work, nonce, prev_text)
        t0 = time.monotonic()
        try:
            out = backend(st, briefing, state)
        except Exception as exc:
            return _abort(sp, wf, n, "backend 异常：%s" % exc)
        duration_s = round(time.monotonic() - t0, 3)

        if not isinstance(out, str) or not _PRODUCING_ARTIFACT_OK.search(out):
            return _abort(sp, wf, n, "backend 空产出（失败不落 action）")

        artifact = artifact_dir / _artifact_name(wf, n, chain)
        artifact.write_text(out if out.endswith("\n") else out + "\n", encoding="utf-8")
        artifacts.append(str(artifact))
        prev_text = out
        wl.append_action(log_path, wf=wf, step=n, by=role,
                         did="artifact:%s" % artifact, status="ok",
                         duration_s=duration_s, chain=chain)

    lp._write_role_state({"active": False, "ts": _now_iso(), "wf": wf,
                          "reason": "workflow_complete"}, sp)
    return {"ok": True, "wf": wf, "steps_done": len(steps), "artifacts": artifacts,
            "log": str(log_path)}


def _abort(state_path: Path, wf: str, step_no: int, reason: str) -> dict:
    lp._write_role_state({"active": False, "ts": _now_iso(), "wf": wf,
                          "reason": "aborted_step%d" % step_no}, state_path)
    return {"ok": False, "wf": wf, "step": step_no, "error": reason}


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _extract_reply(stdout: str) -> str:
    """从 hermes chat 的 TUI stdout 里取干净回复：优先「☤ Hermes」框内文；
    兜底去 Query 回显与尾部会话元数据。"""
    text = _ANSI.sub("", stdout or "")
    lines = text.splitlines()
    start = end = None
    for i, ln in enumerate(lines):
        if start is None:
            if ln.startswith("╭─") and "Hermes" in ln:
                start = i + 1
        elif ln.startswith("╰─"):
            end = i
            break
    if start is not None and end is not None and end > start:
        body = "\n".join(lines[start:end]).strip()
        if body:
            return body
    drop = ("Query:", "Resume this session", "Session:", "Title:", "Duration:")
    return "\n".join(ln for ln in lines if not ln.startswith(drop)).strip()


def hermes_chat_backend(hermes_home: str | None = None):
    """沙箱后端工厂：hermes chat --oneshot 子进程（query 走临时文件；HERMES_HOME 可注入；
    回复经 _extract_reply 去掉 TUI 装饰）。"""
    import subprocess
    import tempfile

    def backend(step: dict, briefing: str, state: dict) -> str:
        q = Path(tempfile.gettempdir()) / ("relnet_q_%s_step%s.txt" % (state.get("wf"), state.get("step")))
        q.write_text(briefing, encoding="utf-8")
        env = dict(os.environ)
        if hermes_home:
            env["HERMES_HOME"] = str(hermes_home)
        r = subprocess.run(["hermes", "chat", "--query-file", str(q), "--oneshot"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, env=env)
        return _extract_reply(r.stdout or "")

    return backend
