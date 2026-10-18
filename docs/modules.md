# Functional-domain modules (demo axis)

> **Example set, not a closed enum.** The domains below are a first-ship demonstration seed. They may be added, removed, or renamed without implying a fixed “five-module product.”

## Purpose

Show how a public relationship-net demo can be organized by **functional domains** (company-style operating functions): domain → synthetic role card → optional demo `owns:` → sample handoff steps.

This is a **demo axis**. It does **not** change production routing. In particular:

- **`net/shortlist.py` is unchanged** by this pack
- Demo `owns:` on fixture cards is **not** enabled as a production shortlist routing key
- No Hermes deploy, no production vault migration, no real personas

Related internal note (not required to run Path A): organization/编制 may align to modules in a separate signed change; this public pack only illustrates the shape.

## Example domain ↔ fixture map

| ID | Example domain | Synthetic card | Sample workflow step |
|---|---|---|---|
| M1 | 数据采集与分析 (input / insight) | [`fixtures/modules_demo/vault_seed_modules/M1_data_analytics.md`](../fixtures/modules_demo/vault_seed_modules/M1_data_analytics.md) | `ingest_signals` |
| M2 | 方案设计与策划 (proposal) | [`…/M2_planning.md`](../fixtures/modules_demo/vault_seed_modules/M2_planning.md) | `draft_options` |
| M3 | 工程落地与测试 (implement + verify) | [`…/M3_engineering.md`](../fixtures/modules_demo/vault_seed_modules/M3_engineering.md) | `implement_and_test` |
| M4 | 营销与推广 (external reach) | [`…/M4_outreach.md`](../fixtures/modules_demo/vault_seed_modules/M4_outreach.md) | `prepare_public_note` |
| M5 | 反馈收集与打回 (close-loop) | [`…/M5_feedback.md`](../fixtures/modules_demo/vault_seed_modules/M5_feedback.md) | `collect_and_route_back` |
| Lead (optional) | 协调／派工 | [`…/00_lead_coord.md`](../fixtures/modules_demo/vault_seed_modules/00_lead_coord.md) | — |

Tree README: [`fixtures/modules_demo/README.md`](../fixtures/modules_demo/README.md).  
Sample trajectory: [`fixtures/modules_demo/sample_workflow.json`](../fixtures/modules_demo/sample_workflow.json).

## How to read this vs Path A

- Path A (`python scripts/bootstrap.py` or the two `net/_test_*.py` scripts) remains the **floor**: layout + unit tests, zero API key.
- This modules demo is **documentation + synthetic fixtures** for reviewers who want a functional-domain mental model. It does not replace Path A and does not claim production module dispatch is live.
