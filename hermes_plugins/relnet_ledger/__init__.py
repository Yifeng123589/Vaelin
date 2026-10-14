"""relnet_ledger —— 关系网 · 落账接缝（post_tool_call hook）v0.2（v1d：增"跑"类 action）

Observer：每次工具调用后判定"是否落一行 action"（设计 §7.3：action 行由 hook 自动落盘、
节点不回填——审计链不过 LLM 的手）。返回值被宿主忽略。

仅当同时满足：
  ① 角色状态 active 且新鲜（TTL，与 relnet_inject 同源同规则）
  ② agent_config 配置了 workflow_log_path（未配置＝熔断链路关，零行为变化）
  ③ 状态携带 wf（无 wf 无法计数——跳过，不落）
  ④ 工具名属产出类——两型（工程提炼 §2.5 三分类：改/跑/写/汇报，且参数带产物引用）：
     · 写类（v1c）：write|edit|create|save|patch|replace|insert × 路径字段
     · 跑类（v1d）：terminal|shell|bash|exec|cmd|run × 命令文本含产物重定向（`>`/`>>`/`tee <路径>`）
  ⑤ 调用成功（status 非失败枚举 且 无 error_type）
  ⑥ 产物引用**当前存在**（存在性轻校验；不存在＝没产出，不落——宁缺不假）
→ 落一行 action：{ts, wf, step(状态携带,缺省1), type:"action", by:<角色>,
   did:"write:<路径>"|"run:<路径>", status:"ok", duration_s:<ms/1000>, tokens/out/cost:null}
  （角色状态携带 chain 时带上——v1d 熔断分键）

已知边界（v1d 接受）：跑类的相对路径产物按 hook 进程 CWD 解析，解析不到即不落
（宁缺不假；汇报类仍不落——无产物引用形态，留给后续口径）。

fail-open：任何异常静默返回；落账失败不影响工具调用本身。
单实现：落账走 net/workflow_log.append_action（带跨进程锁）；本插件自包含判定逻辑
（判定副本与 relnet_inject 的状态/TTL 助手同源，改动须两处同步——tests/_test_ledger.py 防漂移）。
部署：装而不启用；随开旗 bundle 一起启用（plugins.enabled 增 relnet_ledger）。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

PRODUCING_TOOL = re.compile(r"write|edit|create|save|patch|replace|insert", re.I)
RUN_TOOL = re.compile(r"terminal|shell|bash|exec|cmd|run", re.I)
COMMAND_KEYS = ("command", "cmd", "script")
# 产物重定向：`> path` / `>> path` / `tee path`（2>&1 的 "&1" 不存在 → 天然不落）
RUN_REDIRECT = re.compile(r">>?\s*([^\s;&|>]+)")
RUN_TEE = re.compile(r"\btee\s+(?:-{1,2}[\w-]+\s+)*([^\s;&|>]+)")
FAIL_STATUS = {"error", "failed", "timeout", "cancelled", "aborted"}
PATH_KEYS = ("file_path", "path", "filename", "file")
_BY_MAX, _DID_MAX = 64, 200


def register(ctx):
    """挂载 post_tool_call 观察者（v1c 必需——缺 register() 时宿主只在日志里警告，
    插件会静默变成死件；此契约由 tests 防回归）。"""
    ctx.register_hook("post_tool_call", on_post_tool_call)


def _default_home() -> str:
    """与 relnet_inject 同规则（审读 L6）：HERMES_HOME → %LOCALAPPDATA%\\hermes → ~/.hermes。"""
    home = os.environ.get("HERMES_HOME", "").strip()
    if home:
        return home
    lad = os.environ.get("LOCALAPPDATA", "").strip()
    return str(Path(lad) / "hermes") if lad else str(Path.home() / ".hermes")


def _repo_base() -> Path:
    """插件文件第三级父目录（parents[2]）：
    仓库布局=opencode；部署布局=%LOCALAPPDATA%\\hermes；沙箱布局=<沙箱根>。
    用于解析 net/ 与 hermes_hooks/ 的相对位置（修正 v0.1 的 parents[1] 级数错误）。"""
    here = Path(__file__).resolve()
    parents = here.parents
    return parents[2] if len(parents) > 2 else here.parent


def _state_path() -> Path:
    env = os.environ.get("RELNET_ROLE_STATE", "").strip()
    if env:
        return Path(env)
    return Path(_default_home()) / "relnet_role_state.json"


def _ttl_seconds() -> int:
    try:
        return max(0, int(os.environ.get("RELNET_ROLE_TTL_SECONDS", "3600")))
    except Exception:
        return 3600


def _load_state():
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _fresh(state: dict) -> bool:
    try:
        ts = datetime.fromisoformat(str(state.get("ts")))
        age = (datetime.now().astimezone() - ts).total_seconds()
        return 0 <= age <= _ttl_seconds()
    except Exception:
        return False


def _config_path() -> Path:
    """agent_config.json 定位链：RELNET_CONFIG env → HERMES_HOME/agent-hooks →
    仓库布局（parents[2]/hermes_hooks）→ 部署/沙箱布局（parents[2]/agent-hooks）
    → RELNET_HOME/hermes_hooks → 本机缺省。"""
    env_cfg = os.environ.get("RELNET_CONFIG", "").strip()
    if env_cfg:
        return Path(env_cfg)
    base = _repo_base()
    cands = [
        Path(_default_home()) / "agent-hooks" / "agent_config.json",
        base / "hermes_hooks" / "agent_config.json",
        base / "agent-hooks" / "agent_config.json",
    ]
    relnet_home = os.environ.get("RELNET_HOME", "").strip()
    if relnet_home:
        cands.append(Path(relnet_home) / "hermes_hooks" / "agent_config.json")
    cands.append(Path(_default_home()) / "agent_config.json")
    for c in cands:
        if c.exists():
            return c
    return cands[0]


def _workflow_log_path():
    try:
        cfg = json.loads(_config_path().read_text(encoding="utf-8"))
    except Exception:
        return None
    raw = str(cfg.get("workflow_log_path") or "").strip()
    return Path(raw) if raw else None


_wlog = None
_wlog_tried = False


def _load_wlog():
    """单实现：落账一律走 net/workflow_log（带跨进程锁）。导入定位：
    RELNET_HOME env → 仓库布局 parents[2]/net → 部署布局 parents[2]/agent-hooks/net
    → 开发机缺省（与工具链同款约定）。缓存。"""
    global _wlog, _wlog_tried
    if _wlog_tried:
        return _wlog
    _wlog_tried = True
    base = _repo_base()
    cands = []
    env = os.environ.get("RELNET_HOME", "").strip()
    if env:
        cands.append(Path(env))
    cands.append(base / "net")
    cands.append(base / "agent-hooks" / "net")
    for d in cands:
        if (d / "workflow_log.py").exists():
            if str(d) not in __import__("sys").path:
                __import__("sys").path.insert(0, str(d))
            try:
                import workflow_log as wl  # noqa: E402
                _wlog = wl
            except Exception:
                _wlog = None
            break
    return _wlog


def _duration_s(payload: dict):
    """duration_ms → 秒（3 位小数）；缺失/非法 → None（字段可 null）。"""
    try:
        ms = payload.get("duration_ms")
        if ms is None:
            return None
        return round(float(ms) / 1000.0, 3)
    except Exception:
        return None


def _run_artifact_path(args: dict) -> str:
    """跑类产物引用：命令文本里的重定向目标（`>` / `>>` / `tee`，取首个）。"""
    for k in COMMAND_KEYS:
        cmd = str(args.get(k) or "").strip()
        if not cmd:
            continue
        m = RUN_REDIRECT.search(cmd) or RUN_TEE.search(cmd)
        if m:
            return m.group(1).strip("\"'")
    return ""


def judge(payload: dict, state: dict):
    """纯判定：返回 append_action 的 kwargs，或 None（不落账）。测试可直接调用。"""
    tool = str(payload.get("tool_name") or "")
    if not tool:
        return None
    status = str(payload.get("status") or "").strip().lower()
    if status in FAIL_STATUS or payload.get("error_type"):
        return None                                   # 失败不落（防"失败也算清账"）
    args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
    did = ""
    if PRODUCING_TOOL.search(tool):
        path = ""
        for k in PATH_KEYS:
            v = str(args.get(k) or "").strip()
            if v:
                path = v
                break
        if not path:
            return None                               # 无路径字段＝无产物引用
        did = "write:" + path
    elif RUN_TOOL.search(tool):
        path = _run_artifact_path(args)
        if not path:
            return None                               # 跑类无产物重定向＝0 贡献
        did = "run:" + path
    else:
        return None                                   # 未注册工具/查询类：0 贡献
    try:
        if not Path(path).exists():
            return None                               # 产物存在性轻校验（写失败/相对路径解析不到不落）
    except OSError:
        return None
    return {
        "wf": str(state.get("wf") or "").strip(),
        "step": int(state.get("step") or 1),
        "by": (str(state.get("role") or "").strip() or "unknown")[:_BY_MAX],
        "did": did[:_DID_MAX],
        "status": "ok",
        "duration_s": _duration_s(payload),
        "chain": (str(state.get("chain") or "").strip()[:64] or None),
    }


def on_post_tool_call(*args, **kwargs):
    """fail-open Observer：任何路径的异常都静默返回。"""
    try:
        payload: dict = {}
        if args and isinstance(args[0], dict):
            payload.update(args[0])
        payload.update({k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, list, dict))})
        state = _load_state()
        if not isinstance(state, dict) or not state.get("active") or not _fresh(state):
            return                                    # ① 不活跃/过期：零行为
        wf = str(state.get("wf") or "").strip()
        if not wf:
            return                                    # ③ 无 wf：无法计数，不落
        log_path = _workflow_log_path()
        if log_path is None:
            return                                    # ② 熔断链路关：零行为
        wlog = _load_wlog()
        if wlog is None:
            return                                    # 单实现不可用：宁缺不假
        rec = judge(payload, state)
        if rec is None:
            return
        wlog.append_action(log_path, wf=rec["wf"], step=rec["step"], by=rec["by"],
                           did=rec["did"], status=rec["status"], duration_s=rec["duration_s"],
                           chain=rec.get("chain"))
    except Exception:
        return
