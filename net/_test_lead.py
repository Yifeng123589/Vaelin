# -*- coding: utf-8 -*-
"""_test_lead.py —— S4 验收测试（沙箱在系统 temp，零仓库写入；模型全部用 mock，零 API 调用）

覆盖（工程提炼 §5 · S4）：
  1. 输入组装：短名单/剧本/日志摘录 + seed 派生确定性
  2. 提示词：任务与候选进入 user；硬规则进入 system
  3. 解析：fenced / 裸 JSON / 无 JSON 报错
  4. 校验（写时校验）：to 必须在短名单；步骤有序；fallback 必填；seed 必填
  5. 注入包顺序：设定 → 剧本 → 调制；空段跳过
  6. mock 闭环：slip 落盘 + 首步 dispatch 落账（并用 workflow_log 校验器复核）
  7. 坏 slip 被拒（发明节点）
  8. CLI --dry-run 冒烟
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lead  # noqa: E402
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
    (vault / "30_剧本").mkdir(parents=True)
    (vault / "00_组长" / "组长_日常.md").write_text(
        "---\ntype: agent\nform: lead\nknows: [\"[[A]]\", \"[[B]]\"]\nversion: 1\n---\n\n# 组长\n",
        encoding="utf-8")
    (vault / "20_角色" / "A.md").write_text(
        "---\ntype: agent\nform: character_card\ncapability: 写草稿\nweight: 0.8\nbias: 1.1\navailable: true\n---\n\n# A\n",
        encoding="utf-8")
    (vault / "20_角色" / "B.md").write_text(
        "---\ntype: agent\nform: character_card\nweight: 0.3\navailable: true\n---\n\n# B\n",
        encoding="utf-8")
    (vault / "30_剧本" / "整理剧本.md").write_text("# 整理剧本\n", encoding="utf-8")
    return vault


GOOD_SLIP = {"wf": "wf_t01", "seed": 42,
             "steps": [{"step": 1, "to": "A", "work": "写一份整理草稿", "require": None},
                       {"step": 2, "to": "B", "work": "复核草稿并给建议", "require": None}],
             "fallback": {"to": "B"}}

BAD_SLIP = {"wf": "wf_t01", "seed": 42,
            "steps": [{"step": 1, "to": "幽灵节点", "work": "x", "require": None}],
            "fallback": {"to": "B"}}


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="lead_"))
    vault = make_vault(tmp)
    log = tmp / "workflow_log.jsonl"
    slip_dir = tmp / "workflows"

    print("== 1. 输入组装 ==")
    inp = lead.assemble_inputs(vault, "把 A 页整理成三条建议", "wf_t01", log_path=log)
    cands = [c["node"] for c in inp["candidates"]]
    check("候选 = [A, B]", cands == ["A", "B"], str(cands))
    check("剧本清单提取", inp["scripts"] == ["整理剧本"], str(inp["scripts"]))
    check("seed 派生确定", inp["seed"] == lead.derive_seed("wf_t01") and inp["seed"] == lead.derive_seed("wf_t01"))
    check("不同 wf → 不同 seed", lead.derive_seed("wf_a") != lead.derive_seed("wf_b"))

    print("== 2. 提示词 ==")
    system, user = lead.build_prompt(inp)
    check("user 含任务与候选", "把 A 页整理" in user and "A（weight" in user)
    check("user 携带 capability", "写草稿" in user)
    check("system 含硬规则关键字", ("只能从" in system) and ("fallback" in system))

    print("== 3. 解析 ==")
    fenced = "这是结果：\n```json\n" + json.dumps(GOOD_SLIP, ensure_ascii=False) + "\n```\n完。"
    check("fenced JSON 可解析", lead.extract_json(fenced)["wf"] == "wf_t01")
    try:
        lead.extract_json("没有任何 JSON")
        check("无 JSON 报错", False)
    except ValueError:
        check("无 JSON 报错", True)

    print("== 4. 写时校验 ==")
    ok, errs = lead.validate_slip(GOOD_SLIP, cands)
    check("合法 slip 通过", ok, str(errs))
    ok, errs = lead.validate_slip(BAD_SLIP, cands)
    check("发明节点被拒", (not ok) and any("短名单" in e for e in errs), str(errs))
    order_bad = json.loads(json.dumps(GOOD_SLIP))
    order_bad["steps"] = [{"step": 2, "to": "A", "work": "x"}, {"step": 1, "to": "B", "work": "y"}]
    ok, errs = lead.validate_slip(order_bad, cands)
    check("步骤乱序被拒", (not ok) and any("应为" in e for e in errs), str(errs))
    no_fb = {"wf": "w", "seed": 1, "steps": GOOD_SLIP["steps"]}
    ok, errs = lead.validate_slip(no_fb, cands)
    check("缺 fallback 被拒", (not ok) and any("fallback" in e for e in errs), str(errs))
    no_seed = {"wf": "w", "steps": GOOD_SLIP["steps"], "fallback": {"to": "main"}}
    ok, errs = lead.validate_slip(no_seed, cands)
    check("缺 seed 被拒", (not ok) and any("seed" in e for e in errs), str(errs))
    esc = json.loads(json.dumps(GOOD_SLIP))
    esc["wf"] = "../../x"
    ok, errs = lead.validate_slip(esc, cands)
    check("wf 路径逃逸被拒（审读 L2）", (not ok) and any("wf 非法" in e for e in errs), str(errs))

    print("== 5. 注入包顺序 ==")
    inj = lead.compose_injection("你叫助理", "按三栏整理", "语气克制")
    i1, i2, i3 = inj.find("【设定】"), inj.find("【剧本】"), inj.find("【调制】")
    check("设定 → 剧本 → 调制", 0 <= i1 < i2 < i3, inj)
    check("空段跳过", "【剧本】" not in lead.compose_injection("只有设定"))

    print("== 5.5 归一合并（脚本兜底）==")
    two_same = {"wf": "w", "seed": 1,
                "steps": [{"step": 1, "to": "A", "work": "列文件", "require": None},
                          {"step": 2, "to": "A", "work": "配说明", "require": None}],
                "fallback": {"to": "A"}}
    m = lead.normalize_slip(two_same)
    check("同节点连续两步合并为一步", len(m["steps"]) == 1 and "列文件" in m["steps"][0]["work"] and "配说明" in m["steps"][0]["work"], str(m["steps"]))
    diff_to = json.loads(json.dumps(two_same))
    diff_to["steps"][1]["to"] = "B"
    check("不同节点不合并", len(lead.normalize_slip(diff_to)["steps"]) == 2)
    diff_req = json.loads(json.dumps(two_same))
    diff_req["steps"][0]["require"] = "剧本X"
    check("require 不同不合并", len(lead.normalize_slip(diff_req)["steps"]) == 2)

    print("== 6. mock 闭环（slip 落盘 + 首步 dispatch 落账）==")
    result = lead.run(vault, "把 A 页整理成三条建议", "wf_t01", log_path=log,
                      slip_dir=slip_dir, mock_text=json.dumps(GOOD_SLIP, ensure_ascii=False))
    check("slip 文件已落盘", Path(result["slip_file"]).exists())
    recs = wl.read_records(log)
    check("日志恰 1 行且为 dispatch", len(recs) == 1 and recs[0]["type"] == "dispatch", str(recs))
    ok_v, errs_v = wl.validate_record(recs[0]) if recs else (False, ["empty"])
    check("落账行通过 workflow_log 校验", ok_v, str(errs_v))
    check("dispatch: 组长节点 → A（审读 L5）", recs and recs[0]["from"] == "组长_日常" and recs[0]["to"] == "A")

    print("== 7. 坏 slip 被拒（发明节点）==")
    try:
        lead.run(vault, "x", "wf_t02", log_path=log, slip_dir=slip_dir,
                 mock_text=json.dumps(BAD_SLIP, ensure_ascii=False))
        check("坏 slip 抛 SystemExit", False)
    except SystemExit as exc:
        check("坏 slip 抛 SystemExit", "短名单" in str(exc))
    check("坏 slip 未污染日志", len(wl.read_records(log)) == 1)

    print("== 8. CLI --dry-run ==")
    r = subprocess.run([sys.executable, str(HERE / "lead.py"), "--vault", str(vault),
                        "--task", "把 A 页整理成三条建议", "--dry-run"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("dry-run 退出码 0 且输出提示词", r.returncode == 0 and "【候选短名单】" in r.stdout,
          (r.stdout or "")[:200] + (r.stderr or "")[:200])

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
