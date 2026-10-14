# -*- coding: utf-8 -*-
"""_test_vault_write.py —— S6 验收测试（沙箱在系统 temp；真实 git 操作零仓库写入）

覆盖（工程提炼 §2.2 / §5 S6）：
  1. 写入：文件落盘 + 自动 init git + commit（消息含 rel/reason/actor）
  2. 幂等：同内容重写 → 不产生新提交（committed=False）
  3. 防逃逸：rel 带 ../ → 拒绝
  4. 锁：被占用 → 超时友好报错；释放后可写；陈旧锁（>60s）自动回收
  5. 并发：两个进程同时写不同文件 → 串行成功、无死锁、各自落账
  6. 原子性：无 *.tmp 残留
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vault_write as vw  # noqa: E402

PY = sys.executable
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


def git(vault: Path, *args):
    return subprocess.run(["git", "-C", str(vault), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="vaultw_"))
    vault = tmp / "vault"
    vault.mkdir()

    print("== 1. 基本写入 ==")
    r1 = vw.write_node(vault, "20_角色/助理.md", "# 助理 v2\n", reason="更新能力描述", actor="human")
    check("文件已落盘", (vault / "20_角色/助理.md").read_text(encoding="utf-8") == "# 助理 v2\n")
    check("git 已自动初始化", (vault / ".git").exists())
    check("提交成功且消息含 rel/actor", r1["committed"] and "助理.md" in r1["head"] and "human" in r1["head"], str(r1["head"]))
    n1 = git(vault, "rev-list", "--count", "HEAD").stdout.strip()

    print("== 2. 幂等（同内容不新提交）==")
    r2 = vw.write_node(vault, "20_角色/助理.md", "# 助理 v2\n", reason="重复", actor="agent")
    n2 = git(vault, "rev-list", "--count", "HEAD").stdout.strip()
    check("committed=False 且提交数不变", (not r2["committed"]) and n1 == n2, "%s vs %s" % (n1, n2))

    print("== 3. 防逃逸 ==")
    try:
        vw.write_node(vault, "../evil.md", "x")
        check("../ 逃逸被拒", False)
    except ValueError as exc:
        check("../ 逃逸被拒", "逃出" in str(exc))

    print("== 4. 锁 ==")
    lock = vault / ".vault_lock"
    lock.write_text("hoarder", encoding="utf-8")
    t0 = time.time()
    try:
        vw.write_node(vault, "a.md", "x", lock_timeout=0.8)
        check("占用时超时报错", False)
    except TimeoutError:
        check("占用时超时报错（%.1fs 内）" % (time.time() - t0), (time.time() - t0) < 5)
    lock.unlink()
    r3 = vw.write_node(vault, "a.md", "内容A\n")
    check("释放后可写", r3["committed"])
    lock.write_text("stale", encoding="utf-8")
    old = time.time() - 120
    os.utime(lock, (old, old))
    r4 = vw.write_node(vault, "b.md", "内容B\n")
    check("陈旧锁自动回收并可写", r4["committed"] and not lock.exists())

    print("== 5. 并发（两进程同时写）==")
    p1 = subprocess.Popen([PY, str(HERE / "vault_write.py"), "write", "--vault", str(vault),
                           "--rel", "c.md", "--content", "C\n", "--actor", "p1"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    p2 = subprocess.Popen([PY, str(HERE / "vault_write.py"), "write", "--vault", str(vault),
                           "--rel", "d.md", "--content", "D\n", "--actor", "p2"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    o1, e1 = p1.communicate(timeout=60)
    o2, e2 = p2.communicate(timeout=60)
    check("p1 成功", p1.returncode == 0, (o1 or "") + (e1 or ""))
    check("p2 成功", p2.returncode == 0, (o2 or "") + (e2 or ""))
    check("两文件都在", (vault / "c.md").exists() and (vault / "d.md").exists())
    log = git(vault, "log", "--format=%s").stdout
    check("两个 commit 都落账", ("c.md" in log) and ("d.md" in log))

    print("== 6. 原子性 ==")
    leftovers = list(vault.rglob("*.tmp"))
    check("无 .tmp 残留", not leftovers, str(leftovers))

    print("== 7. git=False（编译链路：不 init、不 commit，审读 H4）==")
    vault2 = tmp / "vault_nogit"
    r7 = vw.write_node(vault2, "x.md", "X\n", reason="compile", actor="compile", git=False)
    check("文件已写、无 .git、committed=False",
          (vault2 / "x.md").exists() and not (vault2 / ".git").exists() and r7["committed"] is False, str(r7))
    check("无锁残留", not (vault2 / ".vault_lock").exists())

    print("== 8. 前缀逃逸（审读 L1：兄弟目录前缀不算 vault 内）==")
    sib = tmp / "vault_evil"
    sib.mkdir(exist_ok=True)
    try:
        vw.write_node(vault, "../vault_evil/x.md", "x")
        check("兄弟目录前缀逃逸被拒", False)
    except ValueError as exc:
        check("兄弟目录前缀逃逸被拒", "逃出" in str(exc), str(exc))

    print("\n结果：%d pass / %d fail" % (PASS, FAIL))
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
