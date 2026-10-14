"""relnet_handoff —— 关系网 · v1d handoff 工具本体（register_tool 插件壳）v0.1

职责：把 net/handoff.py 的 run() 注册为 Hermes 工具 `handoff`（toolset=relnet）。
熔断计数与 handoff 落账在 tool_gate 的 pre_tool_call（先于本工具执行，单写者）；
本插件只负责：注册 + 生产路径解析（vault / workflow_log / artifacts / 角色状态）。

部署纪律：**装而不启用**（enable = config.yaml 的 plugins.enabled 增 `relnet_handoff`）。
启用前零行为变化（不注册 = 模型看不到 handoff 工具）。
启用条件（缺一不可）：
  ① agent_config.json 的 workflow_log_path 已配置（未配置 = 转交无法落账，本工具会拒绝执行）；
  ② 需要发起转交的节点，其角色卡 frontmatter `tools:` 清单须含 `handoff`
    （relnet_inject 按清单硬过滤工具，未列出 = 该节点看不到本工具）。

handler 契约：handler(args, **kwargs)——kwargs 由宿主按签名注入（task_id/session_id 等），
本 handler 只用 args。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_here = Path(__file__).resolve()
_base = _here.parents[2] if len(_here.parents) > 2 else _here.parent

_hf = None
_lp = None
_load_err = ""


def _load_net():
    """导入 net 工具链（handoff / lead_proactive）。定位链：RELNET_HOME env →
    仓库布局 parents[2]/net → 部署布局 parents[2]/agent-hooks/net → 开发机缺省
    （与 relnet_ledger 同款约定）。失败缓存错误信息（工具结果里可见，便于诊断）。"""
    global _hf, _lp, _load_err
    if _hf is not None:
        return True
    cands = []
    env = os.environ.get("RELNET_HOME", "").strip()
    if env:
        cands.append(Path(env))
    cands += [_base / "net", _base / "agent-hooks" / "net"]
    for d in cands:
        if (d / "handoff.py").exists():
            if str(d) not in sys.path:
                sys.path.insert(0, str(d))
            try:
                import handoff as hf  # noqa: E402
                import lead_proactive as lp  # noqa: E402
                _hf, _lp = hf, lp
                return True
            except Exception as exc:
                _load_err = "net 导入失败: %s" % exc
                return False
    _load_err = "net/ 定位失败（候选：%s）" % [str(c) for c in cands]
    return False


def _config_path() -> Path:
    """与 relnet_ledger 同款解析链：RELNET_CONFIG → HERMES_HOME/agent-hooks →
    仓库布局 → 部署布局 → RELNET_HOME/hermes_hooks → 本机缺省。"""
    env_cfg = os.environ.get("RELNET_CONFIG", "").strip()
    if env_cfg:
        return Path(env_cfg)
    cands = [
        Path(_lp._default_home() if _lp else Path.home()) / "agent-hooks" / "agent_config.json",
        _base / "hermes_hooks" / "agent_config.json",
        _base / "agent-hooks" / "agent_config.json",
    ]
    relnet_home = os.environ.get("RELNET_HOME", "").strip()
    if relnet_home:
        cands.append(Path(relnet_home) / "hermes_hooks" / "agent_config.json")
    cands.append(Path(_lp._default_home() if _lp else Path.home()) / "agent_config.json")
    for c in cands:
        if c.exists():
            return c
    return cands[0]


def _workflow_log_path():
    """熔断器同源日志路径（tool_gate 读同一键）——未配置 = 转交无法落账。"""
    try:
        cfg = json.loads(_config_path().read_text(encoding="utf-8"))
    except Exception:
        return None
    raw = str(cfg.get("workflow_log_path") or "").strip()
    return Path(raw) if raw else None


def handle(args, **kwargs):
    """工具入口。fail-open 纪律不适用于本工具：转交是结构化动作，失败必须显式报错。"""
    try:
        if not _load_net():
            return {"ok": False, "error": _load_err or "net 工具链不可用"}
        log_path = _workflow_log_path()
        if log_path is None:
            return {"ok": False,
                    "error": "agent_config.json 未配置 workflow_log_path——转交必须落单，"
                             "拒绝盲转交。请先配置熔断链路（或改由组长在任务单内重排）。"}
        relnet = Path(_lp.RELNET_HOME)
        vault = relnet / "agent_vault"
        artifact_dir = relnet / "artifacts"
        return _hf.run(args if isinstance(args, dict) else {},
                       vault=vault, log_path=log_path, artifact_dir=artifact_dir,
                       state_path=_lp.role_state_path())
    except Exception as exc:
        return {"ok": False, "error": "handoff 工具异常：%s" % exc}


def register(ctx):
    """注册 handoff 工具（未启用本插件时不注册——装而不启用，零行为变化）。"""
    if not _load_net():
        raise RuntimeError("relnet_handoff 无法定位 net 工具链：%s" % _load_err)
    schema = _hf.register_schema()
    ctx.register_tool(
        name="handoff",
        toolset="relnet",
        schema={"name": "handoff", "description": schema["description"],
                "parameters": schema["parameters"]},
        handler=handle,
        description=schema["description"],
        emoji="🤝",
    )
