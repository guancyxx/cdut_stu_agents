"""Base worker class and shared data models for specialized agents."""
import logging
from typing import Dict, Any, List, Callable, Awaitable

logger = logging.getLogger("ai-agent-lite.workers")


StreamCallback = Callable[[str, bool], Awaitable[None]]


class BaseWorker:
    """Base class for all specialized workers."""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def _complete_or_stream(
        self,
        prompt: str,
        on_chunk: StreamCallback | None = None,
    ) -> str:
        """Call LLM in streaming mode when callback is provided.

        Returns the full aggregated text in all cases.
        """
        messages = [{"role": "user", "content": prompt}]
        if on_chunk is None:
            return await self.llm.complete(messages)

        chunks: list[str] = []
        pending: str | None = None
        async for piece in self.llm.stream(messages):
            chunks.append(piece)
            if pending is not None:
                await on_chunk(pending, True)
            pending = piece

        if pending is not None:
            await on_chunk(pending, False)
        else:
            await on_chunk("", False)

        return "".join(chunks)

    async def process(
        self,
        user_input: str,
        state: Dict[str, Any],
        message_history: List[Dict[str, str]] = None,
        on_chunk: StreamCallback | None = None,
    ) -> "AgentResponse":
        """Process user input and return structured response."""
        raise NotImplementedError
