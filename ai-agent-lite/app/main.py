import json
import os
from dataclasses import dataclass, field
from typing import Dict, List

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


@dataclass
class SessionState:
    history: List[dict] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState()
        return self._sessions[session_id]


class LlmClient:
    def __init__(self) -> None:
        self.base_url = os.getenv('LITE_LLM_BASE_URL', '').strip()
        self.api_key = os.getenv('LITE_LLM_API_KEY', '').strip()
        self.model = os.getenv('LITE_LLM_MODEL', 'deepseek-chat').strip()
        self.timeout_seconds = float(os.getenv('LITE_LLM_TIMEOUT', '30'))

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def complete(self, messages: List[dict]) -> str:
        if not self.enabled:
            return self._fallback(messages)

        endpoint = self.base_url.rstrip('/') + '/chat/completions'
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.3,
        }
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data['choices'][0]['message']['content']
                return str(content).strip() or 'OK'
        except Exception:
            return self._fallback(messages)

    @staticmethod
    def _fallback(messages: List[dict]) -> str:
        if not messages:
            return 'Ready.'
        last = next((m for m in reversed(messages) if m.get('role') == 'user'), None)
        if not last:
            return 'Ready.'
        text = str(last.get('content', '')).strip()
        if not text:
            return 'Ready.'
        return f'Received: {text[:200]}'


app = FastAPI(title='ai-agent-lite')
store = SessionStore()
llm = LlmClient()


@app.get('/healthz')
async def healthz() -> dict:
    return {
        'ok': True,
        'llm_enabled': llm.enabled,
        'model': llm.model,
    }


async def send_text_stream(websocket: WebSocket, content: str, chunk_size: int = 80) -> None:
    content = content or ''
    if not content:
        await websocket.send_json({'type': 'raw', 'data': {'type': 'text', 'delta': '', 'inprogress': False}})
        return

    start = 0
    total = len(content)
    while start < total:
        end = min(start + chunk_size, total)
        piece = content[start:end]
        await websocket.send_json({'type': 'raw', 'data': {'type': 'text', 'delta': piece, 'inprogress': end < total}})
        start = end


@app.websocket('/ws')
async def ws_handler(websocket: WebSocket) -> None:
    await websocket.accept()

    connection_session_id = websocket.query_params.get('session_id') or websocket.query_params.get('sid') or 'default'
    state = store.get(connection_session_id)

    await websocket.send_json(
        {
            'type': 'init',
            'data': {
                'type': 'init',
                'default_agent': 'ai-agent-lite',
                'agent_type': 'simple',
                'sub_agents': None,
            },
        }
    )

    try:
        while True:
            raw_message = await websocket.receive_text()
            request = json.loads(raw_message)
            req_type = request.get('type')

            if req_type != 'query':
                if req_type == 'list_agents':
                    await websocket.send_json({'type': 'list_agents', 'data': {'type': 'list_agents', 'agents': ['ai-agent-lite']}})
                    continue
                await websocket.send_json({'type': 'error', 'data': {'type': 'error', 'message': 'Unsupported request type'}})
                await websocket.send_json({'type': 'finish'})
                continue

            content = request.get('content') or {}
            query_text = str(content.get('query', '')).strip()
            if not query_text:
                await websocket.send_json({'type': 'error', 'data': {'type': 'error', 'message': 'Query cannot be empty'}})
                await websocket.send_json({'type': 'finish'})
                continue

            state.history.append({'role': 'user', 'content': query_text})
            assistant_text = await llm.complete(state.history)
            state.history.append({'role': 'assistant', 'content': assistant_text})

            await send_text_stream(websocket, assistant_text)
            await websocket.send_json({'type': 'finish'})

    except WebSocketDisconnect:
        return
