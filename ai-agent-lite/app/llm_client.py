"""LLM client with retry, timeout, and structured error handling."""
import asyncio
import json
import logging

import httpx

from app.config import settings
from app.errors import AppError
from app.models.enums import ErrorCode

logger = logging.getLogger("ai-agent-lite.llm")


def _mask_key(key: str) -> str:
    """Mask API keys in logs."""
    if len(key) <= 8:
        return "***"
    return key[:4] + "..." + key[-4:]


class LlmClient:
    """Async LLM client with retry and streaming support."""

    # Fallback system prompt — loaded from prompts.yaml at runtime when available.
    _INLINE_SYSTEM_PROMPT = (
        "You are part of an AI tutoring system for programming competitions. "
        "All your responses to the student MUST be in Chinese (简体中文). "
        "Code, variable names, and technical terms may remain in English, "
        "but all explanatory text, commentary, and instructions must be in Chinese."
    )

    def __init__(self) -> None:
        self.base_url = settings.llm_base_url
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.timeout_seconds = settings.llm_timeout
        self._system_prompt = None  # Lazy-loaded from YAML

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _get_system_prompt(self) -> str:
        """Load system prompt from YAML, fallback to inline default."""
        if self._system_prompt is None:
            from app.prompts import get_prompt
            self._system_prompt = get_prompt("system") or self._INLINE_SYSTEM_PROMPT
        return self._system_prompt

    def _inject_system(self, messages: list[dict]) -> list[dict]:
        """Prepend system prompt if no system message is already present."""
        if messages and messages[0].get("role") == "system":
            return messages
        return [{"role": "system", "content": self._get_system_prompt()}] + messages

    async def complete(self, messages: list[dict]) -> str:
        """Non-streaming completion with retry logic."""
        if not self.enabled:
            return self._fallback(messages)

        messages = self._inject_system(messages)
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(settings.llm_max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)

                    if response.status_code == 429:
                        if attempt < settings.llm_max_retries:
                            logger.warning("LLM rate limited, retry %d/%d", attempt + 1, settings.llm_max_retries)
                            await asyncio.sleep(settings.llm_retry_delay * (2 ** attempt))
                            continue
                        raise AppError(ErrorCode.LLM_RATE_LIMIT, "LLM provider rate limit exceeded")

                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return str(content).strip() or "OK"

            except AppError:
                raise
            except httpx.TimeoutException:
                if attempt < settings.llm_max_retries:
                    logger.warning("LLM timeout, retry %d/%d", attempt + 1, settings.llm_max_retries)
                    await asyncio.sleep(settings.llm_retry_delay)
                    continue
                raise AppError(ErrorCode.LLM_TIMEOUT, f"LLM request timed out after {self.timeout_seconds}s")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < settings.llm_max_retries:
                    logger.warning("LLM server error %d, retry %d/%d", exc.response.status_code, attempt + 1, settings.llm_max_retries)
                    await asyncio.sleep(settings.llm_retry_delay)
                    continue
                raise AppError(ErrorCode.LLM_SERVER_ERROR, f"LLM server returned {exc.response.status_code}")
            except Exception as exc:
                logger.exception("Unexpected LLM error: %s", exc)
                last_error = exc

        raise AppError(ErrorCode.INTERNAL, "LLM call failed after retries") from last_error

    async def stream(self, messages: list[dict]):
        """Streaming completion. Yields content chunks."""
        if not self.enabled:
            yield self._fallback(messages)
            return

        messages = self._inject_system(messages)
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            return
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
        except httpx.TimeoutException:
            raise AppError(ErrorCode.LLM_TIMEOUT, "LLM stream timed out")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise AppError(ErrorCode.LLM_RATE_LIMIT, "LLM rate limit during stream")
            raise AppError(ErrorCode.LLM_SERVER_ERROR, f"LLM stream error {exc.response.status_code}")
        except AppError:
            raise
        except Exception as exc:
            logger.exception("Unexpected stream error: %s", exc)
            raise AppError(ErrorCode.INTERNAL, "LLM stream failed") from exc

    @staticmethod
    def _fallback(messages: list[dict]) -> str:
        if not messages:
            return "Ready."
        last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if not last:
            return "Ready."
        text = str(last.get("content", "")).strip()
        if not text:
            return "Ready."
        return f"Received: {text[:200]}"