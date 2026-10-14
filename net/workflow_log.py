#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""workflow_log.py —— 关系网 · 工作流日志（落账 + 校验 + 熔断计数现算）

职责（工程提炼 §2.5 / 精简版 §10）：
  ① 落账：dispatch / handoff / action 三种记录，追加 JSONL（机器只写、人只读）
  ② 校验：字段定死、值可 null；未知字段拒绝；ts 必须可解析；type 枚举；**同 wf 时间序非倒退**（2026-09-29 审读 L8）
  ③ 熔断计数：从日志**现算**「连续无行动轮数」（崩溃恢复=重放日志，无独立状态文件）
  ④ 并发：追加走 _locked_append（锁文件 + flush/fsync，尽力而为）；统计/熔断读走
     read_records_lenient（容错跳坏行）；validate 仍走严格读（2026-09-29 审读 M4）

格式（字段定死）：
  dispatch / handoff : ts / wf / step / type / from / to / work / require
  action             : ts / wf / step / type / by / did / status / duration_s / tokens_in / tokens_out / cost_usd

计数语义（三分类，设计 §9）：
  action（hook 已在写入前验产物引用）→ 清零；handoff → +1；dispatch → 0 贡献（跳过）

用法：
  python workflow_log.py validate <log>
  python workflow_log.py streak <log> <wf> [N]

追加 API（供脚本 / 未来 hook 调用）：
  append_dispatch / append_handoff / append_action —— 先校验后追加，脏数据进不了日志
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认 GBK：统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TYPES = ("dispatch", "handoff", "action")

_COMMON = ("ts", "wf", "step", "type")
FIELDS = {
    "dispatch": _COMMON + ("from", "to", "work", "require", "chain"),
    "handoff": _COMMON + ("from", "to", "work", "require", "chain"),
    "action": _COMMON + ("by", "did", "status", "duration_s", "tokens_in", "tokens_out", "cost_usd", "chain"),
}
REQUIRED = {
    "dispatch": ("ts", "wf", "step", "type", "from", "to", "work"),
    "handoff": ("ts", "wf", "step", "type", "from", "to", "work"),
    "action": ("ts", "wf", "step", "type", "by", "did"),
}
# 这些字段允许显式 null / 缺省
NULLABLE = ("require", "status", "duration_s", "tokens_in", "tokens_out", "cost_usd", "chain")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def validate_record(rec) -> tuple[bool, list[str]]:
    """返回 (ok, 错误列表)。未知字段也拒绝——字段定死，消费者才敢依赖。"""
    errs: list[str] = []
    if not isinstance(rec, dict):
        return False, ["记录不是 dict"]
    t = rec.get("type")
    if t not in TYPES:
        return False, ["type 非法: %r" % (t,)]
    allowed = set(FIELDS[t])
    extra = sorted(set(rec) - allowed)
    if extra:
        errs.append("未知字段: %s" % extra)
    for k in REQUIRED[t]:
        v = rec.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            errs.append("必填缺失/空: %s" % k)
    ts = rec.get("ts")
    if isinstance(ts, str) and ts.strip():
        try:
            datetime.fromisoformat(ts)
        except Exception:
            errs.append("ts 不可解析: %r" % ts)
    return (not errs), errs


def _file_lock(fh):
    """尽力加锁：Windows msvcrt / POSIX fcntl；拿不到 → None（退化为不加锁仍写）。"""
    try:
        import msvcrt
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        return "msvcrt"
    except ImportError:
        pass
    except Exception:
        return None
    try:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        return "fcntl"
    except Exception:
        return None


def _unlock(fh, how) -> None:
    if not how:
        return
    with suppress(Exception):
        if how == "msvcrt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _locked_append(p: Path, line: str) -> None:
    """跨进程安全的单行追加：<log>.lock 加锁 + 写 + flush/fsync（尽力而为，锁失败仍写）。"""
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_fh, how = None, None
    try:
        lock_fh = open(str(p) + ".lock", "a+b")
        how = _file_lock(lock_fh)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            with suppress(Exception):
                os.fsync(fh.fileno())
    finally:
        if lock_fh is not None:
            _unlock(lock_fh, how)
            with suppress(Exception):
                lock_fh.close()


def append_record(log, rec: dict) -> dict:
    ok, errs = validate_record(rec)
    if not ok:
        raise ValueError("workflow_log 校验失败: " + "; ".join(errs))
    _locked_append(Path(log), json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def append_dispatch(log, wf: str, step, frm: str, to: str, work: str, require=None,
                    chain=None) -> dict:
    rec = {"ts": _now(), "wf": wf, "step": step, "type": "dispatch",
           "from": frm, "to": to, "work": work, "require": require}
    if chain:
        rec["chain"] = str(chain)[:64]
    return append_record(log, rec)


def append_handoff(log, wf: str, step, frm: str, to: str, work: str, require=None,
                   chain=None) -> dict:
    rec = {"ts": _now(), "wf": wf, "step": step, "type": "handoff",
           "from": frm, "to": to, "work": work, "require": require}
    if chain:
        rec["chain"] = str(chain)[:64]
    return append_record(log, rec)


def append_action(log, wf: str, step, by: str, did: str, status=None,
                  duration_s=None, tokens_in=None, tokens_out=None, cost_usd=None,
                  chain=None) -> dict:
    rec = {"ts": _now(), "wf": wf, "step": step, "type": "action",
           "by": by, "did": did, "status": status, "duration_s": duration_s,
           "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd}
    if chain:
        rec["chain"] = str(chain)[:64]
    return append_record(log, rec)


def read_records(log) -> list[dict]:
    p = Path(log)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def read_records_lenient(log) -> tuple[list[dict], int]:
    """容错读：坏行跳过并计数（熔断/统计路径用——崩掉=静默失明，比跳行更糟）。
    validate 命令仍走严格 read_records。返回 (记录列表, 坏行数)。"""
    p = Path(log)
    if not p.exists():
        return [], 0
    recs: list[dict] = []
    bad = 0
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            recs.append(json.loads(line))
        except Exception:
            bad += 1
    return recs, bad


def current_streak(records: list[dict], wf: str, chain=None) -> int:
    """当前连续无行动轮数：从该 (wf, chain) 的末尾往前数——
    handoff +1；dispatch 跳过（0 贡献）；action 停止（清零）。
    v1d 分键（工程提炼 §2.5）：按（wf，任务单链）计数；chain=None = 主链
    （旧日志无 chain 字段 → 同为主链，行为向后兼容）。"""
    streak = 0
    for rec in reversed(records):
        if str(rec.get("wf")) != wf:
            continue
        if (rec.get("chain") or None) != (chain or None):
            continue
        t = rec.get("type")
        if t == "handoff":
            streak += 1
        elif t == "action":
            break
        # dispatch 及其它：0 贡献，继续往前
    return streak


def should_break(records: list[dict], wf: str, n: int = 3, chain=None) -> bool:
    return current_streak(records, wf, chain) >= n


def _cmd_validate(log) -> int:
    p = Path(log)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines() if p.exists() else []
    bad = []
    last_ts: dict[str, datetime] = {}
    total = 0
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        total += 1
        try:
            rec = json.loads(line)
        except Exception as exc:
            bad.append((i, ["JSON 不可解析: %s" % exc]))
            continue
        ok, errs = validate_record(rec)
        if not ok:
            bad.append((i, errs))
        if not isinstance(rec, dict):
            continue
        # 时间序（同 wf）非倒退（审读 L8；同秒相等允许）
        wf = str(rec.get("wf") or "")
        ts = rec.get("ts")
        if wf and isinstance(ts, str):
            try:
                t = datetime.fromisoformat(ts)
            except Exception:
                t = None
            if t is not None:
                prev = last_ts.get(wf)
                if prev is not None and t < prev:
                    bad.append((i, ["时间序倒退（同 wf）：%s < 上一行 %s" % (ts, prev.isoformat())]))
                last_ts[wf] = t
    print("行数 %d，非法 %d" % (total, len(bad)))
    for i, errs in bad:
        print("  第 %d 行: %s" % (i, "; ".join(errs)))
    return 0 if not bad else 2


def _cmd_streak(argv) -> int:
    if len(argv) < 2:
        print("用法: python workflow_log.py streak <log> <wf> [N] [chain]")
        return 1
    log, wf = argv[0], argv[1]
    n = int(argv[2]) if len(argv) > 2 else 3
    chain = argv[3] if len(argv) > 3 else None
    records, bad = read_records_lenient(log)
    s = current_streak(records, wf, chain)
    print("wf=%s chain=%s 连续无行动轮数=%d（熔断阈值 N=%d）→ %s" %
          (wf, chain or "(主链)", s, n, "熔断条件达成" if s >= n else "未达成"))
    if bad:
        print("⚠ 跳过坏行 %d 行（计数可能偏小，建议跑 validate 排查）" % bad)
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "validate":
        return _cmd_validate(argv[1]) if len(argv) > 1 else 1
    if argv[0] == "streak":
        return _cmd_streak(argv[1:])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
