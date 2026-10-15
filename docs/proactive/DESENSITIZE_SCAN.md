# 脱敏扫描记录 · 2026-10-15

> staging 根：`_vaelin_stage/docs/proactive/`  
> 时区：Asia/Shanghai

| # | 检查 | 结果 | 备注 |
|---|---|---|---|
| S1 | 密钥／token（sk-／api_key／Bearer／.env 实体值） | PASS | 无实体密钥；教程仅原则说明 |
| S2 | 私人邮箱／手机号模式 | PASS | 知情／教程仅保留公开热线类别表述；未贴私人号 |
| S3 | 本机绝对路径 | PASS | 已改为占位／相对仓内路径；无 `<USERPROFILE>/...` |
| S4 | 真实对话大段粘贴 | PASS | 观察结论去原文；叙事／教程用合成示意 |
| S5 | 护栏细表（危险词表／pre_guard／post_guard 全文） | PASS | 未纳入；骨架仅概念表 |
| S6 | vault／SEALED | PASS | 未纳入 |
| S7 | v0.4 zip／G2 全文／q10 replay | PASS | 未纳入 |
| S8 | 白名单 W1–W5＋W6 点名 | PASS | 见文件列表；lead_proactive 仅 README 点名 |
| S9 | 包级声明 | PASS | README 含脱敏／未 push／非无护栏产品 |

**总评**：PASS（可审查本地 staging；**未 push**）
