# QDUOJ 快速部署指南

## ⚠️ 重要说明

QDUOJ 的官方 Docker 镜像可能需要从源码构建。以下是两种部署方案：

## 方案一：使用官方预构建脚本（推荐）

1. **克隆 QDUOJ 仓库**：

```powershell
# 在项目根目录下克隆
git clone https://github.com/QingdaoU/OnlineJudgeDeploy.git qduoj-deploy
cd qduoj-deploy
```

2. **运行部署脚本**：

```powershell
# Windows 使用 PowerShell
.\install.ps1
```

3. **配置环境**：

编辑 `.env` 文件：
```bash
JUDGE_SERVER_TOKEN=your-secure-token
POSTGRES_PASSWORD=onlinejudge
```

4. **启动服务**：

```powershell
docker-compose up -d
```

## 方案二：从源码构建（开发环境）

1. **克隆后端仓库**：

```powershell
git clone https://github.com/QingdaoU/OnlineJudge.git oj-backend-src
cd oj-backend-src
```

2. **构建后端镜像**：

```powershell
docker build -t qduoj-backend:local .
```

3. **克隆判题服务器**：

```powershell
git clone https://github.com/QingdaoU/JudgeServer.git judge-server-src
cd judge-server-src
docker build -t qduoj-judge:local .
```

4. **克隆前端**：

```powershell
git clone https://github.com/QingdaoU/OnlineJudgeFE.git oj-frontend-src
cd oj-frontend-src
docker build -t qduoj-frontend:local .
```

5. **修改 docker-compose.yml 使用本地镜像**。

## 方案三：简化集成（暂时跳过 OJ）

先专注于 AI Agent 开发，OJ 集成后续添加：

```powershell
# 只启动 AI Agent
docker-compose up -d youtu-agent

# 访问 AI 辅导系统
# http://localhost:8848
```

## 推荐方案

### 现阶段（开发 AI 功能）

1. **先启动 AI Agent**：
   ```powershell
   # 修改 docker-compose.yml，注释掉 OJ 相关服务
   docker-compose up -d youtu-agent
   ```

2. **完成 AI 辅导系统的核心功能**：
   - 基础问答对话 ✅ (规格已完成)
   - 代码审查
   - 算法讲解

3. **并行准备 OJ 环境**：
   ```powershell
   # 在另一个目录部署完整的 QDUOJ
   cd ..
   git clone https://github.com/QingdaoU/OnlineJudgeDeploy.git
   cd OnlineJudgeDeploy
   docker-compose up -d
   ```

### 下一阶段（集成 OJ）

当 AI Agent 基础功能完成后：
1. 确保 QDUOJ 正常运行
2. 开发 API 集成层（已提供 qduoj_client.py）
3. 实现 AI + OJ 联动功能

## 临时方案：本地开发环境

如果 Docker 部署遇到问题，可以使用本地开发环境：

```powershell
# 安装 PostgreSQL 和 Redis
# 使用 Python 虚拟环境运行后端
# 使用 Node.js 运行前端
```

具体步骤见 [QDUOJ 官方文档](https://opensource.qduoj.com/#/onlinejudge/guide/deploy)

## 下一步建议

1. **立即可做**：
   - 启动 AI Agent 服务
   - 测试 AI 辅导对话功能
   - 完善功能规格说明

2. **准备工作**：
   - 在独立环境部署完整 QDUOJ
   - 熟悉 QDUOJ API
   - 准备测试题目

3. **集成开发**：
   - 开发 API 调用层
   - 实现 AI 分析判题结果
   - 建立学习反馈循环
