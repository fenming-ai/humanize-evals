# 数据目录

- benchmark-v1.jsonl：当前主集合588条，中文500＋英文88。
- curated/zh-v1.jsonl：中文500；development.jsonl为300，holdout.jsonl为200。
- curated/audit.json：实际覆盖、审核计数和来源/重复核验。
- curated/manifest.json：版本、配额、文件SHA256与分区冻结信息。
- cases.jsonl：初版94条，作为历史回归档案保留；不与新版重复计数。
- reference/：原始公开资料；C-ReD和Fast-DetectGPT最初为私有归档，现随仓库公开保留；第三方语料许可未明确或未逐项核实，不纳入本仓库MIT授权。
- sources.json、raw-inventory.json：来源版本、许可状态、实际解析条数和逐文件摘要。
- curation/：候选、淘汰、初标与独立上下文模型复核；不是参赛生成结果。

初版6条合成中文仅在历史集合中保留；新版500条全部选自C-ReD原文。原始检测标签不当作质量标签，教学示例不能充当未见测试。模型辅助审核不等同于人工金标准，详见../docs/DATA_BUILD.md。
