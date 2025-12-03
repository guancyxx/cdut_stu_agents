# QDUOJ 部署完成

## ✅ 部署状态

所有服务已成功启动并运行：

- ✅ **Redis 缓存**: 运行中
- ✅ **PostgreSQL 数据库**: 运行中  
- ✅ **判题服务器**: 运行中 (healthy)
- ✅ **后端 API**: 运行中 (healthy)
- ✅ **前端界面**: 可访问

## 🌐 访问信息

### Web 界面
- **主页**: http://localhost
- **管理后台**: http://localhost/admin
- **API 文档**: http://localhost/api/docs (如果可用)

### 默认管理员账号
- **用户名**: `root`
- **密码**: `rootroot`
- ⚠️ **请务必立即修改密码！**

## 📂 数据存储

所有数据存储在 `qduoj/data/` 目录：

```
qduoj/data/
├── backend/         # 后端数据（题目、用户等）
│   └── test_case/   # 测试用例
├── postgres/        # PostgreSQL 数据库文件
├── redis/           # Redis 数据文件
└── judge_server/    # 判题服务器数据
    ├── log/         # 判题日志
    └── run/         # 运行环境
```

## 🚀 常用命令

### 服务管理

```powershell
# 查看服务状态
cd qduoj
docker-compose ps

# 查看日志
docker-compose logs -f oj-backend
docker-compose logs -f oj-judge

# 停止服务
docker-compose stop

# 启动服务
docker-compose start

# 重启服务
docker-compose restart

# 完全停止并删除容器（数据保留）
docker-compose down

# 完全删除（包括数据）
docker-compose down -v
```

### 备份数据

```powershell
# 备份整个 data 目录
Compress-Archive -Path .\qduoj\data\ -DestinationPath oj_backup_$(Get-Date -Format 'yyyyMMdd').zip

# 备份数据库
docker exec qduoj-oj-postgres-1 pg_dump -U onlinejudge onlinejudge > oj_db_backup.sql
```

## 🔧 初始配置步骤

### 1. 首次登录

1. 访问 http://localhost
2. 点击右上角"登录"
3. 使用管理员账号登录：
   - 用户名: `root`
   - 密码: `rootroot`

### 2. 修改管理员密码

1. 登录后访问 http://localhost/admin
2. 进入"用户管理"
3. 找到 `root` 用户并修改密码

### 3. 系统配置

访问管理后台进行基本配置：

1. **网站配置**
   - 网站名称：CDUT 编程竞赛训练系统
   - 网站简介
   - 网站关键词

2. **SMTP 配置**（可选，用于邮件通知）
   - SMTP 服务器
   - 发件人邮箱

3. **判题配置**
   - 确认判题服务器已连接
   - 配置语言支持

### 4. 创建测试题目

1. 访问管理后台 → 题目管理
2. 点击"创建题目"
3. 填写题目信息：
   - 标题
   - 描述
   - 输入输出格式
   - 样例
   - 时间限制
   - 内存限制
4. 上传测试用例（.in 和 .out 文件）

## 🧪 测试 API

### 获取题目列表

```powershell
# 获取公开题目列表
curl http://localhost/api/problem/?limit=10 -UseBasicParsing | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### 提交代码测试

```powershell
# 首先需要登录获取 token，然后才能提交
# 使用 Python 脚本更方便（见下方 Python API 测试）
```

## 🐍 Python API 测试

创建测试脚本：

```python
# test_qduoj_api.py
import requests
import json

base_url = "http://localhost"

# 1. 登录
login_data = {
    "username": "root",
    "password": "rootroot"
}
response = requests.post(f"{base_url}/api/login", json=login_data)
print("登录结果:", response.json())

# 保存 session
session = requests.Session()
session.cookies.update(response.cookies)

# 2. 获取题目列表
response = session.get(f"{base_url}/api/problem/")
problems = response.json()
print(f"\n题目数量: {problems['data']['total']}")
if problems['data']['results']:
    print(f"第一题: {problems['data']['results'][0]['title']}")

# 3. 提交代码（如果有题目）
if problems['data']['results']:
    problem_id = problems['data']['results'][0]['_id']
    code = """
#include <iostream>
using namespace std;

int main() {
    int a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
    """
    
    submit_data = {
        "problem_id": problem_id,
        "language": "C++",
        "code": code
    }
    
    response = session.post(f"{base_url}/api/submission", json=submit_data)
    print("\n提交结果:", response.json())
```

运行测试：

```powershell
python test_qduoj_api.py
```

## 🔗 与 AI Agent 集成

### 更新主 docker-compose.yml

回到项目根目录，更新 `docker-compose.yml` 以连接到 QDUOJ：

```yaml
services:
  youtu-agent:
    # ... 现有配置 ...
    environment:
      - OJ_API_URL=http://host.docker.internal
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - cdut-network
      - qduoj_default

networks:
  cdut-network:
    driver: bridge
  qduoj_default:
    external: true
```

### 测试集成

使用已创建的 `custom_agents/tools/qduoj_client.py`：

```python
from custom_agents.tools.qduoj_client import QDUOJClient

# 初始化客户端
client = QDUOJClient(base_url="http://localhost")

# 登录
client.login("root", "rootroot")

# 获取题目
problems = client.get_problem_list(limit=5)
print(f"题目数量: {problems['data']['total']}")
```

## 📊 监控和维护

### 查看系统资源使用

```powershell
# 查看容器资源使用
docker stats qduoj-oj-backend-1 qduoj-oj-judge-1 qduoj-oj-postgres-1 qduoj-oj-redis-1
```

### 查看判题日志

```powershell
# 实时查看判题日志
docker logs -f qduoj-oj-judge-1

# 查看后端日志
docker logs -f qduoj-oj-backend-1
```

### 清理旧数据

```powershell
# 清理 Docker 未使用的镜像和容器
docker system prune -a

# 清理旧的判题日志（如果日志过大）
# 进入容器清理
docker exec -it qduoj-oj-judge-1 sh
cd /log
ls -lh
# 删除旧日志文件
```

## 🎓 导入示例题目

QDUOJ 支持 FPS (Free Problem Set) 格式导入题目：

1. 下载题目包（.zip 格式）
2. 访问管理后台 → 题目管理 → 导入题目
3. 选择 FPS 格式，上传 zip 文件
4. 点击导入

推荐题目来源：
- CSES Problem Set
- 洛谷题库
- HDU Online Judge

## ⚠️ 常见问题

### 端口被占用

如果 80 端口被占用，修改 `qduoj/docker-compose.yml`：

```yaml
ports:
  - "0.0.0.0:8080:8000"  # 改为 8080 端口
```

然后重启服务。

### 判题服务器无法连接

检查 TOKEN 是否一致：
- `oj-backend` 的 `JUDGE_SERVER_TOKEN`
- `oj-judge` 的 `TOKEN`

### 数据库连接失败

等待 PostgreSQL 完全启动（约 30 秒）后再访问系统。

## 🎉 下一步

1. ✅ **OJ 系统已部署**
2. 🔄 **配置管理员账号和基本设置**
3. 📝 **创建/导入测试题目**
4. 🤖 **开发 AI Agent 集成功能**
5. 🔗 **实现 AI + OJ 联动**

## 📚 相关资源

- [QDUOJ 官方文档](http://opensource.qduoj.com/)
- [GitHub 仓库](https://github.com/QingdaoU/OnlineJudge)
- [API 客户端](../custom_agents/tools/qduoj_client.py)
- [集成说明](./QDUOJ_INTEGRATION.md)
