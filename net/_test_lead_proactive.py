# -*- coding: utf-8 -*-
"""_test_lead_proactive.py —— v1a/v1b 装配验收（v0.2：指令含单+状态落盘；失败置 inactive）

覆盖：
  1. 开关语义：缺省/0 → False；未启用 → None 且**零副作用**（无日志/无状态）
  2. 成功态：投递文本 = base + 工作流单 + 执行行（行为规范口径，指令内**不再含卡文**）；
     角色状态落盘（active/role/ts/setting/script/tools）
  3. 失败态：坏输出 / 非法 slip / 模型异常 → None + **状态置 inactive** + 日志不新增
  4. 卡节选与卡 tools 解析（纯函数）
"""
import json
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lead_proactive as lp  # noqa: E402
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


def make_vault(tmp: Path) -> Path:
    vault = tmp / "vault"
    (vault / "00_组长").mkdir(parents=True)
    (vault / "20_角色").mkdir(parents=True)
    (vault / "00_组长" / "组长_日常.md").write_text(
        "---\ntype: agent\nform: lead\nknows: [\"[[陪伴者]]\"]\nversion: 1\n---\n\n# 组长\n",
        encoding="utf-8")
    (vault / "20_角色" / "陪伴者.md").write_text(
        "---\ntype: agent\nform: character_card\ncapability: 陪伴对话与语气润色\n"
        "tools: []\navailable: true\nbias: 1.00\n---\n\n# 陪伴者\n\n" + "克制、温和的陪伴者。" + "补充。" * 80 + "\n",
        encoding="utf-8")
    return vault


SLIP = {"wf": "w_test", "seed": 7,
        "steps": [{"step": 1, "to": "陪伴者", "work": "起草一条简短自然的主动消息", "require": None}],
        "fallback": {"to": "陪伴者"}}
BASE = "[SCHEDULER] 主动回合请求。\n最近已发过的主动消息（不要重复）：\n- 「吃了没」\n"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="leadpro_"))
    vault = make_vault(tmp)
    log = tmp / "workflow_log.jsonl"
    slips = tmp / "workflows"
    state_path = tmp / "role_state.json"

    print("== 1. 开关语义 ==")
    check("缺省 → False", lp.is_enabled({}) is False)
    check("value=1 → True", lp.is_enabled({"lead_workflow_enabled": {"value": 1}}) is True)
    out_off = lp.build_lead_instruction(wf="w_off", base_instruction=BASE,
                                        specs={"lead_workflow_enabled": {"value": 0}},
                                        vault_dir=vault, log_path=log, slip_dir=slips,
                                        role_state_path=state_path)
    check("未启用 → None（回退）", out_off is None)
    check("未启用零副作用（无日志/无状态）", not log.exists() and not state_path.exists())

    print("== 2. 成功态（mock 组长）==")
    out = lp.build_lead_instruction(wf="w_test", base_instruction=BASE,
                                    specs={"lead_workflow_enabled": {"value": 1}},
                                    urge=0.61, count_today=1, vault_dir=vault,
                                    log_path=log, slip_dir=slips, role_state_path=state_path,
                                    call_fn=lambda s, u: json.dumps(SLIP, ensure_ascii=False))
    check("返回投递文本", isinstance(out, str) and bool(out))
    check("含工作流单头（wf·口令 nonce）", re.search(r"【组长工作流单 w_test · [0-9a-f]{8}】", out) is not None, out[:160])
    check("含步骤与 fallback", ("step 1 → 陪伴者" in out) and ("fallback → 陪伴者" in out))
    check("执行行（行为规范口径）", "按「陪伴者」的行为规范" in out)
    check("指令内不再含卡文（已移入状态文件）", "【角色卡 ·" not in out and "克制、温和" not in out)
    check("base 完整保留（防重复段在）", "不要重复" in out and "「吃了没」" in out)
    check("slip 已落盘", (slips / "w_test.json").exists())
    recs = wl.read_records(log)
    check("dispatch 落账（lead→陪伴者）",
          len(recs) == 1 and recs[0]["type"] == "dispatch" and recs[0]["to"] == "陪伴者", str(recs))
    st = json.loads(state_path.read_text(encoding="utf-8"))
    check("角色状态：active/role/ts", st.get("active") is True and st.get("role") == "陪伴者" and bool(st.get("ts")))
    check("状态 marker：一次性口令（8 hex）且进投递文本（审读 M2）",
          bool(re.fullmatch(r"[0-9a-f]{8}", st.get("marker") or "")) and (st.get("marker") in out))
    check("状态 setting：行为规范框架 + 卡文", ("行为规范" in (st.get("setting") or "")) and ("克制、温和" in (st.get("setting") or "")))
    check("状态 script：wf + step 1", ("w_test" in (st.get("script") or "")) and ("step 1" in (st.get("script") or "")))
    check("状态 tools 透传（卡 frontmatter tools=[] → []）", st.get("tools") == [])

    print("== 3. 失败态（回退 + 状态置 inactive）==")
    out_bad = lp.build_lead_instruction(wf="w_bad1", base_instruction=BASE,
                                        specs={"lead_workflow_enabled": {"value": 1}},
                                        vault_dir=vault, log_path=log, slip_dir=slips,
                                        role_state_path=state_path,
                                        call_fn=lambda s, u: "这不是 JSON")
    check("坏输出 → None", out_bad is None)
    st2 = json.loads(state_path.read_text(encoding="utf-8"))
    check("失败 → 状态置 inactive", st2.get("active") is False, str(st2))
    bad_slip = {"wf": "w_bad2", "seed": 1,
                "steps": [{"step": 1, "to": "幽灵", "work": "x", "require": None}],
                "fallback": {"to": "main"}}
    out_bad2 = lp.build_lead_instruction(wf="w_bad2", base_instruction=BASE,
                                         specs={"lead_workflow_enabled": {"value": 1}},
                                         vault_dir=vault, log_path=log, slip_dir=slips,
                                         role_state_path=state_path,
                                         call_fn=lambda s, u: json.dumps(bad_slip, ensure_ascii=False))
    check("非法 slip → None", out_bad2 is None)
    check("失败后日志未新增", len(wl.read_records(log)) == 1)
    out_exc = lp.build_lead_instruction(wf="w_bad3", base_instruction=BASE,
                                        specs={"lead_workflow_enabled": {"value": 1}},
                                        vault_dir=vault, log_path=log, slip_dir=slips,
                                        role_state_path=state_path,
                                        call_fn=lambda s, u: (_ for _ in ()).throw(RuntimeError("boom")))
    check("模型异常 → None 且状态仍 inactive",
          out_exc is None and json.loads(state_path.read_text(encoding="utf-8")).get("active") is False)

    print("== 4. 卡解析（纯函数）==")
    card = lp._card_excerpt(vault, "陪伴者")
    check("节选 ≤300 字且去 frontmatter", len(card) <= 300 and "type:" not in card and not card.startswith("#"))
    check("卡 tools 解析（[] → []）", lp._card_tools(vault, "陪伴者") == [])
    check("找不到节点 → None", lp._card_tools(vault, "不存在") is None)

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
