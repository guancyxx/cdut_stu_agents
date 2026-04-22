# ai-agent-lite

Minimal replacement for youtu-agent in this project.

## Features
- WebSocket endpoint: `/ws`
- Health endpoint: `/healthz`
- In-memory per-session history keyed by `session_id` query param
- Compatible event format for current frontend (`init`, `raw.text`, `finish`, `error`)

## Environment
- `LITE_LLM_BASE_URL` e.g. `https://api.deepseek.com/v1`
- `LITE_LLM_API_KEY`
- `LITE_LLM_MODEL` default `deepseek-chat`
- `LITE_LLM_TIMEOUT` default `30`

If `LITE_LLM_BASE_URL` or `LITE_LLM_API_KEY` is missing, service falls back to echo-style response.

## Run (local)
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8848
```
