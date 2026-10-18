# vaelin (留白) · relnet

Working-layer relationship-net control plane: turn “split the task, hand it off, and leave an audit trail” into evolvable data — not a prettier one-line reply.

**Tag:** [`relnet-v1.0-rc1`](https://github.com/Yifeng123589/Vaelin/releases/tag/relnet-v1.0-rc1)

## What it is / is not

1. **What it is.** A working-layer relationship net (vaelin / 留白): dispatch, ledger, circuit-break, and human-review boundaries.
2. **What it is not.** Not a drop-in replacement for a general agent framework. Not an unguarded companion product. The public demo is not that product. q10 is a **floor / mechanism** segment (strategy–iteration coupling), not a claim of organization-level long-horizon superiority. Forks that strip companion guardrails must not reuse the **Vaelin / 留白** name or safety claims.
3. **How to run.** See [`docs/demo.md`](docs/demo.md). Minimal path = local unit tests, zero API key. Optional end-to-end needs a model API you supply. Hermes plugin shells: **install ≠ enable**.
4. **Data.** No user conversations by default. Research material is the q10 **summary only**: [`docs/exp/q10_summary.md`](docs/exp/q10_summary.md). Scope and exclusions: [`PUBLIC.md`](PUBLIC.md).

## Quick start (Path A · recommended)

Python 3.10+. From the repository root (PowerShell, or any shell with `python` on `PATH`):

One-shot (layout check + both Path A tests):

```powershell
python scripts/bootstrap.py
```

Or run the two tests directly (equivalent):

```powershell
python net/_test_workflow_log.py
python net/_test_handoff.py
```

Expected: workflow_log **27 pass**; handoff **15 pass** (tempfile sandbox, zero production writes, zero API key).

What those scripts cover is listed in [`docs/demo.md`](docs/demo.md). Path B (live-model sandbox) is optional and is not part of this floor.

## Layout

| Path | Role |
|---|---|
| `net/` | Core library (handoff / executor / workflow_log / lead* / vault I/O) |
| `net/_test_*.py` | Unit tests (Path A) |
| `hermes_plugins/relnet_*` | Plugin shells (inject / ledger / handoff); require a compatible Hermes host; **install ≠ enable** |
| `fixtures/vault_seed/` | Synthetic / redacted role skeletons only |
| `docs/` | Design and engineering excerpts, demo, q10 summary |
| [`PUBLIC.md`](PUBLIC.md) / [`SECURITY.md`](SECURITY.md) / [`LICENSE`](LICENSE) | Boundary · security · MIT |

## Community

Discussions are off. [Issue #1](https://github.com/Yifeng123589/Vaelin/issues/1) is the launch thread for Path A results and questions. Share **redacted or synthetic** notes only — no production sessions, real chats, secrets, or unredacted replays.

## 中文（留白）

工作层关系网控制面：派工、落账、熔断、人审边界。不是通用 Agent 框架替代品，也不是无护栏陪伴产品；q10 只是地板／机制段证据。最小试用即上文 Path A（**27 / 15 pass**，零 API key）。边界见 [`PUBLIC.md`](PUBLIC.md)。

## License

MIT — see [`LICENSE`](LICENSE).

## Security

See [`SECURITY.md`](SECURITY.md). Do not open public issues for security-sensitive reports. Prefer [private vulnerability reporting](https://github.com/Yifeng123589/Vaelin/security/advisories).
