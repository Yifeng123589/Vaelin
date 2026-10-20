#!/usr/bin/env python3
"""Path A one-shot entry for editable installs (`vaelin-bootstrap`).

Delegates to the same layout check + floor tests as ``scripts/bootstrap.py``.
Zero API key; does not touch production Hermes, deploy, or production vaults.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REQUIRED_PATHS = (
    Path("net"),
    Path("net/_test_workflow_log.py"),
    Path("net/_test_handoff.py"),
    Path("fixtures"),
    Path("docs"),
    Path("README.md"),
    Path("PUBLIC.md"),
)

PATH_A_TESTS = (
    Path("net/_test_workflow_log.py"),
    Path("net/_test_handoff.py"),
)


def repo_root() -> Path:
    """Locate the public-repo root (editable checkout or cwd fallback)."""
    here = Path(__file__).resolve().parent
    candidate = here.parent
    if (candidate / "net" / "_test_workflow_log.py").exists():
        return candidate
    return Path.cwd()


def check_layout(root: Path) -> list[str]:
    missing: list[str] = []
    for rel in REQUIRED_PATHS:
        if not (root / rel).exists():
            missing.append(str(rel).replace("\\", "/"))
    return missing


def run_test(root: Path, rel: Path) -> int:
    cmd = [sys.executable, str(rel)]
    print(f"==> running: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=root)
    return int(completed.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vaelin-bootstrap",
        description=(
            "Verify Vaelin public-repo layout and run Path A floor tests "
            "(workflow_log + handoff). Zero API key; no production Hermes or deploy touch."
        ),
    )
    parser.parse_args(argv)

    root = repo_root()
    missing = check_layout(root)
    if missing:
        sys.stderr.write(
            "bootstrap layout check FAILED; missing:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n"
        )
        return 1

    print("layout OK")
    failures = 0
    for rel in PATH_A_TESTS:
        code = run_test(root, rel)
        if code != 0:
            failures += 1
            sys.stderr.write(f"test FAILED: {rel.as_posix()} (exit {code})\n")

    passed = len(PATH_A_TESTS) - failures
    if failures:
        sys.stderr.write(
            f"bootstrap FAILED: {passed}/{len(PATH_A_TESTS)} Path A tests passed\n"
        )
        return 1

    print(f"bootstrap PASS: layout OK; Path A {passed}/{len(PATH_A_TESTS)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
