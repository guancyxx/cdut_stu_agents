# OJ 后端迁移合并方案

> 目标：彻底移除 QDUOJ 依赖，ai-agent-lite 直接与代码执行沙盒交互。
> 日期：2026-05-11
> 状态：Phase4 已完成（已移除 QDUOJ 运行依赖）

---

## 1. 现状分析

### 1.1 当前架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                      │
├───────────────┬──────────────────────┬───────────────────────┤
│  前端 (Vue)   │  AI Agent (FastAPI)  │    QDUOJ (Django)     │
│  port 5173    │  port 8850:8848      │    port 8000          │
│               │                      │                       │
│  vue-ai-chat  │  ai-agent-lite       │  oj-backend:1.6.1     │
│               │                      │  oj-judge:1.6.1       │
│               │                      │  oj-postgres:10       │
│               │                      │  oj-redis:4.0         │
└───────────────┴──────────────────────┴───────────────────────┘
```

### 1.2 QDUOJ 依赖清单

| 组件 | 用途 | 耦合方式 |
|------|------|----------|
| `oj-backend` (Django) | Admin API：登录、题目CRUD、提交管理 | ai-agent-lite 通过 HTTP 调用 `/api/admin/problem` |
| `oj-judge` | 代码编译运行、判题 | oj-backend 内部调度，ai-agent-lite 不直接访问 |
| `oj-postgres` | 共享数据库 | ai-agent-lite 直连读写 problem 表 + ai_agent schema |
| `oj-redis` | Celery 任务队列 | ai-agent-lite 的 Celery worker 使用 |
| `qduoj/data/backend/test_case` | 测试用例文件 | 通过 Docker volume 挂载到 `/data/test_cases` |

### 1.3 关键代码文件

```
ai-agent-lite/app/
├── config.py              # OJ_API_URL, OJ_ADMIN_USER, OJ_ADMIN_PASS
├── database.py            # 直连 oj-postgres:5432
├── main.py                # 路由注册
├── routers/
│   ├── problem_upload.py  # 题目创建 → 调 problem_service
│   ├── problem_audit.py   # 触发 audit Celery 任务
│   ├── oj_test_cases.py    # 读取 /data/test_cases 目录
│   └── submission_events.py # 接收前端提交结果 (fallback API)
├── services/
│   ├── problem_service.py # 直写 QDUOJ problem 表
│   └── submission_summary.py # 解析 submission 结果
├── tasks/
│   └── problem_auditor.py # QDUOJ Admin API 登录 + 题目 CRUD
└── celery_app.py          # Redis broker 依赖
```

---

## 2. Sandbox 方案选型

### 2.1 候选项对比

| 维度 | **isolate** | nsjail | Judge0 | DMOJ judge | subprocess+seccomp |
|------|-------------|--------|--------|------------|-------------------|
| GitHub Stars | 1.4k | 3.9k | 4.2k | 972 | N/A |
| 语言 | C | C++ | Ruby | Python | Python |
| 隔离技术 | namespaces + cgroups + seccomp | namespaces + seccomp-bpf + cgroups | Docker container | seccomp (cptbox) | seccomp only |
| 维护者 | IOI / Martin Mareš | Google | Herman Z. Dosilovic | DMOJ (quantum5) | 自建 |
| 最近更新 | last week (v2.5) | active | 3 days ago | last week | N/A |
| IOI 使用 | ✅ (CMS 官方) | ❌ | ❌ | ❌ | ❌ |
| Python 接口 | subprocess 调用 CLI | subprocess 调用 CLI | REST API | Python native | Python native |
| Docker 兼容 | ✅ (需 privileged) | ✅ (需 privileged) | ✅ | ✅ | ✅ (no privileged) |
| 许可证 | GPL-2.0 | Apache-2.0 | MIT | AGPL-3.0 | 自定 |

### 2.2 推荐：isolate

**理由：**
1. **行业标准** — IOI 官方竞赛平台 CMS 的底层沙盒，经过全球竞赛实战验证
2. **安全成熟** — 三层隔离：Linux namespaces (PID/NET/IPC/UTS/MOUNT) + cgroups (CPU/memory) + seccomp-bpf
3. **接口简洁** — CLI 工具，一行命令即可运行：
   ```bash
   isolate --init --cg -b 0                    # 创建沙盒
   isolate --run -b 0 --time=1.0 --mem=262144  # 运行程序
   isolate --cleanup -b 0                      # 清理
   ```
4. **主动维护** — 2026年5月仍在发布新版本 (v2.5)
5. **精确资源控制** — wall time、CPU time、memory、processes、disk 均可精确限制

**不推荐 Judge0 / DMOJ judge 的理由：**
- Judge0 是完整的代码执行平台（Ruby/Rails），引入太重，且其底层实际也使用 isolate
- DMOJ judge 是 Python 方案，但强绑定 DMOJ 生态，cptbox 沙盒不如 isolate 成熟
- nsjail 更偏向安全研究/fuzzing 场景，学习曲线陡峭

---

## 3. 目标架构

### 3.1 移除的组件

```
❌ oj-backend (Django)     → ai-agent-lite 自行管理题目 + 提交
❌ oj-judge                → 替换为 isolate sandbox
❌ oj-postgres (QDUOJ DB)  → 独立 PostgreSQL 实例
❌ oj-redis (QDUOJ Redis)  → 独立 Redis 实例
```

### 3.2 目标 Docker Compose

```yaml
services:
  # ── 保留并改造 ──
  ai-agent-lite:        # FastAPI 后端（新增 sandbox 集成）
  vue-ai-chat:          # Vue 前端（不变）
  
  # ── 新增 ──
  cdut-postgres:        # 独立 PG（从 oj-postgres 迁移数据）
  cdut-redis:           # 独立 Redis
  cdut-sandbox:         # isolate sandbox 容器（privileged）
  
  # ── 移除 ──
  # oj-backend, oj-judge, oj-postgres, oj-redis
```

### 3.3 新的判题流程

```
Vue 前端 → POST /api/submission {code, language, problem_id}
         ↓
ai-agent-lite (FastAPI)
  ├─ 1. 从 PG 读取 problem 信息 + test_case_id
  ├─ 2. 读取 test_case 文件 (本地目录 /data/test_cases/)
  ├─ 3. 调用 isolate sandbox 编译运行
  │      isolate --init --cg -b $BOX_ID
  │      isolate --run  -b $BOX_ID --time=1.0 --mem=262144 \
  │               --stdin=$INPUT --stdout=out --stderr=err \
  │               -- /usr/bin/python3 solution.py
  │      isolate --cleanup -b $BOX_ID
  ├─ 4. 对比输出与预期结果
  └─ 5. 写入 submission 记录到 PG
         ↓
返回结果给前端 (AC/WA/TLE/MLE/RE/CE)
```

---

## 4. 数据迁移策略

### 4.1 需要保留的数据

| 表 | 说明 | 迁移方式 |
|----|------|----------|
| `problem` | 2683 道题目 | pg_dump → pg_restore 到新实例 |
| `problem_tag` | 题目标签 | 同上 |
| `problem_tags` | 关联表 | 同上 |
| `ai_agent.*` | AI Agent 会话、消息、审核记录 | 同上 |
| `test_case` 文件 | ~30GB 测试数据 | rsync 到新目录 |

### 4.2 需要重新设计的表

| 表 | 问题 | 新设计 |
|----|------|--------|
| `submission` | QDUOJ 专有 schema | 新建 `ai_agent.submission` 表 |
| `contest` / `contest_problem` | 从未使用 | 按需新建 |

### 4.3 迁移步骤

```bash
# 1. 导出数据
pg_dump -h localhost -U onlinejudge -d onlinejudge \
  -t problem -t problem_tag -t problem_tags \
  -n ai_agent --no-owner > oj_data.sql

# 2. 创建新数据库
docker exec cdut-postgres psql -U cdut -c "CREATE DATABASE cdut_oj"

# 3. 导入
psql -h localhost -U cdut -d cdut_oj < oj_data.sql

# 4. 迁移 test_case 文件
rsync -av qduoj/data/backend/test_case/ data/test_cases/
```

---

## 5. 实施阶段

### Phase 1: Sandbox 集成 (1-2 天)

**目标：** isolate 在 Docker 中正常编译运行 C/C++/Python3/Java 代码

```
□ isolate 编译 + Dockerfile
□ 验证各语言编译运行
□ 验证资源限制 (time/memory) 生效
□ 编写 sandbox.py 封装模块
```

### Phase 2: 数据库独立 (半天)

```
□ 启动独立的 PostgreSQL + Redis 容器
□ 迁移数据和 test_case 文件
□ 更新 ai-agent-lite 的 DB 连接配置
```

### Phase 3: 判题服务替换 (1-2 天)

```
□ 新写 judge_service.py（调用 isolate，对比输出，支持SPJ）
□ 新写 POST /api/submission 端点
□ 新写 ai_agent.submission 表 + ORM
□ 单元测试覆盖各判题结果
```

### Phase 4: QDUOJ 下线 + 清理 (半天)

```
- [x] 修改 docker-compose.yml 移除 QDUOJ 服务
- [x] 清理配置中的 OJ_API_URL / OJ_ADMIN_* 变量
- [x] 修改 problem_auditor.py 改用直连 PG（不再调 Admin API）
- [x] 全链路测试
- [x] 文档更新
```

---

## 6. 风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| isolate 需要 --privileged | 安全面扩大 | 仅给 sandbox 容器 privileged，网络隔离 |
| test_case 文件路径变更 | 题目数据读取失败 | Phase 2 做完整性校验 |
| SPJ (Special Judge) 逻辑 | 需自行实现 | QDUOJ SPJ 也是简单脚本，可复用 |
| Java 编译较慢 | 判题延迟 | 预留充足 timeout |
| 大量并发提交 | 沙盒资源竞争 | isolate 支持多 box 并行，加排队机制 |

---

## 7. 验收标准

- [ ] 提交 C/C++/Python3/Java 代码能正确返回判题结果
- [ ] 所有判题状态覆盖：AC, WA, TLE, MLE, RE, CE
- [ ] 时间/内存限制生效且精确 (±5%)
- [ ] SPJ 题目正常判题
- [ ] 2683 道题目全部可提交
- [ ] docker-compose.yml 中不含任何 QDUOJ 服务
- [ ] 代码中无 `OJ_API_URL` / `oj-backend` / `oj-judge` 引用
- [ ] 文档更新

---

## 8. 后续扩展方向

- 支持更多语言 (Go, Rust, JavaScript)
- 交互式判题 (Interactive Judge)
- 沙盒性能监控 (Prometheus metrics)
- 分布式判题 (多 sandbox worker)
