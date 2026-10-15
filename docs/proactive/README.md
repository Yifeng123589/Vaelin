# Vaelin · Proactive Companion · Docs Pack（脱敏 · 本地 staging）

> **状态**：本地组装完成 · **未 push** · 非无护栏产品说明  
> **组装日**：2026-10-15（Asia/Shanghai）  
> **目标**：日后可迁入公开仓 Vaelin 的 `docs/proactive/`；本包仅本地 staging。

## 对外四句

1. Vaelin（留白）是研究原型：主动式陪伴＋本地护栏，不是医疗产品。  
2. 本目录是**设计叙事与观察结论的脱敏文档包**，不含生产护栏源码、词表全文或真实对话。  
3. 主动弧线装配源码已在公开／可公开面点名：`lead_proactive`（见仓内 `net/lead_proactive.py`＋单测）；本包**不重复拷贝**该源码。  
4. **本包未 push**；挂仓／Publish 须另拍。

## 白名单（本包内）

| 文件 | 对应 |
|---|---|
| `design_narrative.md` | 设计叙事脱敏（为何主动／边界陪伴） |
| `emotion_personality.md` | 情绪与性格设计要点（脱敏） |
| `passive_skeleton.md` | 被动式执行流程骨架（去生产路径） |
| `usage_guide.md` | 使用教程脱敏（合成示例） |
| `informed_consent.md` | 知情说明（对外伦理表述） |
| `observation_conclusions.md` | 观察期结论／数字摘要（禁对话原文） |
| `README.md` | 本文件 |

## 禁推（确认未纳入）

pre_guard／post_guard 生产副本 · scheduler 生产副本 · 危险词表全文 · 破甲危机细则全文 · 真实对话／audit 原文 · vault／SEALED · v0.4 zip 原样 · G2 论文全文 · q10 全量 replay · `lead_proactive` 物理拷贝（仅点名）

## lead_proactive（点名）

主动弧线装配已公开／可进仓源码面：`net/lead_proactive.py`（及 `_test_lead_proactive.py`）。本脱敏包只点名引用，不在此目录再拷一份。

## 声明

本包为研究叙事与观察摘要，**不是**完整可部署产品包，**不宣称**「无护栏即可上线」。生产护栏与危机处置链不在本包范围。
