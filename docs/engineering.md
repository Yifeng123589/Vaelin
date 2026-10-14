# vaelin · relnet engineering（public summary）

> How the working-layer net is built in layers.  
> Companion private notes may mention host-specific deploy wires; this public file stays host-portable.

## 1. Layering principle

All deterministic logic lives in a **pure Python kernel** (white-box). Host adapters are thin shells (plugin / MCP). Swapping hosts ≈ rewriting the shell, not the kernel.

## 2. Milestone ladder

| Milestone | Contents | Host dependency | Acceptance focus |
|---|---|---|---|
| **M0 kernel** | vault scaffold · write gateway · env probe/compile · shortlist · workflow_log schema＋appender＋breaker counters · weight kernel＋synthetic-log harness | **None** (pytest) | Pure-function suites |
| **M1 wire** | Lead closed loop (read vault → task sheet → dispatch → worker → action log) · thin plugin shells | Compatible host | One real task end-to-end in sandbox |
| **M2 write** | Score prior · live EMA · playbook propose＋human gate | Same | First playbook landed; weights move |
| **M3 run** | Real sub-agent spawn · hard tool separation · cross-check playbook · worker pool | Same | Parallel exec blueprint |
| **M4 proactive＋A/B** | Proactive redirect · criterion-3 A/B | Host(s) used in study | Published metrics |

Dependency chain: gateway → compile／shortlist／briefing; log schema → breaker／accountability; full kernel → host shell.

## 3. Public repo layout (target)

`
vaelin/
  README.md
  PUBLIC.md
  LICENSE
  SECURITY.md
  .gitignore
  net/                 # core library + _test_*.py
  hermes_plugins/      # relnet_inject / relnet_ledger / relnet_handoff shells
  fixtures/vault_seed/ # desensitized skeleton only
  docs/
    demo.md
    design.md
    engineering.md
    exp/q10_summary.md
`

Live companion vaults and session logs **do not** live in this repo.

## 4. Write gateway (M0 first piece)

Change-order fields (conceptual): timestamp, requester, vault-relative file, base version／hash, node type, reason, full new content.

Mechanisms:

1. **CAS** — stale base → reject and reread  
2. **External-edit absorb** — hash≠HEAD → record external_edit, bump version, then CAS  
3. **Typed approval** — specs/playbooks queue for humans; weights/experience apply  
4. **Atomic write** — temp file + replace, then git commit  
5. **Single-instance lock** — enough for personal scale  

Acceptance tests (idea): concurrent same-base (one wins); human bypass then stale submit (reject); spec queued; kill mid-write (no corruption); weight applies with audit line.

## 5. Other M0 pieces (names only)

- **probe/compile** — union of 
equires; multiplicative bias clamped  
- **shortlist** — visible ∩ available ∩ ranked score (+ε explore)  
- **workflow_log** — single appender; breaker = pure replay over (wf, chain)  
- **weight kernel** — EMA×κ + match_mult + clamps + decay; synthetic logs for mechanism-only drills (do not enter live pools)

## 6. Implementation status (public, as of 2026-10)

Already in the private working tree and intended for public 
et/ + plugin shells:

| Piece | Status (public wording) |
|---|---|
| workflow_log + validators | Implemented; unit tests green |
| shortlist / env compile | Implemented; unit tests green |
| empty-hop breaker counters | Implemented; default off until explicitly enabled |
| lead scheduling + inject shell | Implemented; **install ≠ enable** |
| ledger (post-tool action lines) | Implemented; **install ≠ enable** |
| multi-step executor | Implemented; sandbox e2e sequence dispatch/action legal |
| write gateway v0 | File lock + atomic write + git note; full CAS/approval = later hardening |
| weight / playbook evolution | Not required for first public demo |

**Demo path A (no API key):** run unit tests under 
et/_test_*.py (see docs/demo.md).

## 7. Safety / publish discipline

- Never commit .env, API keys, production vaults, real chat, or full eval replay dumps.  
- Plugin shells may ship **installed but disabled** until an operator opts in.  
- Fail-open on ledger／inject faults so a broken shell does not brick the host chat.  
- Public summary of mechanism experiments: docs/exp/q10_summary.md only.

## 8. What engineering.md is not

- Not a license to enable production plugins.  
- Not a dump of internal deploy checklists with machine-local paths.  
- Not the full private engineering diary.
