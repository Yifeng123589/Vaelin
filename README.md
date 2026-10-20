# Vaelin（留白）

**Working-layer relationship-net control plane** — dispatch, ledger, circuit-break, and human-review boundaries. Turns “split the task, hand it off, and leave an audit trail” into evolvable data — not a prettier one-line reply.

Tag: [`relnet-v1.0-rc1`](https://github.com/Yifeng123589/Vaelin/releases/tag/relnet-v1.0-rc1)

---

## See it in 30 seconds (local demo)

Fixture-only Web shell. **demo ≠ production**. No Hermes, no tunnel, no secrets.

```bat
cd demos\ui
start_demo.bat
```

Or any shell:

```bash
cd demos/ui
python -m http.server 8765 --bind 127.0.0.1
```

Open **http://127.0.0.1:8765/** (HTTP, not `file://`). Details: [`demos/ui/README.md`](demos/ui/README.md).

---

## Install (editable)

Python **≥ 3.10**. From the repository root:

```bash
pip install -e .
```

**Zero mandatory API key.** Install does not enable any host plugins (**install ≠ enable**).

Then run the floor check (same as Path A below):

```bash
vaelin-bootstrap
# or still:
python scripts/bootstrap.py
```

---

## Verify / developers (Path A floor tests)

Local unit tests only — tempfile sandbox, zero production writes, zero API key.

```bash
python scripts/bootstrap.py
```

Or the two tests directly:

```bash
python net/_test_workflow_log.py
python net/_test_handoff.py
```

Expected: workflow_log **27 pass**; handoff **15 pass**.

What those scripts cover: [`docs/demo.md`](docs/demo.md). Optional live-model sandbox is not part of this floor.

---

## What it is not (short)

Not a drop-in replacement for a general agent framework. Not an unguarded companion product. The public demo is not that product. q10 is a **floor / mechanism** segment, not a claim of organization-level long-horizon superiority. Forks that strip companion guardrails must not reuse the **Vaelin / 留白** name or safety claims.

Full publish / exclusion boundary: [`PUBLIC.md`](PUBLIC.md). Security: [`SECURITY.md`](SECURITY.md).

---

## Layout

| Path | Role |
|---|---|
| `demos/ui/` | Local Web UI demo shell (fixture-only; **demo ≠ production**) |
| `net/` | Core library (handoff / executor / workflow_log / lead* / vault I/O) |
| `net/_test_*.py` | Unit tests (Path A) |
| `scripts/bootstrap.py` | Path A one-shot layout check + unit tests |
| `vaelin/` | Installable package entry (`vaelin-bootstrap`) |
| `hermes_plugins/relnet_*` | Plugin shells; need a compatible Hermes host; **install ≠ enable** |
| `fixtures/` | Synthetic / redacted seeds and module demos |
| `docs/` | Design excerpts, demo notes, q10 summary |
| [`PUBLIC.md`](PUBLIC.md) / [`SECURITY.md`](SECURITY.md) / [`LICENSE`](LICENSE) | Boundary · security · MIT |

---

## Community

Discussions are off. [Issue #1](https://github.com/Yifeng123589/Vaelin/issues/1) is the launch thread for Path A results and questions. Share **redacted or synthetic** notes only — no production sessions, real chats, secrets, or unredacted replays.

---

## 中文（留白）

工作层关系网控制面：派工、落账、熔断、人审边界。

- **先看演示**：`cd demos/ui` → `start_demo.bat`（或 `python -m http.server 8765 --bind 127.0.0.1`）→ 打开 http://127.0.0.1:8765/ · **demo ≠ production**
- **安装**：`pip install -e .`（Python ≥3.10；零强制 API key；**install ≠ enable**）
- **验证**：`vaelin-bootstrap` 或 `python scripts/bootstrap.py` → 期望 workflow_log **27**／handoff **15** pass

不是通用 Agent 框架替代品，也不是无护栏陪伴产品。边界见 [`PUBLIC.md`](PUBLIC.md)。

---

## License

MIT — see [`LICENSE`](LICENSE).

## Security

See [`SECURITY.md`](SECURITY.md). Do not open public issues for security-sensitive reports. Prefer [private vulnerability reporting](https://github.com/Yifeng123589/Vaelin/security/advisories).
