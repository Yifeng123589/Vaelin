# -*- coding: utf-8 -*-
"""_test_handoff.py —— v1d handoff 工具本体验收（沙箱在系统 temp，零仓库写入）

覆盖（工程提炼 §2.5 / v1d 方案）：
  1. 字段校验：缺 wf/to/work → 显式报错（转交必须落单）
  2. 拓扑守门：组员→组员拒绝；→组长 reroute（不 spawn、清角色状态、不自行落 handoff 行）
  3. 组长→组员 execute：stub backend → 产物落盘 + action 行（step≥2 不重复 dispatch），
     action 行带 chain（熔断计数清零面）
  4. 失败路径：backend 空产出 → ok=False 且**不落 action**（防"失败也算清账"）
  5. 角色状态落位：execute 完成后状态 inactive（workflow_complete）
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TMP = Path(tempfile.mkdtemp(prefix="relnet_handoff_"))
STATE = TMP / "relnet_role_state.json"
LOG = TMP / "workflow_log.jsonl"
ARTDIR = TMP / "artifacts"

os.environ["RELNET_HOME"] = str(HERE)
os.environ["RELNET_ROLE_STATE"] = str(STATE)
os.environ["HERMES_HOME"] = str(TMP / "hermes_home")

import handoff as hf  # noqa: E402
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


def write_state(role: str, active: bool = True):
    STATE.write_text(json.dumps({
        "active": active, "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "wf": "wfH", "role": role, "step": 1,
    }, ensure_ascii=False), encoding="utf-8")


def rows() -> list:
    return wl.read_records(LOG) if LOG.exists() else []


def stub_ok(step, briefing, state) -> str:
    return "产出文本 %s" % state.get("role")


def stub_empty(step, briefing, state) -> str:
    return ""


def main() -> int:
    print("== 1. 字段校验 ==")
    r = hf.run({"wf": "wfH", "to": "组长_日常"}, vault=HERE, log_path=LOG, artifact_dir=ARTDIR)
    check("缺 work → 显式报错", not r["ok"] and "work" in r["error"], str(r))

    print("== 2. 拓扑守门（组长是唯一路由器）==")
    write_state("陪伴者")
    r = hf.run({"wf": "wfH", "step": 2, "to": "助理", "work": "横向转交"},
               vault=HERE, log_path=LOG, artifact_dir=ARTDIR)
    check("组员→组员拒绝", not r["ok"] and "禁止" in r["error"], str(r))

    r = hf.run({"wf": "wfH", "step": 2, "to": "组长_日常", "work": "改道回组长"},
               vault=HERE, log_path=LOG, artifact_dir=ARTDIR)
    st = json.loads(STATE.read_text(encoding="utf-8"))
    check("→组长 reroute：ok 且 mode=reroute",
          r.get("ok") and r.get("mode") == "reroute", str(r))
    check("→组长 reroute：角色状态已清（inactive）", st.get("active") is False, str(st))
    check("→组长 reroute：本模块不落任何行（handoff 行归 tool_gate）", rows() == [], str(rows()))

    print("== 3. 路由面内接力（execute：executor 单步生产接入）==")
    SLIPDIR = TMP / "workflows"
    SLIPDIR.mkdir(exist_ok=True)
    (SLIPDIR / "wfH.json").write_text(json.dumps({
        "wf": "wfH", "seed": 1,
        "steps": [{"step": 1, "to": "陪伴者", "work": "起草"},
                  {"step": 2, "to": "助理", "work": "润色"}],
        "fallback": {"to": "main"},
    }, ensure_ascii=False), encoding="utf-8")
    write_state("陪伴者", active=False)   # 调用者=主 agent（无活跃角色状态 → main/组长）
    r = hf.run({"wf": "wfH", "step": 2, "to": "助理", "work": "润色产物", "chain": "shard1",
                "require": None},
               vault=HERE, log_path=LOG, artifact_dir=ARTDIR, backend=stub_ok,
               slip_dir=SLIPDIR)
    check("execute：ok 且 mode=execute", r.get("ok") and r.get("mode") == "execute", str(r))
    art = Path(r.get("artifact") or "")
    check("execute：产物落盘非空", art.exists() and art.read_text(encoding="utf-8").strip() != "")
    recs = rows()
    kinds = [(x.get("type"), x.get("by"), x.get("chain")) for x in recs]
    check("execute：落 action 行（by=目标角色，带 chain）",
          ("action", "助理", "shard1") in kinds, str(kinds))
    check("execute：不重复落 dispatch（dispatch_ge2=False）",
          sum(1 for x in recs if x.get("type") == "dispatch") == 0, str(kinds))
    st2 = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    check("execute：完成后状态 inactive（workflow_complete）",
          st2.get("active") is False and st2.get("reason") == "workflow_complete", str(st2))
    check("execute：熔断计数清零", wl.current_streak(recs, "wfH", "shard1") == 0)

    print("== 4. 马甲回归（e2e 发现项：穿角色的组长路由不误伤）==")
    LOG.unlink()
    write_state("陪伴者", active=True)    # 主 agent 正穿 step1 角色马甲
    r = hf.run({"wf": "wfH", "step": 2, "to": "助理", "work": "接力润色"},
               vault=HERE, log_path=LOG, artifact_dir=ARTDIR, backend=stub_ok,
               slip_dir=SLIPDIR)
    check("马甲身份 → slip 路由面内目标放行（execute）",
          r.get("ok") and r.get("mode") == "execute", str(r))
    r2 = hf.run({"wf": "wfH", "step": 3, "to": "局外人", "work": "越权横向转交"},
                vault=HERE, log_path=LOG, artifact_dir=ARTDIR, backend=stub_ok,
                slip_dir=SLIPDIR)
    check("马甲身份 → 路由面外目标仍拒（组长唯一路由器）",
          not r2["ok"] and "不在任务单路由内" in r2["error"], str(r2))
    LOG.unlink()

    print("== 5. 失败路径（防失败也算清账）==")
    if LOG.exists():
        LOG.unlink()
    r = hf.run({"wf": "wfH", "step": 1, "to": "助理", "work": "会失败的任务"},
               vault=HERE, log_path=LOG, artifact_dir=ARTDIR, backend=stub_empty)
    check("空产出 → ok=False", not r["ok"], str(r))
    check("失败不落 action", rows() == [], str(rows()))

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
