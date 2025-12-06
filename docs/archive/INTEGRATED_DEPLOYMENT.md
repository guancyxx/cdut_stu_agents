# 🚀 CDUT 竞赛训练系统 - 整合部署指南

## 📋 系统架构

本系统整合了 **AI 辅导系统** 和 **OJ 评测系统** 到一个统一的 Docker Compose 环境中。

```
┌─────────────────────────────────────────────────────────┐
│                   CDUT 竞赛训练系统                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐         ┌──────────────────┐     │
│  │  AI 辅导系统      │◄───────►│  OJ 评测系统      │     │
│  │  (youtu-agent)   │         │  (QDUOJ)         │     │
│  │  Port: 8848      │         │  Port: 8000      │     │
│  └──────────────────┘         └──────────────────┘     │
│         │                              │                │
│         │                              ▼                │
│         │                     ┌──────────────────┐     │
│         │                     │  判题服务器       │     │
│         │                     │  (Judge Server)  │     │
│         │                     └──────────────────┘     │
│         │                              │                │
│         └──────────────┬───────────────┘                │
│                        ▼                                │
│              ┌──────────────────┐                       │
│              │  PostgreSQL      │                       │
│              │  + Redis         │                       │
│              └──────────────────┘                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 🎯 服务列表

| 服务名称 | 容器名称 | 端口 | 描述 |
|---------|---------|------|------|
| youtu-agent | cdut-youtu-agent | 8848 | AI 辅导对话系统 |
| oj-backend | cdut-oj-backend | 8000 | OJ 后端 API + Web 界面 |
| oj-judge | cdut-oj-judge | - | 判题服务器（内部） |
| oj-postgres | cdut-oj-postgres | - | PostgreSQL 数据库 |
| oj-redis | cdut-oj-redis | - | Redis 缓存 |

## 📦 快速开始

### 1. 迁移到整合环境

如果你之前已经部署过独立的服务，运行迁移脚本：

```powershell
.\migrate-to-integrated.ps1
```

迁移脚本会：
- ✅ 停止旧的 QDUOJ 服务
- ✅ 停止旧的 AI Agent 服务
- ✅ 检查并创建必要的数据目录
- ✅ 拉取最新的 Docker 镜像
- ✅ 启动整合后的服务

### 2. 全新部署

如果是首次部署：

```powershell
# 1. 拉取镜像
docker-compose pull

# 2. 启动服务
docker-compose up -d

# 3. 等待服务启动（约 30 秒）
Start-Sleep -Seconds 30

# 4. 检查服务状态
docker-compose ps
```

## 🌐 访问地址

### AI 辅导系统
- **访问地址**: http://localhost:8848
- **功能**: 
  - 算法问题解答
  - 代码审查
  - 学习路径推荐
  - 对话式辅导

### OJ 评测系统
- **主页**: http://localhost:8000
- **管理后台**: http://localhost:8000/admin
- **API 文档**: http://localhost:8000/api/
- **默认账号**: 
  - 用户名: `root`
  - 密码: `rootroot`
  - ⚠️ **首次登录后请立即修改密码！**

## 🔧 常用操作

### 服务管理

```powershell
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart

# 重启单个服务
docker-compose restart youtu-agent
docker-compose restart oj-backend

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f youtu-agent
docker-compose logs -f oj-backend
docker-compose logs -f oj-judge
```

### 数据管理

```powershell
# 备份所有数据
Compress-Archive -Path .\data\,.\qduoj\data\ -DestinationPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"

# 备份数据库
docker exec cdut-oj-postgres pg_dump -U onlinejudge onlinejudge > "db_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"

# 恢复数据库
Get-Content backup.sql | docker exec -i cdut-oj-postgres psql -U onlinejudge onlinejudge
```

### 清理和维护

```powershell
# 查看磁盘使用
docker system df

# 清理未使用的镜像、容器和卷
docker system prune -a --volumes

# 查看日志大小
docker exec cdut-oj-judge du -sh /log
docker logs cdut-oj-backend 2>&1 | Measure-Object -Line

# 清理日志（需要重启容器）
docker-compose restart oj-judge
```

## 📊 监控和调试

### 实时监控服务资源

```powershell
# 查看所有容器的资源使用
docker stats

# 查看特定服务的资源使用
docker stats cdut-youtu-agent cdut-oj-backend cdut-oj-judge
```

### 查看详细日志

```powershell
# AI Agent 日志
docker-compose logs -f --tail=100 youtu-agent

# OJ 后端日志
docker-compose logs -f --tail=100 oj-backend

# 判题服务器日志
docker-compose logs -f --tail=100 oj-judge

# 数据库日志
docker-compose logs -f --tail=100 oj-postgres

# 所有服务日志
docker-compose logs -f
```

### 进入容器调试

```powershell
# 进入 AI Agent 容器
docker exec -it cdut-youtu-agent /bin/bash

# 进入 OJ 后端容器
docker exec -it cdut-oj-backend /bin/sh

# 进入数据库容器
docker exec -it cdut-oj-postgres psql -U onlinejudge onlinejudge

# 查看 Redis 数据
docker exec -it cdut-oj-redis redis-cli
```

## 🔌 AI 与 OJ 集成

### API 访问配置

在 AI Agent 中访问 OJ API：

```python
# custom_agents/tools/qduoj_integration.py
from custom_agents.tools.qduoj_client import QDUOJClient

# 使用内部网络地址
client = QDUOJClient(base_url="http://oj-backend:8000")

# 登录
client.login("username", "password")

# 获取题目
problems = client.get_problem_list(limit=10)

# 提交代码
result = client.submit_code(
    problem_id=1,
    language="C++",
    code="your code here"
)
```

### 环境变量说明

`.env` 文件中的关键配置：

```bash
# AI Agent 访问 OJ（容器内部）
OJ_API_URL=http://oj-backend:8000

# 外部访问 OJ（浏览器）
OJ_EXTERNAL_URL=http://localhost:8000

# 判题服务器令牌（必须一致）
JUDGE_SERVER_TOKEN=cdut-secure-token-2024
```

## 🐛 常见问题

### Q1: 端口冲突

**问题**: 启动时提示 8000 或 8848 端口被占用

**解决**:
```powershell
# 查看端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :8848

# 修改 docker-compose.yml 中的端口映射
# 例如将 8000 改为 8001
ports:
  - "8001:8000"  # 宿主机:容器
```

### Q2: 服务无法启动

**问题**: 容器状态显示 Exit 或 Restarting

**排查步骤**:
```powershell
# 1. 查看容器日志
docker-compose logs [服务名]

# 2. 检查数据目录权限
ls -la .\qduoj\data\

# 3. 检查配置文件
cat docker-compose.yml
cat .env

# 4. 重新构建并启动
docker-compose down -v
docker-compose up -d --build
```

### Q3: OJ 无法访问

**问题**: 访问 http://localhost:8000 超时或无响应

**解决**:
```powershell
# 1. 检查后端服务状态
docker-compose ps oj-backend

# 2. 检查后端日志
docker-compose logs oj-backend

# 3. 等待服务完全启动（首次启动需要数据库迁移）
Start-Sleep -Seconds 60
docker-compose logs oj-backend | Select-String "Booting worker"

# 4. 测试 API 连接
curl http://localhost:8000/api/website
```

### Q4: 判题服务器连接失败

**问题**: 提交代码后一直显示 "Pending"

**排查**:
```powershell
# 1. 检查判题服务器日志
docker-compose logs oj-judge

# 2. 验证 TOKEN 一致性
# 检查 docker-compose.yml 中两处 TOKEN 是否相同：
# - oj-judge 的 TOKEN
# - oj-backend 的 JUDGE_SERVER_TOKEN

# 3. 重启判题服务器
docker-compose restart oj-judge

# 4. 在 OJ 管理后台查看判题服务器状态
# 访问: http://localhost:8000/admin/judge_server/
```

### Q5: AI Agent 无法连接 OJ

**问题**: AI Agent 调用 OJ API 失败

**检查**:
```powershell
# 1. 检查网络连通性
docker exec cdut-youtu-agent ping -c 3 oj-backend

# 2. 测试 API 访问
docker exec cdut-youtu-agent curl http://oj-backend:8000/api/website

# 3. 检查 .env 配置
cat .env | Select-String "OJ_API_URL"

# 4. 查看 AI Agent 日志
docker-compose logs youtu-agent | Select-String "OJ"
```

## 🔐 安全建议

1. **修改默认密码**
   - OJ 管理员密码（root/rootroot）
   - 数据库密码（onlinejudge/onlinejudge）

2. **更换判题令牌**
   ```bash
   # 在 .env 和 docker-compose.yml 中更新
   JUDGE_SERVER_TOKEN=your-secure-random-token-here
   ```

3. **配置 HTTPS**（生产环境）
   - 使用 Nginx 反向代理
   - 申请 SSL 证书
   - 修改端口映射

4. **限制对外访问**
   ```yaml
   ports:
     - "127.0.0.1:8000:8000"  # 仅本地访问
     - "127.0.0.1:8848:8848"
   ```

## 📁 目录结构

```
cdut_stu_agents/
├── docker-compose.yml          # 整合的 Docker Compose 配置
├── .env                        # 环境变量配置
├── migrate-to-integrated.ps1   # 迁移脚本
├── data/                       # AI Agent 数据
│   ├── submissions/            # 学生提交的代码
│   ├── training/               # 训练数据
│   ├── chat_history/           # 对话历史
│   └── problems/               # 题目数据
├── qduoj/                      # QDUOJ 数据和配置
│   └── data/
│       ├── backend/            # 后端数据（包括题目、测试用例）
│       ├── postgres/           # PostgreSQL 数据
│       ├── redis/              # Redis 数据
│       └── judge_server/       # 判题服务器日志
├── custom_agents/              # 自定义 AI Agent
│   └── tools/
│       └── qduoj_client.py     # OJ API 客户端
└── youtu-agent/                # Youtu-agent 源码
```

## 🎓 后续开发

### 下一步任务

1. **配置 OJ 系统**
   - [ ] 登录管理后台修改密码
   - [ ] 导入题目或创建测试题目
   - [ ] 创建测试用户账号
   - [ ] 验证判题功能

2. **开发 AI 集成功能**
   - [ ] 实现题目推荐算法
   - [ ] 开发代码分析功能
   - [ ] 创建学习路径规划
   - [ ] 实现提交结果反馈

3. **创建功能规格**
   ```bash
   # 使用 speckit 创建新功能规格
   /speckit.specify 集成 QDUOJ 评测系统，实现 AI 智能题目推荐和代码分析反馈功能
   ```

### 开发资源

- **AI Agent 配置**: `./custom_agents/configs/`
- **工具开发**: `./custom_agents/tools/`
- **API 文档**: `./docs/QDUOJ_INTEGRATION.md`
- **测试脚本**: `./test_qduoj.py`

## 📞 技术支持

如遇到问题：

1. 查看服务日志定位问题
2. 参考本文档的常见问题部分
3. 检查 GitHub Issues
4. 查阅官方文档：
   - [QDUOJ 文档](http://opensource.qduoj.com/)
   - [Youtu-agent 文档](https://github.com/tencent/youtu-agent)

---

**最后更新**: 2025-12-02  
**版本**: v1.0.0
