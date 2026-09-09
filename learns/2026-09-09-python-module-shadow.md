---
date: 2026-09-09
updated: 2026-09-09
tags: [domain/data, lang/python]
severity: minor
status: fixed
related: []
---

# 辅助脚本不能使用标准库模块名

## 现象
临时案例选择脚本命名为select.py，导致subprocess导入selectors时报错。

## 复现
运行同目录下的标注脚本。

## 根因
Python优先加载本地select.py，遮蔽标准库select。

## 影响
标注批次未实际启动；不能把排队当作已运行。

## 缓解
将文件改名select_cases.py后重新启动，保留未运行状态。

## 修复方向
新脚本命名避开select、json、csv、subprocess等标准库名。
