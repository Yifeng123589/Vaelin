# -*- coding: utf-8 -*-
"""_test_workflow_log.py —— S2 验收测试（沙箱在系统 temp，零仓库写入）

覆盖（对应工程提炼 §2.5 与设计 §9/§10）：
  1. 校验：必填缺失 / 未知字段 / type 非法 / ts 非法 → 全部拒绝
  2. 幂等 API：三种记录追加 → 合法落盘
  3. 熔断计数：dispatch 不计；handoff +1；action 清零；跨 wf 隔离
  4. 阈值：连续 3 次 handoff → should_break(N=3) 成立
  5. 崩溃恢复语义：计数从日志重算（新进程读同一文件得同样结果）
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
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


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="wf_log_"))
    log = tmp / "workflow_log.jsonl"

    print("== 1. 校验 ==")
    ok, errs = wl.validate_record({"ts": wl._now(), "wf": "w1", "step": 1, "type": "handoff",
                                   "from": "A", "to": "B", "work": "t", "require": None})
    check("合法 handoff 通过", ok, str(errs))
    ok, errs = wl.validate_record({"ts": wl._now(), "wf": "w1", "step": 1, "type": "handoff",
                                   "from": "A", "work": "t"})
    check("缺 to 被拒", (not ok) and any("to" in e for e in errs), str(errs))
    ok, errs = wl.validate_record({"ts": wl._now(), "wf": "w1", "step": 1, "type": "dispatch",
                                   "from": "A", "to": "B", "work": "t", "extra": 1})
    check("未知字段被拒", (not ok) and any("未知字段" in e for e in errs), str(errs))
    ok, errs = wl.validate_record({"ts": "not-a-date", "wf": "w1", "step": 1, "type": "action",
                                   "by": "A", "did": "write:x"})
    check("ts 非法被拒", (not ok) and any("ts" in e for e in errs), str(errs))
    ok, errs = wl.validate_record({"ts": wl._now(), "wf": "w1", "step": 1, "type": "action",
                                   "by": "A", "did": "write:x", "status": None, "cost_usd": None})
    check("action 可空字段通过（null 合法）", ok, str(errs))
    ok, errs = wl.validate_record({"ts": wl._now(), "wf": "w1", "step": 1, "type": "handoff",
                                   "from": "A", "to": "B", "work": "t", "chain": "shard1"})
    check("v1d：chain 字段合法（三型通用）", ok, str(errs))

    print("== 2. 追加（坏数据进不了日志）==")
    wl.append_dispatch(log, "w1", 1, "lead", "A", "任务：改模块甲")
    wl.append_handoff(log, "w1", 2, "A", "B", "子任务：乙")
    try:
        wl.append_handoff(log, "w1", 3, "B", "", "子任务：丙")  # to 空 → 应拒
        check("空 to 追加被拒", False)
    except ValueError:
        check("空 to 追加被拒", True)
    wl.append_handoff(log, "w1", 3, "B", "C", "子任务：丙")
    wl.append_handoff(log, "w1", 4, "C", "D", "子任务：丁")
    check("落盘行数 = 4", len(wl.read_records(log)) == 4)

    print("== 3. 熔断计数 ==")
    recs = wl.read_records(log)
    s = wl.current_streak(recs, "w1")
    check("连续 handoff ×3（dispatch 不计）→ streak=3", s == 3, "实际 %d" % s)
    check("should_break(N=3) = True", wl.should_break(recs, "w1", 3) is True)
    check("跨 wf 隔离（w2 无记录 → 0）", wl.current_streak(recs, "w2") == 0)

    wl.append_action(log, "w1", 5, "D", "write:report.md", status="ok", duration_s=12.5)
    recs = wl.read_records(log)
    check("action 清零 → streak=0", wl.current_streak(recs, "w1") == 0)
    wl.append_handoff(log, "w1", 6, "D", "E", "子任务：戊")
    recs = wl.read_records(log)
    check("再 handoff → streak=1", wl.current_streak(recs, "w1") == 1)

    print("== 4. 崩溃恢复语义（子进程重读）==")
    r = subprocess.run([sys.executable, str(HERE / "workflow_log.py"), "streak", str(log), "w1"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("CLI streak 输出含 streak=1", "=1" in r.stdout, r.stdout + r.stderr)
    r = subprocess.run([sys.executable, str(HERE / "workflow_log.py"), "validate", str(log)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("CLI validate 全合法", ("非法 0" in r.stdout) and r.returncode == 0, r.stdout + r.stderr)

    print("== 5. 容错读 + 锁 + 时间序（审读 M4/L8）==")
    log2 = tmp / "mixed.jsonl"
    good1 = {"ts": "2026-09-29T10:00:00+08:00", "wf": "w1", "step": 1, "type": "dispatch",
             "from": "lead", "to": "A", "work": "x", "require": None}
    good2 = {"ts": "2026-09-29T10:00:01+08:00", "wf": "w1", "step": 2, "type": "handoff",
             "from": "A", "to": "B", "work": "y", "require": None}
    log2.write_text("\n".join([json.dumps(good1), "{broken json", json.dumps(good2)]) + "\n",
                    encoding="utf-8")
    recs2, bad2 = wl.read_records_lenient(log2)
    check("容错读：跳坏行（2 好 + 1 坏）", len(recs2) == 2 and bad2 == 1, "%s/%s" % (len(recs2), bad2))
    check("容错读后计数可用", wl.current_streak(recs2, "w1") == 1)
    r_streak = subprocess.run([sys.executable, str(HERE / "workflow_log.py"), "streak", str(log2), "w1"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("CLI streak 跳坏行并提示", ("=1" in r_streak.stdout) and ("坏行" in r_streak.stdout),
          r_streak.stdout + r_streak.stderr)
    wl.append_dispatch(log2, "w2", 1, "lead", "A", "z")
    check("追加产生 .lock（跨进程锁文件）", Path(str(log2) + ".lock").exists())
    check("追加后共 3 条好行", len(wl.read_records_lenient(log2)[0]) == 3)
    order_log = tmp / "order.jsonl"
    rows3 = [good1, {**good1, "ts": "2026-09-29T09:59:00+08:00", "step": 2}]
    order_log.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows3) + "\n",
                         encoding="utf-8")
    r_order = subprocess.run([sys.executable, str(HERE / "workflow_log.py"), "validate", str(order_log)],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("validate 报时间序倒退（rc=2）",
          r_order.returncode == 2 and "时间序" in r_order.stdout, r_order.stdout + r_order.stderr)

    print("== 6. v1d 熔断分键（wf, chain）==")
    clog = tmp / "chain_log.jsonl"
    wl.append_handoff(clog, "wfC", 1, "A", "B", "s1", chain="shard1")
    wl.append_handoff(clog, "wfC", 2, "B", "C", "s2", chain="shard1")
    wl.append_handoff(clog, "wfC", 1, "A", "D", "s3", chain="shard2")
    wl.append_action(clog, wf="wfC", step=3, by="D", did="artifact:x", chain="shard2")
    wl.append_handoff(clog, "wfC", 1, "A", "B", "主链跳")
    crecs, _ = wl.read_records_lenient(clog)
    check("分键：shard1 计 2", wl.current_streak(crecs, "wfC", "shard1") == 2)
    check("分键：shard2 被 action 清零", wl.current_streak(crecs, "wfC", "shard2") == 0)
    check("分键：主链独立计 1", wl.current_streak(crecs, "wfC") == 1)
    check("分键：should_break 按 chain 判定",
          wl.should_break(crecs, "wfC", 2, "shard1")
          and not wl.should_break(crecs, "wfC", 2, "shard2")
          and not wl.should_break(crecs, "wfC", 2))
    okc, errs_c = wl.validate_record({"ts": wl._now(), "wf": "w", "step": 1, "type": "action",
                                      "by": "A", "did": "run:x", "chain": None})
    check("分键：chain 显式 null 合法", okc, str(errs_c))
    r_streak = subprocess.run([sys.executable, str(HERE / "workflow_log.py"), "streak",
                               str(clog), "wfC", "3", "shard1"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("CLI streak 带 chain", "shard1" in r_streak.stdout and "达成" in r_streak.stdout,
          r_streak.stdout + r_streak.stderr)

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
