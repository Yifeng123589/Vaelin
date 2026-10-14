# vaelin（留白）· relnet

工作层关系网控制面：把「拆任务、交给谁、如何审计」做成可进化数据，而不是只调一句回复。

## 对外四句

1. **是什么**：工作层关系网（vaelin／留白）——派工、落账、熔断、人审边界。
2. **不是什么**：不是通用 Agent 框架替代品；不是无护栏的陪伴产品；q10 只是地板／机制段证据。
3. **怎么跑**：见 [`docs/demo.md`](docs/demo.md)（最小＝本机单测，零 API key）；需要自备模型 API 才做可选 e2e。Hermes 插件默认**装≠启用**。
4. **数据**：默认无用户对话；研究材料见 [`docs/exp/q10_summary.md`](docs/exp/q10_summary.md)（**摘要 only**）。边界见 [`PUBLIC.md`](PUBLIC.md)。

## Quick start（路径 A · 推荐）

需要 Python 3.10+。在仓库根：

```powershell
python net/_test_workflow_log.py
python net/_test_handoff.py
```

期望：workflow_log **27 pass**；handoff **15 pass**（临时目录沙箱，零生产写入）。

## Layout

| Path | Role |
|---|---|
| `net/` | Core library（handoff／executor／workflow_log／lead*／vault I/O） |
| `net/_test_*.py` | Unit tests（路径 A） |
| `hermes_plugins/relnet_*` | Plugin shells（inject／ledger／handoff）；require compatible Hermes |
| `fixtures/vault_seed/` | Synthetic／redacted role skeletons only |
| `docs/` | Design／engineering excerpts＋demo＋q10 summary |
| `PUBLIC.md` / `SECURITY.md` / `LICENSE` | Boundary · security · MIT |

## License

MIT — see [`LICENSE`](LICENSE).

## Security

See [`SECURITY.md`](SECURITY.md). Do not open public issues for security-sensitive reports.
