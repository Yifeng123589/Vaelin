# q10 experiment · public summary

> This file is a **summary only**（public-repo policy G3）.  
> It does **not** include: full 2550-game replay dumps, reference-target source, or the full preregistration body.

## What q10 is

q10 is a **floor／mechanism** segment for the relnet working layer on a **strategy–iteration coupling** task
（write→run→inspect→edit a small bot under a fixed time gate）.

It is **not** the validation field for organization-level long-horizon hypotheses（those belong to a separate real-task anchor line）.

Registered roles（preregistration framing）:

| # | Role | Meaning |
|---|---|---|
| F1 non-inferiority | On non-home turf, C must not hurt correctness vs A, and must not fall far below A on strength | Bidirectional pre-declaration: A≥C can be an **expected** boundary outcome |
| F2 mechanism | Full chain（task sheet／workflow_log／breaker／multi-step exec／knowledge inject）runs and audits | Logs legal; breaker／fallback auditable |
| F3 process | Iteration discipline／observation behavior measurable | Process metrics only |

## Design in one table

| Item | Setting |
|---|---|
| Arms | A solo agent · B fixed 3-step workflow · C relnet full chain |
| Budget | Pure **time gate ≤60 min**／run；play／token counted, not capped |
| Eval pool | Ladder bots ＋ one fixed external reference target（**play only, never read source**） |
| Scale | Strength 900 ＋ round-robin 1530 ＋ negative-control 120 ＝ **2550** games |
| Preregistration | v1.4 signed（pure time gate ＋ 2550 pool） |

## Headline results（report v1, post red-flag rulings）

Ordering on this task: **A > C > B**.

- **F1 correctness holds**: illegal moves **0** across arms; own forfeits **C=0 ≤ A=5**（A's five from one crashed bot）→ 「不该用也不伤」holds.
- **F1 strength non-inferiority does not hold**: C−A Elo ≈ **−192.8**（95% CI about **−246 … −150**）, below the registered margin → falls on the **pre-declared expected side（A≥C）**; reported as-is, **not** an architecture failure claim.
- **C vs B is a positive signal**: C−B Elo ≈ **+453**; C beats B in ~**94%** of mutual games.
- **Negative control passes**: walls=0 → three arms tie ~50%（coupling removed ⇒ differences vanish）.

### Boundary statements（do not over-claim）

1. On this strategy–iteration task, relnet did **not** show strength superiority over solo agent; correctness did not regress; the mechanism ran.
2. Relnet's clearer contrast here is vs **fixed workflow**（lifting a weak process）, not 「beat solo agent」.
3. No claim of statistical significance as a sole headline（n=6／arm; report effect sizes＋CI）.
4. No claim of optimal routing／organization evolution; no extrapolation beyond q10.

## What stays private

- Full replay JSONL／frozen run artifacts
- Reference-target source used only in the eval pool
- Full preregistration markdown body and deviation log entries that may contain session detail
- Production Hermes home、audit streams、personal vault cards

## Reproduce the public floor（no eval corpus needed）

See the repo demo path（unit tests under `net/_test_*.py`）——mechanism floor without API keys.
