# Security Policy

## Supported surface

This repository publishes the **relnet / vaelin (留白) working-layer** control plane:
handoff, workflow log, ledger/inject plugin shells, and related docs/tests.

It is **not** a drop-in companion product. Production guardrails, crisis pipelines,
and live user sessions are **out of scope** for this public tree (see `PUBLIC.md`).

## Data defaults

- **No user conversations** are included by default.
- **No production vault** contents, API keys, `.env`, or live `workflow_log` are shipped.
- Demo fixtures (when present) are **synthetic / redacted** skeletons only.
- Research artifacts (e.g. q10) ship as **summaries only** unless a separate data policy says otherwise.

## What we do not publish (safety)

- Full crisis / jailbreak lexicons and bypass-sensitive guardrail internals
- Production Hermes home, audit/event streams, or personal role cards
- Reference-target source used in registered evals (to avoid target copying)

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive reports.

Prefer:

1. GitHub **Private vulnerability reporting** / Security Advisory: https://github.com/Yifeng123589/Vaelin/security/advisories
2. Or contact the maintainer via the profile linked from the repo (`Yifeng123589`).

Include: affected path/version, impact, and a minimal reproduction **without** real user data.

## Guardrail / identity note

Removing or disabling companion guardrails in a fork is outside this project's identity.
Do not reuse the **Vaelin / 留白** name or safety claims for unguarded derivatives.
(Full product identity text lives in the private/product tree `SAFETY.md`, not duplicated here.)

## Dependencies

Runtime needs a model API of your choice and (for plugin shells) a compatible Hermes host.
Those vendors' security terms apply separately; this repo does not proxy or store your keys.
