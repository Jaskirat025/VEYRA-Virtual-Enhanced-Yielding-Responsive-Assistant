"""LLM providers: local Ollama and an optional OpenAI-compatible endpoint."""

from __future__ import annotations

import contextlib
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


def ollama_url() -> str:
    """Return the local runtime URL, including the bundled Ollama port."""
    return (os.environ.get("VEYRA_OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")


class LLMError(Exception):
    """A provider failure with a message that is safe to show to the user."""


@dataclass
class ToolInvocation:
    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    provider: str = "local"


class ChatProvider(Protocol):
    name: str

    async def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMResponse: ...


def _normalise_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {}
    return {}


def to_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "content": str(message.get("content", "")),
                    "tool_name": message.get("name", ""),
                }
            )
        elif role == "assistant" and message.get("tool_calls"):
            converted.append(
                {
                    "role": "assistant",
                    "content": message.get("content", ""),
                    "tool_calls": [
                        {
                            "function": {
                                "name": call["name"],
                                "arguments": call.get("arguments", {}),
                            }
                        }
                        for call in message["tool_calls"]
                    ],
                }
            )
        else:
            converted.append({"role": role, "content": message.get("content", "")})
    return converted


def to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for message in messages:
        role = message.get("role")
        if role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": message.get("tool_call_id", ""),
                    "content": str(message.get("content", "")),
                }
            )
        elif role == "assistant" and message.get("tool_calls"):
            converted.append(
                {
                    "role": "assistant",
                    "content": message.get("content", "") or None,
                    "tool_calls": [
                        {
                            "id": call.get("id") or f"call_{index}",
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call.get("arguments", {})),
                            },
                        }
                        for index, call in enumerate(message["tool_calls"])
                    ],
                }
            )
        else:
            converted.append({"role": role, "content": message.get("content", "")})
    return converted


class OllamaProvider:
    name = "local"

    def __init__(
        self,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        context_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or ollama_url()).rstrip("/")
        self.model = model
        self.temperature = temperature
        self.context_tokens = context_tokens
        self.timeout = timeout

    async def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_ollama_messages(messages),
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.context_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.HTTPError as exc:
            raise LLMError("The local model runtime is not reachable.") from exc

        if response.status_code >= 400:
            detail = ""
            with contextlib.suppress(ValueError):
                detail = response.json().get("error", "")
            hint = " Is the model pulled?" if response.status_code == 404 else ""
            raise LLMError(f"Local model error {response.status_code}. {detail}{hint}".strip())

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("The local model returned an invalid response.") from exc

        message = data.get("message") or {}
        calls: list[ToolInvocation] = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            name = function.get("name") or ""
            if not name:
                continue
            calls.append(
                ToolInvocation(
                    name=name,
                    arguments=_normalise_arguments(function.get("arguments")),
                )
            )

        return LLMResponse(
            text=str(message.get("content") or "").strip(),
            tool_calls=calls,
            provider=self.name,
        )


class OnlineProvider:
    """OpenAI-compatible chat completions client (Mercury or any equivalent)."""

    name = "online"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        temperature: float = 0.2,
        timeout: float = 60.0,
    ) -> None:
        if not base_url:
            raise LLMError("The online model base URL is not configured.")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key.strip()
        self.temperature = temperature
        self.timeout = timeout

    async def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(messages),
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise LLMError("The online model is unreachable. Staying local.") from exc

        if response.status_code in (401, 403):
            raise LLMError("The online model rejected the API key.")
        if response.status_code == 429:
            raise LLMError("The online model is rate limited. Staying local.")
        if response.status_code >= 400:
            raise LLMError(f"The online model returned error {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMError("The online model returned an invalid response.") from exc

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("The online model returned an unexpected payload.") from exc

        calls: list[ToolInvocation] = []
        for index, call in enumerate(message.get("tool_calls") or []):
            function = call.get("function") or {}
            name = function.get("name") or ""
            if not name:
                continue
            calls.append(
                ToolInvocation(
                    name=name,
                    arguments=_normalise_arguments(function.get("arguments")),
                    call_id=call.get("id") or f"call_{index}",
                )
            )

        return LLMResponse(
            text=str(message.get("content") or "").strip(),
            tool_calls=calls,
            provider=self.name,
        )


async def fetch_ollama_models(base_url: str | None = None, timeout: float = 3.0) -> list[str]:
    base_url = (base_url or ollama_url()).rstrip("/")
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(f"{base_url}/api/tags")
        response.raise_for_status()
        data = response.json()
        return [model.get("name", "") for model in data.get("models", []) if model.get("name")]
