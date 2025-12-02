# CDUT 学生竞赛培训系统

基于腾讯开源的 youtu-agent 框架构建的 AI 化学生竞赛培训系统。

## 项目结构

```
cdut_stu_agents/
├── youtu-agent/           # youtu-agent 框架（子模块）
├── custom_agents/         # 自定义 AI Agent 配置
├── data/                  # 数据持久化目录
│   ├── submissions/       # 学生代码提交
│   ├── training/          # 训练数据
│   ├── chat_history/      # 对话历史记录
│   └── problems/          # 题库数据
├── specs/                 # 功能规格说明（由 speckit 管理）
├── docker-compose.yml     # Docker 编排配置
├── .env                   # 环境变量配置
└── .env.example          # 环境变量配置模板
```

## 快速启动

### 前置要求

- Docker 和 Docker Compose 已安装
- DeepSeek API Key（已配置在 .env 文件中）

### 启动服务

1. **构建并启动容器**：

```powershell
docker-compose up -d --build
```

2. **查看日志**：

```powershell
docker-compose logs -f youtu-agent
```

3. **访问 Web UI**：

打开浏览器访问：http://localhost:8848

### 常用命令

```powershell
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 进入容器 Shell
docker-compose exec youtu-agent bash

# 查看容器状态
docker-compose ps
```

## 配置说明

### 环境变量

主要配置在 `.env` 文件中：

- **LLM 配置**：DeepSeek API 配置（已设置）
- **Web UI**：端口 8848
- **数据目录**：所有数据持久化在 `./data/` 目录

### 自定义 Agent

在 `custom_agents/` 目录下创建自定义 Agent 配置文件。参考 `youtu-agent/configs/agents/` 中的示例。

## 功能规划

使用 speckit 工具进行功能规划和开发：

### 创建功能规格

```bash
# 示例：创建 AI 辅导对话系统规格
/speckit.specify 开发AI辅导对话系统，支持学生提问、代码审查、算法讲解
```

### 功能规划

```bash
# 基于规格创建实施计划
/speckit.plan
```

### 需求澄清

```bash
# 对不明确的需求进行讨论
/speckit.clarify
```

## 开发路线图

### 第一阶段：AI Agent 基础功能
- [ ] AI 辅导对话系统
- [ ] 代码审查与建议
- [ ] 算法概念讲解

### 第二阶段：Online Judge 集成
- [ ] 题目管理系统
- [ ] 代码提交与评测
- [ ] 评测结果反馈

### 第三阶段：智能训练系统
- [ ] 个性化学习路径
- [ ] 难度自适应推荐
- [ ] 学习进度追踪

## 技术栈

- **AI Framework**: youtu-agent (基于 openai-agents)
- **LLM**: DeepSeek-V3
- **Backend**: Python 3.12
- **Frontend**: youtu-agent WebUI
- **Containerization**: Docker & Docker Compose

## 相关资源

- [youtu-agent 文档](https://tencentcloudadp.github.io/youtu-agent/)
- [youtu-agent GitHub](https://github.com/TencentCloudADP/youtu-agent)
- [DeepSeek API 文档](https://platform.deepseek.com/docs)

## 许可证

MIT License
