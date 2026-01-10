# Git 子模块使用指南

本项目使用Git子模块管理三个主要组件。

## 📦 子模块列表

| 子模块 | 仓库地址 | 用途 |
|--------|---------|------|
| youtu-agent | https://github.com/TencentCloudADP/youtu-agent.git | AI Agent框架 |
| qduoj | https://github.com/QingdaoU/OnlineJudgeDeploy.git | OJ系统部署配置 |
| fps-problems | https://github.com/zhblue/freeproblemset.git | FPS题库（609题） |

## 🚀 首次克隆项目

```bash
# 克隆主仓库及所有子模块
git clone --recursive git@github.com:guancyxx/cdut_stu_agents.git

# 或者，如果已经克隆了主仓库
git clone git@github.com:guancyxx/cdut_stu_agents.git
cd cdut_stu_agents
git submodule update --init --recursive
```

## 🔄 更新子模块

### 更新所有子模块到最新版本

```bash
git submodule update --remote --merge
```

### 更新特定子模块

```bash
# 更新youtu-agent到最新
git submodule update --remote youtu-agent

# 更新qduoj到最新
git submodule update --remote qduoj

# 更新fps-problems到最新
git submodule update --remote fps-problems
```

### 拉取主仓库和子模块的更新

```bash
# 拉取主仓库更新
git pull

# 同步子模块到主仓库指定的提交
git submodule update --init --recursive
```

## 📝 查看子模块状态

```bash
# 查看所有子模块状态
git submodule status

# 查看子模块的具体提交信息
git submodule foreach git log --oneline -1
```

## ⚠️ 注意事项

### 1. 子模块工作目录是独立的
- 进入子模块目录后，它是一个独立的git仓库
- 在子模块内的修改不会自动影响主仓库

### 2. 修改子模块内容

```bash
# 进入子模块
cd youtu-agent

# 查看当前分支（通常处于detached HEAD状态）
git branch

# 切换到主分支进行开发
git checkout main

# 进行修改、提交
git add .
git commit -m "修改说明"

# 回到主仓库
cd ..

# 更新主仓库的子模块引用
git add youtu-agent
git commit -m "更新youtu-agent子模块引用"
```

### 3. 切换分支时同步子模块

```bash
# 切换分支
git checkout <branch-name>

# 同步子模块（重要！）
git submodule update --init --recursive
```

## 🔧 常见问题

### 问题1：子模块目录为空

```bash
# 初始化并更新所有子模块
git submodule update --init --recursive
```

### 问题2：子模块处于detached HEAD状态

这是正常的。子模块默认指向特定的提交，而不是分支。如需修改：

```bash
cd <submodule-directory>
git checkout main  # 或其他分支
```

### 问题3：删除子模块

```bash
# 1. 从.gitmodules删除配置
git config -f .gitmodules --remove-section submodule.<submodule-name>

# 2. 从.git/config删除配置
git config -f .git/config --remove-section submodule.<submodule-name>

# 3. 从暂存区删除
git rm --cached <submodule-path>

# 4. 删除物理目录
rm -rf <submodule-path>
rm -rf .git/modules/<submodule-name>

# 5. 提交更改
git commit -m "删除子模块 <submodule-name>"
```

## 📚 更多资源

- [Git子模块官方文档](https://git-scm.com/book/zh/v2/Git-%E5%B7%A5%E5%85%B7-%E5%AD%90%E6%A8%A1%E5%9D%97)
- [youtu-agent文档](https://github.com/TencentCloudADP/youtu-agent)
- [QDUOJ文档](https://github.com/QingdaoU/OnlineJudge)
