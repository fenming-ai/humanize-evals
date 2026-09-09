---
date: 2026-09-09
updated: 2026-09-09
tags: [domain/git, tool/git]
severity: major
status: mitigated
related: []
---

# 全局URL重写可能覆盖正确的仓库凭证

## 现象
GitHub API确认私有仓库存在且有推送权限，但Git返回Repository not found。

## 复现
在存在其他账号URL重写的环境，用当前账号凭证执行git ls-remote。诊断时只输出配置项类别和布尔判断，不打印原始URL或完整配置键。

## 根因
全局insteadOf将目标URL替换为含旧凭证的地址，绕过预期账号选择。即使只输出配置键名，凭证也可能嵌在键名里。

## 影响
首次推送失败；原始配置键输出存在凭证泄露风险。

## 缓解
本次Git命令设置GIT_CONFIG_GLOBAL=/dev/null，保留仓库级gh凭证助手，并显式传入目标账号凭证环境。未修改全局配置。已验证私有可见性与远端HEAD。排查输出意外包含旧凭证，已提示用户撤销轮换；凭证未写入仓库。

## 修复方向
多账号操作优先使用隔离配置；诊断先在进程内脱敏再输出。不要假设--name-only不含秘密。新空仓库确认无远端分支后首次push，随后正常pull --rebase和HEAD核验。
