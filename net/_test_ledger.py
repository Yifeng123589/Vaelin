# -*- coding: utf-8 -*-
"""_test_ledger.py —— v1c relnet_ledger 判定矩阵 + wrapper 端到端（沙箱在系统 temp，零仓库写入）

覆盖（v1c 方案 §A / §C.1）：
  1. judge 判定矩阵：非产出类 / status 失败 / error_type / 无路径字段 / 路径不存在 → 全部不落
  2. judge 正路：step 取状态、by 取角色、did=write:<路径>、duration_ms→s
  3. wrapper 门条件：不活跃 / 过期 / 缺 wf / 未配置 workflow_log_path → 零落账
  4. wrapper 正路：真落一行 action 且通过 workflow_log 校验
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TMP = Path(tempfile.mkdtemp(prefix="relnet_ledger_"))
HOME = TMP / "hermes_home"
(HOME / "agent-hooks").mkdir(parents=True, exist_ok=True)
LOG = TMP / "workflow_log.jsonl"
STATE = TMP / "relnet_role_state.json"

# 沙箱 env（插件按调用时读取）
os.environ["HERMES_HOME"] = str(HOME)
os.environ["RELNET_ROLE_STATE"] = str(STATE)
os.environ["RELNET_CONFIG"] = str(TMP / "agent_config.json")
os.environ["RELNET_HOME"] = str(HERE)
(TMP / "agent_config.json").write_text(
    json.dumps({"workflow_log_path": str(LOG), "privacy_mode": True}), encoding="utf-8")

sys.path.insert(0, str(HERE.parent / "hermes_plugins" / "relnet_ledger"))
import __init__ as ledger  # noqa: E402  # 插件模块
import workflow_log as wl  # noqa: E402

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


STATE_OK = {"active": True, "ts": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
            "wf": "wf_ledger_t", "role": "陪伴者", "step": 2}
ART = TMP / "artifact_ok.md"
ART.write_text("产出内容", encoding="utf-8")


def payload(**over):
    base = {"tool_name": "Write", "args": {"file_path": str(ART)},
            "status": "success", "duration_ms": 1500}
    base.update(over)
    return base


def rows() -> list:
    return wl.read_records(LOG) if LOG.exists() else []


def main() -> int:
    # 1) judge 判定矩阵
    check("非产出类工具不落", ledger.judge(payload(tool_name="terminal"), STATE_OK) is None)
    check("status=failed 不落", ledger.judge(payload(status="failed"), STATE_OK) is None)
    check("error_type 不落", ledger.judge(payload(error_type="io"), STATE_OK) is None)
    check("无路径字段不落", ledger.judge(payload(args={}), STATE_OK) is None)
    check("路径不存在不落", ledger.judge(payload(args={"file_path": str(TMP / "nope.md")}), STATE_OK) is None)
    rec = ledger.judge(payload(), STATE_OK)
    check("正路返回 kwargs", rec is not None and rec["wf"] == "wf_ledger_t"
          and rec["step"] == 2 and rec["by"] == "陪伴者"
          and rec["did"] == "write:%s" % ART and rec["status"] == "ok", str(rec))
    check("duration_ms→s", rec is not None and rec["duration_s"] == 1.5, str(rec))
    check("读类工具不落", ledger.judge(payload(tool_name="read_file"), STATE_OK) is None)

    # 2) wrapper 门条件
    STATE.write_text(json.dumps({**STATE_OK, "active": False}), encoding="utf-8")
    ledger.on_post_tool_call(payload())
    check("不活跃状态零落账", rows() == [])
    STATE.write_text(json.dumps({**STATE_OK, "ts": "2020-01-01T00:00:00+08:00"}), encoding="utf-8")
    ledger.on_post_tool_call(payload())
    check("过期状态零落账", rows() == [])
    STATE.write_text(json.dumps({**STATE_OK, "wf": ""}), encoding="utf-8")
    ledger.on_post_tool_call(payload())
    check("缺 wf 零落账", rows() == [])

    # 3) 未配置 workflow_log_path → 零落账（临时改 config）
    (TMP / "agent_config.json").write_text(json.dumps({"privacy_mode": True}), encoding="utf-8")
    STATE.write_text(json.dumps(STATE_OK), encoding="utf-8")
    ledger.on_post_tool_call(payload())
    check("未配置 workflow_log_path 零落账", rows() == [])
    (TMP / "agent_config.json").write_text(
        json.dumps({"workflow_log_path": str(LOG)}), encoding="utf-8")

    # 4) wrapper 正路：真落一行 action 且过校验
    ledger.on_post_tool_call(payload())
    rs = rows()
    check("正路落一行", len(rs) == 1, str(rs))
    ok, errs = wl.validate_record(rs[0]) if rs else (False, ["空"])
    check("落账行通过校验", ok and rs[0]["type"] == "action"
          and rs[0]["by"] == "陪伴者" and rs[0]["did"] == "write:%s" % ART, str(errs))

    # 5) register 契约（防「没有 register()」类 bug 复发——宿主只会 warning，插件静默变死件）
    class FakeCtx:
        def __init__(self):
            self.hooks = []

        def register_hook(self, name, cb):
            self.hooks.append((name, cb))

    fx = FakeCtx()
    ledger.register(fx)
    check("register() 已挂 post_tool_call 且指向 on_post_tool_call",
          len(fx.hooks) == 1 and fx.hooks[0][0] == "post_tool_call"
          and fx.hooks[0][1] is ledger.on_post_tool_call,
          str([(h[0], getattr(h[1], "__name__", h[1])) for h in fx.hooks]))

    # 6) _config_path 仓库布局解析（parents[2]/hermes_hooks——修正 v0.1 的级数 bug）
    import importlib.util
    import shutil as _sh

    fake = TMP / "fakerepo"
    (fake / "hermes_plugins" / "relnet_ledger").mkdir(parents=True, exist_ok=True)
    _sh.copy2(Path(ledger.__file__), fake / "hermes_plugins" / "relnet_ledger" / "__init__.py")
    (fake / "hermes_hooks").mkdir(exist_ok=True)
    (fake / "hermes_hooks" / "agent_config.json").write_text(
        '{"workflow_log_path": "x"}', encoding="utf-8")
    os.environ["HERMES_HOME"] = str(TMP / "empty_home")   # 标准位不存在 → 走仓库布局候选
    os.environ.pop("RELNET_CONFIG", None)
    spec = importlib.util.spec_from_file_location(
        "ledger_fake", fake / "hermes_plugins" / "relnet_ledger" / "__init__.py")
    mod2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod2)
    got = mod2._config_path()
    expect = fake / "hermes_hooks" / "agent_config.json"
    ok_cfg = os.path.normcase(os.path.realpath(str(got))) == os.path.normcase(os.path.realpath(str(expect)))
    check("_config_path 命中仓库布局（parents[2]/hermes_hooks）", ok_cfg, str(got))

    print("== 5. v1d 跑类（terminal/bash × 重定向产物）==")
    run_art = TMP / "run_out.txt"
    run_art.write_text("x", encoding="utf-8")
    rec_run = ledger.judge(payload(tool_name="terminal",
                                   args={"command": "echo hi > %s" % run_art}), STATE_OK)
    check("跑类：`>` 重定向产物落 run:<路径>",
          rec_run is not None and rec_run["did"] == "run:%s" % run_art, str(rec_run))
    check("跑类：2>&1 非产物不落",
          ledger.judge(payload(tool_name="terminal",
                               args={"command": "ls 2>&1 | tr -d '\\000'"}), STATE_OK) is None)
    check("跑类：无重定向不落（0 贡献）",
          ledger.judge(payload(tool_name="terminal", args={"command": "ls -la"}), STATE_OK) is None)
    check("跑类：tee 产物落",
          ledger.judge(payload(tool_name="bash",
                               args={"command": "echo x | tee %s" % run_art}), STATE_OK) is not None)
    STATE_CHAIN = dict(STATE_OK, chain="shard-1")
    rec_chain = ledger.judge(payload(), STATE_CHAIN)
    check("状态带 chain → kwargs 透传 chain",
          rec_chain is not None and rec_chain.get("chain") == "shard-1", str(rec_chain))

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
