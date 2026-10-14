# Minimal demo

> Goal: an outsider can run **one** demo. Full 2550-game eval replay is **not** required.

## One sentence

**Minimal demo = run `net/` unit tests locally (zero API key, zero production writes).**
Optional advanced path = sandbox e2e (bring your own model API + compatible Hermes host; still do not touch production).

## Prerequisites

| Item | Requirement |
|---|---|
| OS | Windows 10+ (PowerShell) or Linux / WSL |
| Python | 3.10+ (`python` on your PATH) |
| Keys | **Path A needs no** model / cloud API key |
| Production | **Do not** point at a production host home, production vault, or live workflow log |

Repository root = the clone root of this repo.

## Path A (recommended · minimal)

At the repository root:

```powershell
cd <repo-root>
python net/_test_workflow_log.py
python net/_test_handoff.py
```

### Expected results

| Script | Result |
|---|---|
| `_test_workflow_log.py` | **27 pass / 0 fail** (validate / append / breaker counters / crash recovery / key split) |
| `_test_handoff.py` | **15 pass / 0 fail** (field checks / topology gate / execute stub / alias / fail-no-ledger) |

Both use a tempfile sandbox — **zero repo writes**, **zero production ledger writes**.

### What you are looking at

| Script | Mechanism |
|---|---|
| workflow_log | Ledger validation, breaker streak, `(wf, chain)` keying, bad-line tolerance |
| handoff | Required handoff fields, single lead router, execute→artifact+action, failure does not append action |

This is the public floor: routable, ledgered, breakable — without a live model.

## Path B (optional · live-model sandbox e2e)

> Advanced; **not** required for the minimal demo. Needs a Hermes chat backend + model API. Use an isolated sandbox home env; **never** a production home.

Optional e2e scripts are omitted from the first public drop when they embed machine-local paths. Prefer Path A for a reproducible zero-key floor.

## Explicitly out of scope

- Do not replay full q10 (2550) / do not run reference-target sources
- Do not copy production vaults / sessions / audit / events
- Do not change production plugin enable flags; do not install ACE in this demo
- Do not treat this demo as an unguarded companion product

See also: `PUBLIC.md`, `SECURITY.md`, `docs/exp/q10_summary.md`.
