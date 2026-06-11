"""
Tatsu AI — LLM Provider
========================
Abstraction layer over LLM backends.
Supports Ollama (local) and OpenAI-compatible APIs (Cloud).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator

import ollama
import openai

import config

logger = logging.getLogger("tatsu.llm")


@dataclass
class ToolCall:
    """Represents a single tool call from the LLM."""
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """Structured response from the LLM."""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    model: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider:
    """
    Provides a unified interface for LLM interactions.
    Uses Ollama for local or OpenAI for Cloud inference.
    """

    def __init__(self):
        self.provider_type = config.LLM_PROVIDER
        self.temperature = config.LLM_TEMPERATURE

        if self.provider_type == "openai":
            self.model = config.OPENAI_MODEL
            self.client = openai.AsyncOpenAI(
                base_url=config.OPENAI_BASE_URL,
                api_key=config.OPENAI_API_KEY
            )
            logger.info(f"OpenAI Provider initialized: model={self.model}")
        else:
            self.model = config.OLLAMA_MODEL
            self.client = ollama.AsyncClient(host=config.OLLAMA_BASE_URL)
            logger.info(f"Ollama Provider initialized: model={self.model}, url={config.OLLAMA_BASE_URL}")

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        """Send a chat completion request to the LLM."""
        if self.provider_type == "openai":
            return await self._chat_openai(messages, tools)
        else:
            return await self._chat_ollama(messages, tools)

    async def _chat_openai(self, messages, tools) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            # Convert ollama tool schema to openai tool schema
            openai_tools = [{"type": "function", "function": t} for t in tools]
            kwargs["tools"] = openai_tools

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"Cloud LLM request failed: {e}") from e

        msg = response.choices[0].message
        tool_calls = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                ))

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            model=response.model,
        )

    async def _chat_ollama(self, messages, tools) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": {"temperature": self.temperature},
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await self.client.chat(**kwargs)
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise RuntimeError(f"Ollama request failed: {e}") from e

        msg = response.message
        tool_calls = []

        if msg.tool_calls:
            for i, tc in enumerate(msg.tool_calls):
                tool_calls.append(ToolCall(
                    id=f"call_{i}",
                    name=tc.function.name,
                    arguments=tc.function.arguments if isinstance(tc.function.arguments, dict)
                              else json.loads(tc.function.arguments),
                ))

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            model=response.model or self.model,
        )

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        if tools:
            response = await self.chat(messages, tools)
            if response.has_tool_calls:
                yield json.dumps({
                    "type": "tool_calls",
                    "calls": [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
                })
                return
            else:
                yield response.content
                return

        if self.provider_type == "openai":
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "stream": True,
            }
            try:
                stream = await self.client.chat.completions.create(**kwargs)
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                logger.error(f"OpenAI Stream error: {e}")
                yield f"\n[Error: {e}]"
        else:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": self.temperature},
            }
            try:
                async for chunk in await self.client.chat(**kwargs):
                    if chunk.message and chunk.message.content:
                        yield chunk.message.content
            except Exception as e:
                logger.error(f"Ollama Stream error: {e}")
                yield f"\n[Error: {e}]"

    async def check_connection(self) -> bool:
        if self.provider_type == "openai":
            try:
                await self.client.models.list()
                return True
            except Exception as e:
                logger.error(f"OpenAI connection failed: {e}")
                return False
        else:
            try:
                await self.client.list()
                return True
            except Exception as e:
                logger.error(f"Ollama health check failed: {e}")
                return False
