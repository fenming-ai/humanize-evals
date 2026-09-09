---
date: 2026-09-09
updated: 2026-09-09
tags: [domain/data, lang/python]
severity: minor
status: fixed
related: []
---

# 上游原始数据不应直接输出完整diff检查

## 现象
CSV使用CRLF，git diff --check产生大量上游换行告警和原文输出。

## 复现
对新导入CSV直接执行未限制输出的diff检查。

## 根因
把来源原始字节当作自有代码进行空白规范检查。

## 影响
日志膨胀，难以审阅实际改动。

## 缓解
用.gitattributes关闭原始归档的文本转换、diff和空白检查；用SHA256及CSV解析验证。

## 修复方向
代码与原始资料分开验证，诊断输出只保留计数和文件名。
