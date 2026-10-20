# PUBLIC · What is in this repository

## Goal

Outsiders should understand and **minimally run** the relnet / vaelin（留白）working-layer control plane:
dispatch, workflow log, circuit-break, and human-review boundaries — with design notes, core code, and one demo path.

This tree does **not** ship companion production sessions, full eval corpora, secrets, or unredacted research materials.

## Published by default

| Category | Contents |
|---|---|
| Design / engineering | Public excerpts of the relnet design＋engineering notes（no internal ticket voice, no secrets） |
| Core library | `net/` sources without keys |
| Plugin shells | `hermes_plugins/relnet_inject`／`relnet_ledger`／`relnet_handoff`（Hermes version range noted; **install ≠ enable**） |
| Tests | `net/_test_*.py` and demo docs（no API keys） |
| Vault seed | **Synthetic／redacted** role skeletons only（never production vault） |
| Experiment summary | q10 report **conclusion＋preregistration abstract** only（see `docs/exp/q10_summary.md`） |
| Meta | `LICENSE`（MIT）、`SECURITY.md`、this `PUBLIC.md` |
| Root UX entry | Root `README.md` first-run path + `demos/ui/` local Web demo shell (fixture-only; **demo ≠ production**; non-production) |

## Not published（default）

| Category | Examples | Why |
|---|---|---|
| Secrets / env | `.env`、API keys、live config key paths | Safety |
| Production sessions | Hermes events／audit、real user chats、memory stores | Privacy／ethics |
| Production vault | Personal companion／assistant cards | Privacy |
| Full q10 artifacts | Full 2550-game replay dumps、frozen tarballs、reference-target source | Size＋target-copying risk（G3＝summary only） |
| Guardrail internals | Full crisis／jailbreak lexicons and bypass-sensitive tables | Separate disclosure review |
| Parallel papers | Paper-1／「无感测评」full texts | **Late／separate repo**（G2） |

## Settled scope decisions

| Item | Decision |
|---|---|
| Repo shape | Independent public repo **`vaelin`（留白）** — not a trimmed slice of the private product tree |
| Paper-1／无感 docs | **Late／separate** — not in first release |
| q10 materials | **Summary only** — no full replay／reference-target source／full preregistration body |
| License | **MIT** |
| Distribution form（web vs desktop） | Deferred; does not block first release |

## Claims discipline

- q10 is a **floor／mechanism** segment（strategy–iteration coupling）, not a claim of organization-level long-horizon superiority.
- Public demo ≠ unguarded companion product.
- Forks that strip companion guardrails must not reuse the **Vaelin／留白** name or safety claims.
