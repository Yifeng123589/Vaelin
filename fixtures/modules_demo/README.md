# modules_demo — functional-domain modular relnet (demo seed)

**This tree is an example set, not a closed product enum.** Domains may be added, removed, or renamed; the five seeds below are a first-ship illustration only.

## What this is

Synthetic fixtures that show how a relationship net can be organized by **functional domains** (company-style operating functions): role cards map to domains, optional `owns:` fields are **demo-only**, and a sample workflow walks a fake cross-domain handoff.

## What this is not

- Not a production vault or sealed archive
- Not a claim that production shortlist routes by `owns:` — **production shortlist does not enable that field as a routing key**
- Not a fixed “five-module product definition”
- Not real people, real chats, API keys, or local absolute paths

## First-ship example domains (mutable)

| ID | Example domain (ZH) | Demo role file |
|---|---|---|
| M1 | 数据采集与分析 | `vault_seed_modules/M1_data_analytics.md` |
| M2 | 方案设计与策划 | `vault_seed_modules/M2_planning.md` |
| M3 | 工程落地与测试 | `vault_seed_modules/M3_engineering.md` |
| M4 | 营销与推广 | `vault_seed_modules/M4_outreach.md` |
| M5 | 反馈收集与打回 | `vault_seed_modules/M5_feedback.md` |
| Lead (optional) | 协调／派工示意 | `vault_seed_modules/00_lead_coord.md` |

Mapping narrative: [`docs/modules.md`](../../docs/modules.md). Sample trajectory: [`sample_workflow.json`](sample_workflow.json).

## Rules for contributors

- Keep cards **synthetic / redacted**
- Label any `owns:` as demo
- Do not paste production personas, real transcripts, secrets, or machine paths
