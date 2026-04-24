# QDUOJ 题库导入指南

## 概述

本文档描述如何将标准竞赛题库导入 QDUOJ（Qingdao University Online Judge）系统，以及如何从现有系统导出和恢复题库数据。

**当前题库状态（2026-04-24）：2683 道题目，全部可见**

| 来源 | 前缀 | 数量 | 导入方式 |
|------|-------|------|----------|
| FPS XML (Codeforces) | `fps*` | 2661 | `import_fps_v15.py` Django shell 脚本 |
| 手工创建 | `custom-*` | 10 | Admin API 三阶段导入 |
| Hydro 导出 (蓝桥杯) | `LQ*` | 12 | `import_hydro_problems.py` Admin API 导入 |

---

## 1. 系统环境

- **QDUOJ 版本**: Django 3.2.25
- **Docker 容器**: `cdut-oj-backend`（Django 应用）、`cdut-oj-postgres`（PostgreSQL 数据库）
- **数据库**: PostgreSQL, user=`onlinejudge`, db=`onlinejudge`
- **测试数据目录**: 容器内 `/data/test_case/`（约 220MB，3528 个子目录）
- **Admin API**: `http://localhost:8000/api/admin/`
- **默认管理员**: `root` / `rootroot`（如已修改请用环境变量覆盖）

---

## 2. 数据备份与恢复

### 2.1 完整备份（数据库 + 测试数据）

```bash
cd /home/guancy/workspace/cdutstuagents/backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. PostgreSQL custom-format dump（推荐，用于 pg_restore）
docker exec cdut-oj-postgres pg_dump -U onlinejudge -d onlinejudge -F c \
  -f /tmp/qduoj_full_${TIMESTAMP}.dump
docker cp cdut-oj-postgres:/tmp/qduoj_full_${TIMESTAMP}.dump \
  ./qduoj_full_${TIMESTAMP}.dump

# 2. SQL plain text dump（可读，用于手动检查或跨版本迁移）
docker exec cdut-oj-postgres pg_dump -U onlinejudge -d onlinejudge \
  --no-owner --no-privileges \
  -f /tmp/qduoj_full_${TIMESTAMP}.sql
docker cp cdut-oj-postgres:/tmp/qduoj_full_${TIMESTAMP}.sql \
  ./qduoj_full_${TIMESTAMP}.sql

# 3. 测试数据目录
docker exec cdut-oj-backend tar czf /tmp/qduoj_testcase_${TIMESTAMP}.tar.gz \
  -C /data test_case
docker cp cdut-oj-backend:/tmp/qduoj_testcase_${TIMESTAMP}.tar.gz \
  ./qduoj_testcase_${TIMESTAMP}.tar.gz
```

### 2.2 恢复

```bash
# 恢复数据库（先清空再导入）
docker exec cdut-oj-postgres pg_dropdb -U onlinejudge onlinejudge
docker exec cdut-oj-postgres pg_createdb -U onlinejudge onlinejudge
docker cp qduoj_full_TIMESTAMP.dump cdut-oj-postgres:/tmp/
docker exec cdut-oj-postgres pg_restore -U onlinejudge -d onlinejudge \
  /tmp/qduoj_full_TIMESTAMP.dump

# 恢复测试数据
docker cp qduoj_testcase_TIMESTAMP.tar.gz cdut-oj-backend:/tmp/
docker exec cdut-oj-backend tar xzf /tmp/qduoj_testcase_TIMESTAMP.tar.gz -C /data
```

---

## 3. 导入方式一：FPS XML 批量导入

### 3.1 适用来源

- Free Problem Set (FPS) XML 文件（v1.1~v1.5）
- 来源：[zhblue/freeproblemset](https://github.com/zhblue/freeproblemset)、educg.net 等

### 3.2 步骤

```bash
# 1. 将 FPS XML 文件放入容器
docker cp fps-file.xml cdut-oj-backend:/app/

# 2. 将导入脚本复制到容器
docker cp scripts/import/import_fps_v15.py cdut-oj-backend:/app/

# 3. 在容器内执行导入
docker exec cdut-oj-backend python /app/import_fps_v15.py /app/fps-file.xml

# 4. 设置题目可见（默认导入的题目不可见）
docker exec cdut-oj-backend python manage.py shell -c "
from problem.models import Problem
count = Problem.objects.filter(visible=False).update(visible=True)
print(f'Updated {count} problems to visible')
"

# 5. 清理容器内的临时文件
docker exec cdut-oj-backend rm -f /app/fps-file.xml /app/import_fps_v15.py
```

### 3.3 已知问题

- FPS XML 中部分题目缺少 `description` 字段会导致 `NoneType` 错误（约 831/2833 道受影响）
- 解决方法：修改 `import_fps_v15.py` 中的 `save_image` 函数，添加 None 值检查

---

## 4. 导入方式二：Hydro 格式导入（Admin API）

### 4.1 适用来源

- Hydro（hydro.ac）导出的题目包
- 目录结构：每题一个目录，含 `problem.yaml` + `problem.md` + `testdata/`

### 4.2 Hydro 导出操作

1. 登录 Hydro 管理后台
2. 进入题目管理 → 选择要导出的题目 → 点击「导出」
3. 下载压缩包并解压到 `fps-problems/Export/` 目录

### 4.3 导入步骤

```bash
cd /home/guancy/workspace/cdutstuagents

# 环境变量（可选，默认 root/rootroot）
export OJ_USER=root
export OJ_PASS=rootroot

# 执行导入
HYDRO_DIR=./fps-problems/Export python3 scripts/import/import_hydro_problems.py
```

### 4.4 脚本功能

- **HTML 解析**: 自动从 Hydro 的 `problem.md` 中按 `<h2>` 标签拆分 description/input_description/output_description/hint
- **样例提取**: 三重回退策略
  1. 输入/输出格式中的"输入样例/输出样例"标记
  2. 说明部分中 `<b>输入/输出</b>` 标签内嵌数据
  3. 第一个测试用例（当样例为空时自动填充）
- **测试数据**: 自动打包为 ZIP 上传，支持任意数量的测试点
- **必填字段**: 自动补充 `languages`、`rule_type`、`difficulty`、`visible`、`source` 等必需字段

### 4.5 QDUOJ Admin API 创建题目必需字段

```json
{
  "_id": "唯一显示ID",
  "title": "题目名称",
  "description": "题目描述（支持HTML）",
  "input_description": "输入描述（不能为空）",
  "output_description": "输出描述（不能为空）",
  "samples": [{"input": "样例输入", "output": "样例输出"}],
  "test_case_id": "32位hex",
  "test_case_score": [{"score": 10, "input_name": "1.in", "output_name": "1.out"}],
  "languages": ["C", "C++", "Java", "Python3"],
  "rule_type": "ACM",
  "visible": true,
  "difficulty": "Low|Mid|High",
  "source": "题目来源",
  "io_mode": {"input": "input.txt", "output": "output.txt", "io_mode": "Standard IO"},
  "time_limit": 1000,
  "memory_limit": 256,
  "spj": false,
  "spj_language": null,
  "tags": ["至少一个标签"]
}
```

**注意**: API 字段名是 `samples`（带 s）、`visible`（不是 `is_public`），且 `samples` 列表不能为空。

---

## 5. 导入方式三：Admin API 手工导入

### 5.1 三阶段模式

```
Phase 1: POST /api/admin/problem     → 创建题目（test_case_id 用占位符）
Phase 2: POST /api/admin/test_case   → 上传测试数据 ZIP
Phase 3: PUT  /api/admin/problem     → 更新题目（填入真实 test_case_id）
```

### 5.2 认证流程

```python
import requests

session = requests.Session()
# 1. 获取 CSRF token
session.get("http://localhost:8000/api/profile")
csrf = session.cookies["csrftoken"]

# 2. 登录
resp = session.post("http://localhost:8000/api/login",
    json={"username": "root", "password": "rootroot"},
    headers={"X-CSRFToken": csrf})
csrf = session.cookies["csrftoken"]  # 登录后 CSRF 会轮换
```

### 5.3 上传测试数据

```python
import zipfile, tempfile

# 创建 ZIP
tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
with zipfile.ZipFile(tmp.name, "w") as zf:
    zf.writestr("1.in", "input data")
    zf.writestr("1.out", "output data")

# 上传
with open(tmp.name, "rb") as f:
    resp = session.post("http://localhost:8000/api/admin/test_case",
        files={"file": ("testdata.zip", f, "application/zip")},
        data={"problem_id": str(problem_db_id), "spj": "false"},
        headers={"X-CSRFToken": csrf})

# 返回：{"id": "真实test_case_id", "info": [...], "spj": false}
real_tc_id = resp.json()["id"]  # 注意：是 "id" 不是 "test_case_id"
```

**关键点**: `spj="false"` 必须包含在 form data 中，否则上传静默失败。

---

## 6. 更多题库来源

| 来源 | 网址 | 格式 | 导入方式 | 难度 |
|------|------|------|----------|------|
| Free Problem Set | github.com/zhblue/freeproblemset | FPS XML | `import_fps_v15.py` | 低 |
| Hydro | hydro.ac | YAML + MD + testdata | `import_hydro_problems.py` | 中（需注册账号导出） |
| Kattis | open.kattis.com | 自有格式 | 需申请 → 转换 → API导入 | 高（需申请 + 格式转换） |
| Competitive Companion | 浏览器扩展 | JSON | 需自行编写转换 | 中 |

### 6.1 Hydro 获取更多题目

1. 注册 Hydro 账号并完成实名验证
2. 在目标题库（如蓝桥杯真题、USACO 等）页面选择导出
3. 下载的 ZIP 解压到 `fps-problems/Export/` 下
4. 运行 `import_hydro_problems.py`

**注意**: Hydro 上大部分题目是 remote-judge 镜像，没有本地测试数据。只有题目管理者导出的包才包含完整测试数据。

### 6.2 Kattis 申请流程

详见 `docs/open.kattis.com/application-email-draft.md` 和 `docs/open.kattis.com/integration-plan.md`。

简要流程：
1. 向 problems@kattis.com 发送申请邮件
2. 获得访问权限后下载题目包
3. 编写 Kattis→QDUOJ 格式转换脚本
4. 通过 Admin API 导入

---

## 7. 常见问题

### Q: 导入后题目不可见？
```bash
docker exec cdut-oj-backend python manage.py shell -c "
from problem.models import Problem
Problem.objects.filter(visible=False).update(visible=True)
"
```

### Q: FPS 导入报 NoneType 错误？
修改 `import_fps_v15.py` 中处理 `description` 字段的代码，添加空值检查：
```python
if description is None:
    description = ""
```

### Q: Admin API 返回 `invalid-samples`？
`samples` 列表不能为空。若题目无样例，用第一个测试用例填充。

### Q: Admin API 返回 `invalid-test_case_id`？
上传测试数据后，返回的 test_case_id 键名是 `id` 而非 `test_case_id`。

### Q: 上传测试数据返回 `{"error": "error"}`？
form data 中缺少 `"spj": "false"` 字段。

### Q: 如何检查已有题目？
```bash
# 总数
docker exec cdut-oj-backend python manage.py shell -c "
from problem.models import Problem; print(Problem.objects.count())"

# 按前缀统计
docker exec cdut-oj-backend python manage.py shell -c "
from problem.models import Problem
for p in Problem.objects.order_by('_id')[:5]:
    print(f'{p._id}: {p.title}, visible={p.visible}, tc={p.test_case_id[:16]}')"

# API 查询
python3 -c "
import requests; r = requests.get('http://localhost:8000/api/problem',
    params={'limit': 10, 'keyword': 'LQ'}); print(r.json()['data']['total'])"
```

---

## 8. 文件清单

| 文件 | 用途 |
|------|------|
| `scripts/import/import_fps_v15.py` | FPS XML 批量导入（Django shell） |
| `scripts/import/import_hydro_problems.py` | Hydro 格式导入（Admin API） |
| `scripts/import/import_10_problems.py` | 10题手工导入参考脚本 |
| `backups/qduoj_full_*.dump` | PostgreSQL 自定义格式备份 |
| `backups/qduoj_full_*.sql` | SQL 纯文本备份 |
| `backups/qduoj_testcase_*.tar.gz` | 测试数据目录备份 |
| `fps-problems/fps-examples/` | FPS XML 源文件 |
| `fps-problems/Export/` | Hydro 导出题目目录 |