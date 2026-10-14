# -*- coding: utf-8 -*-
"""_test_executor.py —— v1c 多步执行器验收（stub 后端，沙箱在系统 temp，零仓库写入）

覆盖（v1c 方案 §B / §C.1）：
  1. 两步链日志序列（无 lead.py 时）：action(1), dispatch(2), action(2)——step1 不重复落 dispatch
  2. 字段：by=各步角色、did=artifact:<文件>、duration_s 有值；全部通过 workflow_log 校验
  3. 产物：<wf>_stepN.md 存在且非空
  4. 角色状态：逐步落盘（step/role/marker 随步走、口令互不相同且进了 briefing）；完成置 inactive
  5. 失败路径：backend 空产出 → 不落该步 action、状态置 aborted、无产物
  6. 坏 slip：缺 wf/steps → ValueError
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TMP = Path(tempfile.mkdtemp(prefix="relnet_exec_"))
VAULT = TMP / "agent_vault"
LOG = TMP / "workflow_log.jsonl"
STATE = TMP / "relnet_role_state.json"
ARTDIR = TMP / "artifacts"

os.environ["RELNET_HOME"] = str(HERE)
os.environ["RELNET_ROLE_STATE"] = str(STATE)

# 临时 vault：两个最小角色卡
for name, body in (("陪伴者", "（陪伴者：负责起草陪伴语气的内容。）"),
                   ("助理", "（助理：负责润色与排版。）")):
    p = VAULT / "20_角色" / ("%s.md" % name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntype: agent\nform: character_card\ntools: []\nversion: 1\n---\n\n# %s\n\n%s\n"
                 % (name, body), encoding="utf-8")

import executor as ex  # noqa: E402
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


SLIP = {"wf": "wf_exec_t",
        "steps": [{"step": 1, "to": "陪伴者", "work": "起草一条简短问候", "require": None},
                  {"step": 2, "to": "助理", "work": "润色上一产出", "require": None}],
        "fallback": {"to": "main"}}


def main() -> int:
    seen_steps, seen_briefings, seen_states = [], [], []

    def stub_backend(step, briefing, state):
        seen_steps.append(int(state.get("step") or 0))
        seen_briefings.append(briefing)
        seen_states.append(dict(state))
        return "产出（%s · step%s）" % (state.get("role"), state.get("step"))

    r = ex.run_slip(SLIP, stub_backend, vault=VAULT, log_path=LOG,
                    state_path=STATE, artifact_dir=ARTDIR)
    check("两步链 ok", r.get("ok") is True and r.get("steps_done") == 2, str(r))

    recs = wl.read_records(LOG)
    check("日志序列 action(1),dispatch(2),action(2)",
          [x["type"] for x in recs] == ["action", "dispatch", "action"], str([x["type"] for x in recs]))
    check("step 序 1,2,2", [x["step"] for x in recs] == [1, 2, 2], str([x["step"] for x in recs]))
    check("by=各步角色（action 行）/ to=派工对象（dispatch 行）",
          [x.get("by") for x in recs if x["type"] == "action"] == ["陪伴者", "助理"]
          and recs[1].get("to") == "助理",
          str(recs))
    check("did=artifact 引用", all(str(x.get("did", "")).startswith("artifact:") for x in recs if x["type"] == "action"))
    check("全部通过校验", all(wl.validate_record(x)[0] for x in recs))
    check("dispatch 的 from=组长节点名", recs[1].get("from") == "组长_日常", str(recs[1]))

    arts = sorted(ARTDIR.glob("wf_exec_t_step*.md"))
    check("两个产物文件存在", len(arts) == 2 and all(a.stat().st_size > 0 for a in arts), str(arts))

    check("状态逐步落盘（step 感知）", seen_steps == [1, 2], str(seen_steps))
    markers = [s.get("marker") for s in seen_states]
    check("口令互不相同", markers[0] and markers[1] and markers[0] != markers[1], str(markers))
    check("口令进了 briefing（注入门匹配面）",
          all(m in b for m, b in zip(markers, seen_briefings)))
    check("briefing 含剧本/work", "起草一条简短问候" in seen_briefings[0]
          and "润色上一产出" in seen_briefings[1])

    fin = json.loads(STATE.read_text(encoding="utf-8"))
    check("完成后状态 inactive", fin.get("active") is False and fin.get("reason") == "workflow_complete", str(fin))

    # ── 失败路径：step2 空产出 → 不落 action、置 aborted、无产物 ──
    LOG2 = TMP / "wf_log_fail.jsonl"
    STATE2 = TMP / "state_fail.json"

    def flaky_backend(step, briefing, state):
        return "产出 step1" if int(state.get("step") or 0) == 1 else "   "

    r2 = ex.run_slip(SLIP, flaky_backend, vault=VAULT, log_path=LOG2,
                     state_path=STATE2, artifact_dir=TMP / "art2")
    recs2 = wl.read_records(LOG2) if LOG2.exists() else []
    check("空产出 → ok=False 且停在该步", r2.get("ok") is False and r2.get("step") == 2, str(r2))
    check("失败步不落 action（dispatch 是事实保留，回执缺席）",
          [x["type"] for x in recs2] == ["action", "dispatch"], str([x["type"] for x in recs2]))
    fin2 = json.loads(STATE2.read_text(encoding="utf-8"))
    check("失败置 aborted", fin2.get("active") is False and "aborted" in str(fin2.get("reason")), str(fin2))
    check("失败步无产物", not (TMP / "art2" / "wf_exec_t_step2.md").exists())

    # ── 坏 slip ──
    try:
        ex.run_slip({"steps": []}, stub_backend, vault=VAULT, log_path=LOG,
                    state_path=STATE, artifact_dir=ARTDIR)
        check("坏 slip 抛 ValueError", False, "未抛")
    except ValueError:
        check("坏 slip 抛 ValueError", True)

    # ── 熔断联动（真实写者版）：空跳×2 → streak=2；executor 再写 real action → 清零 ──
    wl.append_handoff(LOG, "wf_exec_t", 2, "助理", "组长_日常", "空跳·申请改道")
    wl.append_handoff(LOG, "wf_exec_t", 2, "组长_日常", "助理", "空跳·回派")
    check("空跳×2 → streak=2", wl.current_streak(wl.read_records(LOG), "wf_exec_t") == 2)
    r3 = ex.run_slip({"wf": "wf_exec_t",
                      "steps": [{"step": 1, "to": "助理", "work": "补一条产出", "require": None}],
                      "fallback": {"to": "main"}},
                     stub_backend, vault=VAULT, log_path=LOG, state_path=STATE,
                     artifact_dir=ARTDIR)
    check("executor 复跑 ok", r3.get("ok") is True)
    fin3 = wl.read_records(LOG)
    check("executor 真写的 action → streak 清零", wl.current_streak(fin3, "wf_exec_t") == 0)
    check("清零行确为 executor 落账（did=artifact:）",
          [x for x in fin3 if x["type"] == "action"][-1]["did"].startswith("artifact:"))

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
