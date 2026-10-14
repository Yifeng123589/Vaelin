#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""vault_write.py —— 关系网 · S6 写入网关 v0（v0.5 降级版）

职责（工程提炼 §2.2；设计 §5.5 的 v0.5 子集）：
  ① 单例文件锁：写者串行（陈旧锁自动回收，超时友好报错）
  ② 原子写：.tmp + os.replace（同卷原子）
  ③ 目录内 git：自动 init + 每次写入 commit（diff 即审计）

v0.5 不含（留 v1，见工程提炼 §4）：CAS/version 校验、外改检测收编、分级审批路由。

用法：
  python vault_write.py write --vault fixtures/vault_seed --rel "20_角色\\助理.md" \\
      --content-file new.md --reason "更新能力描述" --actor human
  python vault_write.py write ... --content "直接文本" [--dry-run] [--lock-timeout 10]
  python vault_write.py check --vault fixtures/vault_seed

纪律：agent 写 vault 一律走本网关（单一写者）；人用 Obsidian 直改由 v1 外改收编处理。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认 GBK：统一 UTF-8 输出
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCK_NAME = ".vault_lock"
STALE_LOCK_SECONDS = 60
LOCK_TIMEOUT_SECONDS = 10
LOCK_POLL = 0.2
GIT_ID = ("vault-gateway", "vault@local")  # 本机无全局 git 身份时的网关身份


def _git(vault: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(vault), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def ensure_repo(vault: Path) -> None:
    """目录内自建 git（与运行日志分家）。幂等。"""
    if (vault / ".git").exists():
        return
    vault.mkdir(parents=True, exist_ok=True)
    _git(vault, "init", "-q")
    _git(vault, "config", "user.name", GIT_ID[0])
    _git(vault, "config", "user.email", GIT_ID[1])
    _git(vault, "add", "-A")
    _git(vault, "commit", "-q", "-m", "vault: 初始提交（网关自动）")  # 空目录会失败，忽略


class VaultLock:
    """单例文件锁：O_CREAT|O_EXCL 抢占；陈旧锁（>60s）自动回收；超时友好报错。"""

    def __init__(self, vault: Path, timeout: float = LOCK_TIMEOUT_SECONDS):
        self.path = Path(vault) / LOCK_NAME
        self.timeout = timeout

    def __enter__(self):
        start = time.time()
        while True:
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("ascii", "ignore"))
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                    if age > STALE_LOCK_SECONDS:
                        self.path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.time() - start > self.timeout:
                    raise TimeoutError("vault 被占用（锁超时 %.1fs）：%s" % (self.timeout, self.path))
                time.sleep(LOCK_POLL)

    def __exit__(self, *exc):
        try:
            self.path.unlink(missing_ok=True)
        except Exception:
            pass
        return False


def write_node(vault: Path, rel: str, content: str, reason: str = "", actor: str = "agent",
               dry_run: bool = False, lock_timeout: float = LOCK_TIMEOUT_SECONDS,
               git: bool = True) -> dict:
    """写一个节点。git=False → 跳过 ensure_repo/commit（compile 链路在 vault 独立 git
    落地前使用：vault 目前嵌在主仓内，防嵌套；审读 M5）。锁与原子写不受影响。"""
    vault = Path(vault)
    target = vault / rel
    # 防逃逸：rel 必须落在 vault 内（审读 L1：补 os.sep，杜绝 "agent_vault_evil" 前缀绕过）
    vault_r = os.path.normcase(str(Path(vault).resolve()))
    target_r = os.path.normcase(str(Path(target).resolve()))
    if target_r != vault_r and not target_r.startswith(vault_r + os.sep):
        raise ValueError("rel 路径逃出 vault：%s" % rel)
    if dry_run:
        return {"ok": True, "dry_run": True, "target": str(target)}
    if git:
        ensure_repo(vault)
    else:
        vault.mkdir(parents=True, exist_ok=True)
    with VaultLock(vault, timeout=lock_timeout):
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            try:
                os.fsync(fh.fileno())   # 审读 L9：tmp 先落盘再 replace（掉电场景）
            except OSError:
                pass
        os.replace(str(tmp), str(target))               # 原子写
        committed, head = False, ""
        if git:
            _git(vault, "add", "--", rel)
            msg = "write: %s | %s | by %s | %s" % (
                rel, reason or "-", actor, datetime.now().astimezone().isoformat(timespec="seconds"))
            rc = _git(vault, "commit", "-q", "-m", msg).returncode
            committed = (rc == 0)
            head = _git(vault, "log", "-1", "--format=%h %s").stdout.strip()
        leftovers = list(target.parent.glob("*.tmp"))
    return {"ok": True, "target": str(target), "committed": committed, "head": head,
            "tmp_leftovers": len(leftovers)}


def cmd_check(vault: Path) -> int:
    vault = Path(vault)
    info = {"vault": str(vault), "exists": vault.exists(),
            "git": (vault / ".git").exists(),
            "lock_present": (vault / LOCK_NAME).exists()}
    if info["git"]:
        info["head"] = _git(vault, "log", "-1", "--format=%h %s").stdout.strip()
        info["commits"] = _git(vault, "rev-list", "--count", "HEAD").stdout.strip()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "check"])
    ap.add_argument("--vault", required=True)
    ap.add_argument("--rel", default=None)
    ap.add_argument("--content", default=None)
    ap.add_argument("--content-file", default=None)
    ap.add_argument("--reason", default="")
    ap.add_argument("--actor", default="agent")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lock-timeout", type=float, default=LOCK_TIMEOUT_SECONDS)
    args = ap.parse_args()

    vault = Path(args.vault)
    if args.cmd == "check":
        return cmd_check(vault)

    if not args.rel:
        print("write 需要 --rel")
        return 1
    if args.content_file:
        content = Path(args.content_file).read_text(encoding="utf-8")
    elif args.content is not None:
        content = args.content
    else:
        print("write 需要 --content 或 --content-file")
        return 1
    try:
        result = write_node(vault, args.rel, content, reason=args.reason, actor=args.actor,
                            dry_run=args.dry_run, lock_timeout=args.lock_timeout)
    except (ValueError, TimeoutError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
