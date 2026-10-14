#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""hermes_common.py —— 共享工具层（C7 去重）

被 pre_guard / scheduler / memory_engine / report 复用：时间、数值、JSON/JSONL IO、
小模型插槽与调用（含 C5① 失败分类）。**不做路径解析、导入无副作用**——
各模块自己解析 DATA 并把路径传进来。

部署：deploy.ps1 同步到 agent-hooks\\ 与 scripts\\ 两处（与各消费方同级）。

刻意不引入本模块的"安全孤岛"：
  · tool_gate.py（fail-closed：缺依赖会阻断全部工具，宁可自包含）
  · post_guard 插件（跨目录加载 + 自包含 SSRF 校验；PII 正则与 pre_guard 同源，
    由 tests/_test_pii.py 场景 10 防漂移）

口径说明（合并自两份历史实现）：
  · call_model 超时统一 DEFAULT_MODEL_TIMEOUT=8s（N4 实测值；调度器原 15s 一并收敛）
  · atomic_write_json / append_jsonl 统一带 mkdir（原 pre_guard 版缺）
  · read_jsonl_tail 统一默认 300 行（原 pre_guard 调用处默认 60，读更多行属向后兼容）
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

DEFAULT_MODEL_TIMEOUT = 8      # N4：单次小模型调用上限（复核+Δ 两串行最坏 16s ≪ hook 外层 60s）
LAST_MODEL_ERROR = ""          # C5①：最近一次 call_model 失败摘要（超时/限流/无 key/不可达）


# ── 时间 / 数值 ──────────────────────────────────────────
def now() -> datetime:
    return datetime.now().astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_ts(value: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


# ── JSON / JSONL IO ─────────────────────────────────────
def read_json(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def read_jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        return []
    rows: list[dict] = []
    for line in lines:
        try:
            record = json.loads(line)
        except Exception:
            continue
        if isinstance(record, dict):
            rows.append(record)
    return rows


def read_jsonl_tail(path: Path, max_lines: int = 300) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        return []
    rows: list[dict] = []
    for line in lines[-max_lines:]:
        try:
            record = json.loads(line)
        except Exception:
            continue
        if isinstance(record, dict):
            rows.append(record)
    return rows


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def parse_json_object(text: Optional[str]) -> Optional[dict]:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


# ── 小模型插槽与调用 ─────────────────────────────────────
def safe_base_url(url: str) -> bool:
    """SSRF 硬化（9/26 外部审查）：base_url 出自本地 agent_config.json（用户自己配），
    正常威胁模型下不构成 SSRF；仍校验 scheme 并拒绝云元数据/链路本地地址，
    防配置被意外写坏后把 API key / 对话内容发给意想不到的目标。
    loopback 放行（F1 本地模型路线要用 127.0.0.1 / localhost）。"""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    host = (parsed.hostname or "").lower()
    if host.startswith("169.254.") or host == "metadata.google.internal":
        return False
    return True


def load_api_key(slot: dict) -> str:
    env_name = str(slot.get("api_key_env") or "ZHIPU_API_KEY")
    key = os.environ.get(env_name, "")
    if key:
        return key
    env_file = slot.get("env_file")
    if env_file:
        try:
            for line in Path(env_file).read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(env_name):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def call_model(slot: dict, system: str, user: str, max_tokens: int = 120,
               timeout: int = DEFAULT_MODEL_TIMEOUT) -> Optional[str]:
    """返回模型文本；任何失败都返回 None（调用方负责降级）。失败摘要记入 LAST_MODEL_ERROR（C5①）。"""
    global LAST_MODEL_ERROR
    LAST_MODEL_ERROR = ""
    key = load_api_key(slot)
    if not key:
        LAST_MODEL_ERROR = "no_api_key"
        return None
    body = {
        "model": slot["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    try:
        req = urllib.request.Request(
            slot["base_url"],
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        LAST_MODEL_ERROR = f"{type(exc).__name__}: {exc}"[:160]
        return None
