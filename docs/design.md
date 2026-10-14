# vaelin · relnet design（public excerpt）

> Public excerpt of the working-layer relationship network design.  
> Full internal design history stays private; this file is the stable external view.

## 1. One-sentence positioning

Companion / reply-layer modules answer **how to say one line well**.  
**relnet** answers **how to get one job done** (working layer): split the task, pick who runs it, follow which playbook, and leave an audit trail.

| Layer | Owns | Analogy |
|---|---|---|
| Reply layer | Generation, safety, emotion, memory per turn | An employee's voice |
| Working layer (relnet) | Task split, routing, SOP, audit | Org chart + SOP |

Control flow is **runtime data** (markdown vault people and agents co-write), not a graph frozen only in developer code.

## 2. Proof it is not a toy

**Delete test** — if removing a piece does not hurt anything measurable, do not build it.

| Remove | What breaks |
|---|---|
| vault | Lead has nothing to read; workflow decisions vanish |
| weights | Routing collapses to fixed order / random |
| playbooks | Same-class tasks replan from zero every time |
| empty-hop breaker | Ping-pong / empty handoffs run away |
| env compile | Routes hit missing local tools and burn calls |

**Load-bearing order (hard → soft):** cost (tools + local context) → reuse (playbooks) → human-editable control flow (md in a vault).

**Falsifiable check (criterion 3):** same N tasks, with-net vs without-net — token cost, rounds, second-run marginal cost, handoff success / breaker rate. Flat metrics ⇒ toy.

## 3. Concept model

### 3.1 Nodes

- **Lead**: only node allowed to query the full net; decision is a pure function of vault + workflow_log + task sheet (+ explicit seed). No chat context.
- **Real sub-agent**: own session + tools (heavy experts).
- **Character card**: inject behavior constraints + tool list + playbook into the current turn (majority of daily work).
- **Librarian**: curates specs / indexes; does not own the storage itself.
- **Knowledge nodes**: playbooks, experience notes, project coupling (implicit only), specs.

### 3.2 Edges

| Edge | Who writes | Meaning |
|---|---|---|
| knows (static) | Human frontmatter | Visibility — workers only see who they know |
| weight (dynamic) | Deterministic formula | Deeper relation → higher handoff priority |

One directed weight per outbound edge, stored on the **source** node only (single ownership).

### 3.3 Playbooks

Successful workflows may be proposed → **human approve** → stored as nodes. Next similar job: lead loads playbook and tweaks, instead of planning from zero.

Default skeleton (borrowed execution pattern, original learning layer kept): plan → prd → exec → verify → fix loop; verify requires machine-readable evidence.

### 3.4 Parallelism

Workers can be spawned as a pool slicing one task list (independent breaker keys per worker). Cross-role redirects go **only back to the lead** (lead is the sole router).

## 4. Vault shape (small start, large schema)

Start ≤ ~30 nodes. Suggested departments:

`
agent_vault/
  _index.md
  00_lead/
  10_experts/
  20_roles/
  30_playbooks/     # fills in later
  40_experience/    # fills in later
  50_memory/        # optional reply-layer partition
  90_archive/
`

Frontmatter essentials: 	ype, 
orm, 	ools, 
equires, knows, capability, outbound weight, 
ersion.

**Write gateway (single channel):** every agent write = change order → CAS on version／hash → typed approval (specs/playbooks human; weights/experience auto) → atomic write + git commit. External human edits are detected and absorbed before overwrite.

## 5. Runtime ladder

| Stage | What |
|---|---|
| v0.5 probe | Env probe → compile vailable / initial bias |
| v1 read | Lead picks people; inject cards; empty-hop breaker watches |
| v2 write | Edge weights update; playbook propose＋human gate |
| v3 run | Real sub-agents with hard tool separation |

**Proactive path:** existing scheduler gates stay; exit is redirected to the lead to start a workflow instead of generating a reply directly.

## 6. Empty-hop breaker

Pure script, zero LLM tokens. Counts per (workflow, chain) key:

- productive tool action with artifact → reset
- handoff → +1
- dispatch / lead route / unknown tools → 0 contribution

Threshold → force solo / escalate to human. Fail-open on instrumentation faults.

## 7. Routing sketch (public)

Score blends quality / speed / cost factors, optional external cost prior + residual, env bias, and demand–profile match multiplier. Learning signals must come from the **user side** (no self-certifying loops). Personal-PC sample sizes are small — treat evolution as mild preference shift unless you have high volume.

## 8. What this public excerpt is not

- Not a replacement for a general agent framework.
- Not the companion safety paper / unobtrusive-assessment line (those ship later / elsewhere).
- Not production session logs, live vaults, or API keys.

See also: PUBLIC.md, docs/demo.md, docs/engineering.md, docs/exp/q10_summary.md.
