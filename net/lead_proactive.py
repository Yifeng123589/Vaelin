#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""lead_proactive.py —— v1a/v1b 主动弧线改道装配（供 scheduler 全过分支调用）

输入：调度器已格式化的 base 指令（旧 INSTRUCTION）+ 开关 + 语境
输出：新的投递文本 = base + 【组长工作流单】 + 执行行；未启用/失败 → None（调用方回退 base）。

v1b（2026-09-29）：卡文不再拼进投递文本，而是写入**角色状态文件**，
由 `relnet_inject` 插件在 provider 请求层注入（只作用于带触发口令的主动回合）。
口令 = 每次装配生成的一次性随机 nonce（写进状态 `marker` 与投递文本头部）——明文
[SCHEDULER] 可被伪造的问题由此解决（审读 M2）；失败时把状态置为 inactive（防陈旧状态泄漏）。

数据落位：RELNET_HOME（默认=开发工作区 opencode/net；可用环境变量覆盖）。
角色状态路径：$RELNET_ROLE_STATE 或 $HERMES_HOME/relnet_role_state.json（HERMES_HOME 未设 →
%LOCALAPPDATA%\\hermes，再退 ~/.hermes——审读 L6）。
开关：params.json 的 `lead_workflow_enabled`（0=旧指令，1=组长指令；默认 0）。
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

RELNET_HOME = Path(os.environ.get("RELNET_HOME", str(Path(__file__).resolve().parent)))
CARD_EXCERPT_MAX = 300

_sl = None
_lead = None


def _load_tools() -> bool:
    """从 RELNET_HOME 导入 net 工具链（shortlist/lead）。失败 = 改道不可用。"""
    global _sl, _lead
    if _lead is not None:
        return True
    try:
        if str(RELNET_HOME) not in sys.path:
            sys.path.insert(0, str(RELNET_HOME))
        import shortlist as sl_mod  # noqa: E402
        import lead as lead_mod  # noqa: E402
        _sl, _lead = sl_mod, lead_mod
        return True
    except Exception:
        return False


def is_enabled(specs: dict) -> bool:
    spec = (specs or {}).get("lead_workflow_enabled") or {}
    try:
        return float(spec.get("value") or 0) > 0
    except Exception:
        return False


def _card_excerpt(vault: Path, node: str, max_chars: int = CARD_EXCERPT_MAX) -> str:
    """角色卡瘦身段：frontmatter 之后的正文，压白、去标题、截断。"""
    try:
        if _sl is None and not _load_tools():
            return ""
        target = None
        for md in Path(vault).rglob(node + ".md"):
            target = md
            break
        if target is None:
            return ""
        text = target.read_text(encoding="utf-8")
        fm, body = _sl.split_frontmatter(text)
        body = " ".join((body or "").split())
        body = body.replace("# " + node, "").strip()
        return body[:max_chars]
    except Exception:
        return ""


def _card_tools(vault: Path, node: str):
    """读角色卡 frontmatter 的 tools 清单（None=不过滤；[]=本轮无工具）。"""
    try:
        if _sl is None and not _load_tools():
            return None
        target = None
        for md in Path(vault).rglob(node + ".md"):
            target = md
            break
        if target is None:
            return None
        text = target.read_text(encoding="utf-8")
        fm, _ = _sl.split_frontmatter(text)
        raw = _sl.get_val(fm, "tools")
        if raw is None:
            return None
        return [x.strip().strip("\"'") for x in str(raw).strip("[]").split(",") if x.strip()]
    except Exception:
        return None


def _default_home() -> str:
    home = os.environ.get("HERMES_HOME", "").strip()
    if home:
        return home
    lad = os.environ.get("LOCALAPPDATA", "").strip()
    return str(Path(lad) / "hermes") if lad else str(Path.home() / ".hermes")


def role_state_path() -> Path:
    env = os.environ.get("RELNET_ROLE_STATE", "").strip()
    if env:
        return Path(env)
    return Path(_default_home()) / "relnet_role_state.json"


def _write_role_state(state: dict, path=None) -> None:
    """best-effort 原子写；失败不影响主链。"""
    try:
        p = Path(path) if path else role_state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_lead_instruction(*, wf: str, base_instruction: str, specs: dict,
                           urge=None, count_today=None, force=None,
                           vault_dir=None, log_path=None, slip_dir=None,
                           call_fn=None, role_state_path=None) -> str | None:
    """返回投递文本；未启用 → None；失败 → 置 inactive 并返回 None（调用方回退 base）。

    force: 覆盖开关（测试用）；vault_dir/log_path/slip_dir/role_state_path: 落位覆盖（测试用）；
    call_fn: 组长模型调用覆盖（测试用，签名 call_fn(system, user) -> str）。
    """
    enabled = force if force is not None else is_enabled(specs)
    if not enabled:
        return None
    try:
        if not _load_tools():
            return None
        vault = Path(vault_dir) if vault_dir else (RELNET_HOME / "agent_vault")
        if not vault.is_dir():
            return None
        task = ("主动回合：基于对用户的了解，规划『一条简短、自然的主动消息（1~2 句）』的产出安排。"
                "背景：冲动值 %s；今天第 %s 条。"
                % (urge if urge is not None else "-", count_today if count_today is not None else "-"))
        kwargs = {}
        if log_path is not None:
            kwargs["log_path"] = Path(log_path)
        if slip_dir is not None:
            kwargs["slip_dir"] = Path(slip_dir)
        result = _lead.run(vault, task, wf, call_fn=call_fn, **kwargs)
        slip = result["slip"]
        step1 = slip["steps"][0]
        role = str(step1.get("to") or "")
        card = _card_excerpt(vault, role)

        # v1b：角色状态落盘（供 relnet_inject 在请求层注入；口令 nonce 随状态与投递文本走）
        nonce = secrets.token_hex(4)
        setting = ""
        if card:
            setting = "本轮回答须遵守以下角色卡行为规范（「%s」）：\n\n%s" % (role, card)
        _write_role_state({
            "active": True, "ts": _now_iso(), "wf": wf, "role": role, "marker": nonce,
            "setting": setting,
            "script": "工作流 %s · step 1：%s" % (wf, step1.get("work") or ""),
            "tone": "",
            "tools": _card_tools(vault, role),
            "placement": "mid_user",
        }, role_state_path)

        lines = ["", "【组长工作流单 %s · %s】" % (wf, nonce)]
        for st in slip["steps"]:
            lines.append("  step %d → %s | %s | require=%s"
                         % (st["step"], st["to"], st["work"], st.get("require")))
        lines.append("  fallback → %s" % (slip.get("fallback") or {}).get("to"))
        lines.append("按「%s」的行为规范完成 step 1——只输出要给他看的那条消息本身。" % role)
        return base_instruction.rstrip() + "\n" + "\n".join(lines) + "\n"
    except (Exception, SystemExit):
        _write_role_state({"active": False, "ts": _now_iso(), "reason": "build_failed"},
                          role_state_path)
        return None
