# Git Submodule Usage Guide

当前仓库不再使用任何 Git Submodule。

## 当前状态

- `.gitmodules` 已清空
- 运行时不再依赖 `qduoj` 子模块
- 判题链路已迁移到：`ai-agent-lite + cdut-sandbox + cdut-postgres`

## 克隆方式

```bash
git clone git@github.com:guancyxx/cdut_stu_agents.git
```

无需执行 `git submodule update --init --recursive`。

## 说明

若后续引入新的 submodule，请同步更新本文件和 `.gitmodules`。
