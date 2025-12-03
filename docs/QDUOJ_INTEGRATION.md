# QDUOJ 集成文档

## 系统架构

```
学生
  ↓
AI 辅导对话系统 (youtu-agent)
  ↓
QDUOJ API (qduoj_client.py)
  ↓
QDUOJ 后端 (oj-backend)
  ↓
判题服务器 (oj-judge-server)
```

## 服务说明

### 1. youtu-agent (AI 辅导系统)
- **端口**: 8848
- **功能**: AI 对话、代码审查、学习指导
- **访问**: http://localhost:8848

### 2. QDUOJ 前端
- **端口**: 8080
- **功能**: 用户界面、题目浏览、代码提交
- **访问**: http://localhost:8080

### 3. QDUOJ 后端 API
- **端口**: 8000
- **功能**: RESTful API、用户管理、题目管理
- **API 文档**: http://localhost:8000/api/docs

### 4. 判题服务器
- **功能**: 代码编译和运行、结果判定
- **支持语言**: C, C++, Java, Python2, Python3, Go, JavaScript, Rust

## 快速启动

### 1. 启动所有服务

```powershell
# 构建并启动
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2. 初始化 QDUOJ

首次启动后，访问 http://localhost:8080 进行初始化：

1. 创建超级管理员账号
2. 配置系统基本信息
3. 导入题目（可选）

### 3. 配置 AI Agent 集成

在 `custom_agents/` 下创建集成配置：

```yaml
# custom_agents/configs/oj_agent.yaml
agent:
  name: "OJ Training Assistant"
  description: "AI 辅导与 OJ 练习集成助手"
  
tools:
  - name: qduoj_client
    enabled: true
    config:
      base_url: ${OJ_API_URL}
      
features:
  - code_review
  - problem_recommendation
  - submission_analysis
  - learning_path
```

## API 使用示例

### Python 客户端

```python
from custom_agents.tools.qduoj_client import QDUOJClient

# 初始化客户端
client = QDUOJClient(base_url="http://localhost:8000")

# 登录
client.login("student_001", "password123")

# 获取推荐题目
problems = client.get_problem_list(difficulty="Low", limit=5)

# 提交代码
result = client.submit_code(
    problem_id=1001,
    language="Python3",
    code=student_code
)

# 查看判题结果
submission = client.get_submission_detail(result['data']['submission_id'])
print(f"判题结果: {submission['data']['result']}")
```

### curl 命令示例

```bash
# 获取题目列表
curl http://localhost:8000/api/problem?limit=10

# 获取题目详情
curl http://localhost:8000/api/problem/1001

# 提交代码 (需要登录 token)
curl -X POST http://localhost:8000/api/submission \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "problem_id": 1001,
    "language": "Python3",
    "code": "print(\"Hello World\")"
  }'
```

## 判题结果说明

| 代码 | 结果 | 说明 |
|------|------|------|
| -2 | 编译中 | 正在编译代码 |
| -1 | 判题失败 | 系统错误 |
| 0 | 待判题 | 等待判题 |
| 1 | 判题中 | 正在运行测试 |
| 2 | 正在编译 | 编译阶段 |
| 3 | 编译错误 (CE) | Compile Error |
| 4 | 答案正确 (AC) | Accepted |
| 5 | 格式错误 (PE) | Presentation Error |
| 6 | 答案错误 (WA) | Wrong Answer |
| 7 | 超时 (TLE) | Time Limit Exceeded |
| 8 | 内存超限 (MLE) | Memory Limit Exceeded |
| 9 | 运行错误 (RE) | Runtime Error |
| 10 | 系统错误 (SE) | System Error |

## 支持的编程语言

```python
LANGUAGES = {
    'C': {'extension': '.c'},
    'C++': {'extension': '.cpp'},
    'Java': {'extension': '.java'},
    'Python2': {'extension': '.py'},
    'Python3': {'extension': '.py'},
    'Go': {'extension': '.go'},
    'JavaScript': {'extension': '.js'},
    'Rust': {'extension': '.rs'}
}
```

## 数据持久化

所有数据存储在 `data/oj/` 目录：

```
data/oj/
├── backend/        # 后端数据（用户、题目等）
├── judge/          # 测试用例数据
├── log/           # 判题日志
└── frontend/      # 前端配置
```

## 常用操作

### 导入题目

使用 FPS (Free Problem Set) 格式导入：

```bash
# 进入后端容器
docker exec -it cdut-oj-backend bash

# 使用管理命令导入
python manage.py import_problem /data/problems/problem.zip
```

### 备份数据

```powershell
# 备份数据库
docker exec cdut-oj-postgres pg_dump -U onlinejudge onlinejudge > backup.sql

# 备份文件数据
Compress-Archive -Path .\data\oj\ -DestinationPath oj_backup.zip
```

### 查看判题日志

```powershell
# 实时查看判题服务器日志
docker-compose logs -f oj-judge-server

# 查看后端日志
docker-compose logs -f oj-backend
```

## 故障排查

### 判题服务器连接失败

检查 `JUDGE_SERVER_TOKEN` 是否一致：
- `.env` 文件中的 `JUDGE_SERVER_TOKEN`
- 判题服务器的 `TOKEN` 环境变量

### 数据库连接问题

```powershell
# 检查数据库服务
docker-compose ps oj-postgres

# 查看数据库日志
docker-compose logs oj-postgres
```

### 重置系统

```powershell
# 停止并删除所有容器和数据
docker-compose down -v

# 删除数据目录
Remove-Item -Recurse -Force .\data\oj\

# 重新启动
docker-compose up -d
```

## API 认证

QDUOJ 使用基于 Session 的认证：

1. 调用 `/api/login` 获取 session cookie
2. 后续请求携带 cookie 或 token
3. Token 存储在响应的 `data.token` 字段

```python
# 登录获取 token
response = client.login("username", "password")
token = response['data']['token']

# 使用 token 访问受保护的 API
headers = {'Authorization': f'Bearer {token}'}
```

## 与 AI Agent 的集成点

### 1. 智能题目推荐
- AI 分析学生水平
- 调用 `get_problem_list()` 获取合适难度题目
- 推荐给学生

### 2. 代码提交与反馈
- 学生提交代码
- AI 预先审查代码
- 提交到 OJ 判题
- AI 分析判题结果并提供改进建议

### 3. 学习路径规划
- 追踪学生提交历史
- 分析薄弱知识点
- 生成个性化训练计划

### 4. 错误分析
- 捕获 CE/WA/TLE 等错误
- AI 分析错误原因
- 提供针对性指导

## 下一步

1. 启动所有服务
2. 创建测试账号
3. 导入示例题目
4. 测试 API 集成
5. 开发 AI Agent 与 OJ 的联动功能
