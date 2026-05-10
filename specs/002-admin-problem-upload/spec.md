# Spec: 管理员题目上传功能（单题/批量）

## Objective

为 CDUT OJ 系统的管理员提供题目上传功能，支持两种模式：

1. **单题上传**：通过表单在线创建题目（填写标题、描述、输入输出规格、样例、提示、标签、难度等），自动通过 QDUOJ Admin API 创建题目并上传测试数据
2. **批量上传**：上传 FPS XML 或 Hydro 格式的题目包（ZIP），由后端解析并批量导入

目标用户：OJ 管理员（root 账号或 Super Admin 角色的用户）

成功标准：
- 管理员可在 Vue AI Chat 前端的"管理"Tab 中进行单题和批量上传
- 单题上传后题目立即可在题库页面搜到
- 批量上传后显示导入进度和结果摘要
- 上传的题目包含完整的测试数据和正确的字段

## Tech Stack

- **前端**：Vue 3 (Composition API) + Vite，在现有 `frontend-vue-ai-chat` 项目内
- **后端代理**：ai-agent-lite (FastAPI) 作为中间层代理 QDUOJ Admin API
- **OJ API**：QDUOJ Admin API (`/api/admin/problem`, `/api/admin/test_case`)
- **认证**：复用 QDUOJ 现有 Admin API 认证（CSRF token + Session Cookie）
- **依赖库**：前端无新依赖；后端新增 `python-multipart`（文件上传）

## Commands

```bash
# Frontend dev
cd frontend-vue-ai-chat && npm run dev

# Backend dev
cd ai-agent-lite && uvicorn app.main:app --reload --port 8848

# Docker compose
cd /home/guancy/workspace/cdutstuagents && docker compose up -d --build vue-ai-chat ai-agent-lite

# Verify
curl -sS http://localhost:8850/health | python3 -m json.tool
curl -sS http://localhost:8000/api/problem?limit=5 | python3 -m json.tool
```

## Project Structure

```
frontend-vue-ai-chat/src/
├── components/
│   ├── AdminProblemUpload.vue   # NEW: 单题上传表单 + 批量上传面板
│   ├── CodeEditor.vue            # EXISTING
│   └── MessageBubble.vue         # EXISTING
├── composables/
│   ├── useOjAuthAndProblems.js  # EXTEND: 添加 admin API 方法
│   ├── useChatFeature.js         # EXISTING
│   └── useSessions.js            # EXISTING
├── services/
│   ├── apiClient.js              # EXTEND: 添加 admin API 调用
│   └── csrfService.js            # EXISTING
├── utils/
│   └── validators.js             # EXTEND: 添加表单验证
└── App.vue                        # EXTEND: 添加 admin tab

ai-agent-lite/app/
├── routers/
│   └── problem_upload.py          # NEW: 批量上传代理路由
├── services/
│   └── problem_import.py          # NEW: FPS/Hydro 解析 + 三阶段导入
└── main.py                        # EXTEND: 注册新路由
```

## Code Style

### Frontend (Vue 3 Composition API)

```vue
<script setup>
import { ref, computed } from 'vue'

const form = ref({
  title: '',
  difficulty: 'Low',
  // ...
})
const submitting = ref(false)

const handleSubmit = async () => {
  submitting.value = true
  try {
    // call API
  } finally {
    submitting.value = false
  }
}
</script>
```

- Use `ref()` / `computed()` from Vue 3 Composition API
- All UI text in Chinese（中文）
- Code comments in English
- Use `sanitizeTextInput()` from existing validators for all user input
- Error display: use inline error state, not `alert()`

### Backend (FastAPI)

```python
from fastapi import APIRouter, UploadFile, File, Depends

router = APIRouter(prefix="/admin/problems", tags=["admin-problem-upload"])

@router.post("/upload/batch")
async def upload_batch(file: UploadFile = File(...)):
    """Batch import problems from FPS XML or Hydro ZIP."""
    ...
```

- English docstrings, English comments
- Chinese string literals for user-facing error messages only
- Follow existing ai-agent-lite router patterns (see `problem_audit.py`)

## Architecture Decisions

### ADR-001: 全部走 ai-agent-lite 直写 DB（不经过 QDUOJ Admin API）

**决策**: 单题和批量上传全部通过 ai-agent-lite 直连 PostgreSQL 写入 `problem` 表，测试数据文件写入共享卷。

**理由**:
- ai-agent-lite 已有 PostgreSQL 直连（`LITE_DATABASE_URL` 指向 `onlinejudge` DB）
- FPS 导入脚本（`import_fps_v15.py`）已验证 Django ORM 直写 DB 路径可行
- 批量场景性能差距巨大（3次HTTP/题 vs 1次批量INSERT，150题 = 450次HTTP vs <10s）
- 避开 QDUOJ Admin API 的 CSRF/session 复杂度和已知分页 bug
- 统一架构：前端只跟 ai-agent-lite 通信，不直调 QDUOJ Admin API

**实施改动**:
1. docker-compose.yml: `test_case` 卷从 `:ro` 改为读写
2. ai-agent-lite 新增路由：`POST /admin/problems/create`（单题）、`POST /admin/problems/upload/batch`（批量）、`GET /admin/problems/import/status/:id`（进度）
3. ai-agent-lite 新增服务层：`ProblemService` 直接操作 `problem` 表
4. 前端统一通过 `/oj-test-cases` 前缀（或新增 `/admin-api` 前缀）与 ai-agent-lite 通信

### ADR-002: 测试数据存储路径

**决策**: 测试数据写入共享卷 `/data/test_case/`（容器内路径），与 QDUOJ backend 共享同一卷。

**理由**: QDUOJ backend 通过 `/data/test_case/` 读取测试数据，ai-agent-lite 需要写入同一目录。docker-compose 已定义该卷映射。

### ADR-003: 前端新增 Admin Tab 作为独立面板

**决策**: 在现有 Vue AI Chat 前端的 Tab 系统中增加一个 "管理" Tab，只有已登录的管理员用户可见。

**理由**:
- 不引入新的路由/页面，复用现有的 `activeTab` 机制
- 现有 Tab 有：home（聊天）、auth（登录/注册）、profile（个人信息）、problemset（题库）
- 新增 admin Tab 仅当 `ojUser.loggedIn && ojUser.adminType >= 1` 时显示

### ADR-004: 批量上传进度用轮询而非 SSE

**决策**: 批量上传使用传统 POST → 任务ID → 轮询模式，而非 SSE。

**理由**:
- ai-agent-lite 已有 Celery 任务基础设施，天然支持异步任务
- SSE 需要额外的长连接管理，增加复杂度
- 前端轮询更简单可靠，导入任务通常在几十秒到几分钟内完成

## API Design

> 全部 API 走 ai-agent-lite，不直调 QDUOJ Admin API。

### 1. Single Problem Create (前端 → ai-agent-lite → DB 直写)

```
POST /admin/problems/create
```

Request JSON:
```json
{
  "title": "两数相加",
  "difficulty": "Low",
  "source": "蓝桥杯",
  "description": "<p>给定两个整数...</p>",
  "input_description": "输入两个整数...",
  "output_description": "输出它们的和...",
  "samples": [{"input": "1 2", "output": "3"}],
  "hint": "注意数据范围",
  "tags": ["数学"],
  "visible": true,
  "languages": ["C", "C++", "Java", "Python3"],
  "time_limit": 1000,
  "memory_limit": 256,
  "test_case_file": "(multipart: test data ZIP)"
}
```

Response:
```json
{
  "success": true,
  "problem_id": "custom-ab1c",
  "db_id": 2684,
  "message": "题目创建成功"
}
```

Service flow: validate fields → generate _id → insert DB row → write test case files → compute test_case_score → update row

### 2. Batch Problem Import (前端 → ai-agent-lite → DB 批量写入)

```
POST /admin/problems/upload/batch
```

Request (multipart form):
- `file`: FPS XML or Hydro ZIP file
- `format`: "fps" | "hydro"
- `tags`: optional comma-separated tags to append
- `difficulty`: optional override ("Low"|"Mid"|"High")
- `visible`: optional boolean, default false

Response:
```json
{
  "task_id": "import_abc123",
  "status": "pending",
  "total": 0,
  "message": "文件已接收，正在处理..."
}
```

```
GET /admin/problems/import/status/{task_id}
```

Response:
```json
{
  "task_id": "import_abc123",
  "status": "running" | "completed" | "failed",
  "total": 150,
  "imported": 145,
  "skipped": 3,
  "failed": 2,
  "failed_details": [{"title": "...", "reason": "..."}]
}
```

### 3. Admin User Detection

前端通过 QDUOJ 公共 API 检测当前用户是否为管理员：
```
GET /api/profile → { data: { admin_type: 0 | 1 | 2 } }
```
- `0` = Regular User
- `1` = Admin
- `2` = Super Admin

只有 `admin_type >= 1` 才显示 Admin Tab。

## Component Design

### AdminProblemUpload.vue

```
┌──────────────────────────────────────────────┐
│  📋 题目管理                                  │
├──────────────┬───────────────────────────────┤
│  单题上传     │  批量导入                      │
├──────────────┴───────────────────────────────┤
│                                              │
│  [单题上传面板]                               │
│  标题: [__________]                          │
│  难度: [Low ▼]  来源: [__________]           │
│  题目描述: [富文本文区域]                      │
│  输入描述: [__________]                       │
│  输出描述: [__________]                       │
│  样例输入1: [__________]                      │
│  样例输出1: [__________]  [+添加样例]          │
│  提示: [__________]                           │
│  标签: [__________]                           │
│  测试数据: [上传 .zip 文件]                   │
│                                              │
│  [提交创建]                                   │
│                                              │
│  ── 或 ──                                    │
│                                              │
│  [批量导入面板]                               │
│  格式: [FPS XML ▼ | Hydro ZIP]               │
│  文件: [选择文件或拖拽上传]                    │
│  追加标签: [__________]                       │
│  默认难度: [Mid ▼]                            │
│  导入后设为公开: [☐]                           │
│                                              │
│  [开始导入]                                   │
│                                              │
│  导入进度: 145/150 已导入，3 跳过，2 失败       │
│  [查看详情]                                   │
└──────────────────────────────────────────────┘
```

## Testing Strategy

- **单题上传**: 手动测试 — 创建题目 → 在题库搜索 → 验证字段完整性
- **批量上传**: 用小型 FPS XML 文件（5-10题）测试完整流程
- **权限验证**: 非 Admin 用户应无法看到 Admin Tab，直接调用 Admin API 应返回 `login-required`
- **边界测试**: 空 ZIP、损坏的 XML、超大文件（>50MB）

## Boundaries

- **Always**: 验证管理员权限后再显示/执行操作；使用 `sanitizeTextInput()` 处理所有用户输入；中文 UI 文案；英文代码注释
- **Ask first**: 修改数据库 Schema；添加新的 Docker 服务；更改现有 API 接口
- **Never**: 在前端存储 QDUOJ Admin 密码；跳过权限检查；直接操作数据库绕过 API

## Success Criteria

1. 管理员登录后可以看到 "管理" Tab
2. 在管理 Tab 中可以通过表单创建单题，创建后题目可被搜索到
3. 可以上传 FPS XML 或 Hydro ZIP 文件批量导入题目
4. 批量导入显示进度（已导入/总数/失败数）
5. 非管理员用户无法看到管理面板
6. 三阶段创建流程（create → upload → update）全部成功且数据完整

## Open Questions

1. ~上传入口位置~ → 已决定在 Vue 前端新增管理 Tab
2. ~批量格式~ → FPS XML 和 Hydro ZIP 都支持
3. ~认证方式~ → 单题走 QDUOJ Admin API 直通，批量走 ai-agent-lite 代理
4. 测试数据 ZIP 格式：QDUOJ 要求 `1.in`/`1.out`/`2.in`/`2.out` — 单题上传时由用户手动打包还是前端生成？
5. 富文本编辑器：描述字段是否需要 Markdown 编辑器？（MVP 阶段可用普通 textarea + 预览）