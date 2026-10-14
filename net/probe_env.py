# -*- coding: utf-8 -*-
"""probe_env.py —— 关系网 v0.5 · 环境探测（§5.5）

纯确定性脚本，零 LLM。装机后跑一次 + 按需复跑，产出 env_snapshot.json：
机器事实（python / venv / Edge / Chrome / 默认浏览器）→ 编译节点 available 与 bias 的唯一事实源。
事实文件不进上下文（机器读，LLM 永不读）。

ⓝ 2026-09-27 归档进 net/ 子文件夹：关系网暂为设计构想（见《智能体关系网_设计梳理》v1.16），
   主线回到情绪模块（B3 记忆引擎）。本脚本与 compile_nodes.py 一并封存，解封时路径再接。

用法：python probe_env.py [输出路径=同目录 env_snapshot.json]
"""
import json
import os
import sys
import winreg
from datetime import datetime
from pathlib import Path

try:  # Windows 控制台默认 GBK：统一 UTF-8 输出（S1 适配）
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _first_existing(paths) -> str | None:
    for p in paths:
        if Path(p).exists():
            return p
    return None


def default_browser() -> str | None:
    """读注册表 UserChoice 的 https ProgId：ChromeHTML→chrome / MSEdgeHTM→edge。"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice",
        )
        prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        winreg.CloseKey(key)
        low = str(prog_id).lower()
        if "chrome" in low:
            return "chrome"
        if "msedge" in low or "edge" in low:
            return "edge"
    except Exception:
        pass
    return None


def probe() -> dict:
    edge = _first_existing(EDGE_PATHS)
    chrome = _first_existing(CHROME_PATHS)
    venv = os.environ.get("VIRTUAL_ENV")
    return {
        "schema": "env-snapshot/v1",
        "ts": datetime.now().isoformat(timespec="seconds"),
        "python": {"available": True, "path": sys.executable,
                   "version": f"{sys.version_info.major}.{sys.version_info.minor}"},
        "venv": {"available": bool(venv), "path": venv},
        "edge": {"available": bool(edge), "path": edge},
        "chrome": {"available": bool(chrome), "path": chrome},
        "default_browser": default_browser(),
    }


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "env_snapshot.json"
    snap = probe()
    out.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"env_snapshot OK: {out}")
    print(f"  python={snap['python']['available']} venv={snap['venv']['available']} "
          f"edge={snap['edge']['available']} chrome={snap['chrome']['available']} "
          f"default_browser={snap['default_browser']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
