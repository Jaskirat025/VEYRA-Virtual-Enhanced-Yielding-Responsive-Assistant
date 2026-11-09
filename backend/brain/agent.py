"""Agentic loop: tool selection, validation, risk gates, execution and repair."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from backend.brain.llm import LLMError, LLMResponse, ToolInvocation
from backend.brain.prompts import build_messages
from backend.brain.router import Router
from backend.config import AppSettings
from backend.memory.db import Database
from backend.tools.registry import (
    Risk,
    ToolError,
    ToolSpec,
    ensure_tools_loaded,
    get_tool,
    validate_arguments,
)
from backend.tools.selector import select_tools

logger = logging.getLogger(__name__)

MAX_STEPS = 6
MAX_OUTPUT_CHARS = 2000
CONFIRM_TIMEOUT_S = 120.0
MAX_FAILURES_PER_TOOL = 2

EmitFn = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass
class AgentResult:
    text: str
    steps: int
    used_online: bool


class ConfirmBroker:
    """Pending confirmation requests keyed by request id."""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[bool]] = {}

    def create(self) -> tuple[str, asyncio.Future[bool]]:
        request_id = uuid.uuid4().hex
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        return request_id, future

    def resolve(self, request_id: str, approved: bool) -> bool:
        future = self._pending.get(request_id)
        if future is None or future.done():
            return False
        future.set_result(bool(approved))
        return True

    def cancel_all(self) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_result(False)
        self._pending.clear()

    async def wait(self, request_id: str, timeout: float = CONFIRM_TIMEOUT_S) -> bool:
        future = self._pending.get(request_id)
        if future is None:
            return False
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            return False
        finally:
            self._pending.pop(request_id, None)


def redact_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """Keep the tool log useful without storing long or sensitive payloads."""
    redacted: dict[str, Any] = {}
    for key, value in arguments.items():
        lowered = key.lower()
        if any(word in lowered for word in ("token", "password", "secret", "key")):
            redacted[key] = "[redacted]"
        elif isinstance(value, str) and len(value) > 300:
            redacted[key] = value[:120] + "...[truncated]"
        elif isinstance(value, (str, int, float, bool)) or value is None:
            redacted[key] = value
        else:
            redacted[key] = str(value)[:200]
    return redacted


def _truncate(text: str) -> str:
    cleaned = "".join(character for character in text if character >= " " or character in "\n\t")
    return (
        cleaned
        if len(cleaned) <= MAX_OUTPUT_CHARS
        else cleaned[:MAX_OUTPUT_CHARS] + "\n...[truncated]"
    )


def execute_tool(spec: ToolSpec, arguments: dict[str, Any]) -> tuple[str, str, int]:
    """Run a tool synchronously. Returns (status, text, duration_ms)."""
    started = time.monotonic()
    try:
        result = spec.func(**arguments)
        text = result if isinstance(result, str) else str(result)
        status = "ok"
    except ToolError as exc:
        text, status = str(exc), "error"
    except Exception as exc:  # a tool must never crash the app
        logger.exception("Tool %s failed", spec.name)
        text, status = f"The tool failed: {exc.__class__.__name__}.", "error"
    duration = int((time.monotonic() - started) * 1000)
    return status, _truncate(text), duration


class Agent:
    def __init__(
        self,
        settings: AppSettings,
        db: Database,
        emit: EmitFn,
        broker: ConfirmBroker,
        router: Router | None = None,
    ) -> None:
        self.settings = settings
        self.db = db
        self.emit = emit
        self.broker = broker
        self.router = router or Router(settings)
        self.registry = ensure_tools_loaded()

    def _schemas(self, text: str) -> tuple[list[dict[str, Any]], list[ToolSpec]]:
        selection = select_tools(text, self.registry, self.settings.tool_enabled)
        registry = {spec.name: spec for spec in selection.tools}
        return [spec.to_llm_schema() for spec in registry.values()], list(registry.values())

    async def _confirm(self, spec: ToolSpec, arguments: dict, external_read: bool) -> bool:
        request_id, _future = self.broker.create()
        await self.emit(
            {
                "type": "tool_confirm_request",
                "data": {
                    "request_id": request_id,
                    "tool": spec.name,
                    "category": spec.category.value,
                    "risk": spec.risk.value,
                    "summary": f"{spec.name} is about to run.",
                    "arguments": redact_arguments(arguments),
                    "external_content_read": external_read,
                    "timeout_s": int(CONFIRM_TIMEOUT_S),
                },
            }
        )
        approved = await self.broker.wait(request_id)
        if not approved:
            await self.emit(
                {
                    "type": "tool_result",
                    "data": {
                        "tool": spec.name,
                        "status": "denied",
                        "output": "The user declined this action.",
                    },
                }
            )
        return approved

    async def run(
        self, text: str, conversation_id: str, history: list[dict[str, Any]] | None = None
    ) -> AgentResult:
        self.router.update(self.settings)
        messages = build_messages(self.settings, history or [], text)
        schemas, _tools = self._schemas(text)

        failures: dict[str, int] = {}
        escalated = False
        used_online = False
        steps = 0
        final_text = ""

        for step in range(MAX_STEPS):
            steps = step + 1
            provider = self.router.provider_for(text, escalated=escalated)
            used_online = used_online or provider.name == "online"

            await self.emit({"type": "state", "state": "thinking", "detail": provider.name})

            try:
                response: LLMResponse = await provider.chat(messages, schemas)
            except LLMError as exc:
                fallback = self.router.fallback_for(provider)
                if fallback is None:
                    raise
                logger.warning(
                    "%s failed (%s); falling back to %s", provider.name, exc, fallback.name
                )
                await self.emit(
                    {
                        "type": "notice",
                        "data": {"message": f"{exc} Using the {fallback.name} model."},
                    }
                )
                provider = fallback
                used_online = used_online or provider.name == "online"
                response = await provider.chat(messages, schemas)

            if not response.tool_calls:
                final_text = response.text.strip()
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {
                            "id": call.call_id or uuid.uuid4().hex,
                            "name": call.name,
                            "arguments": call.arguments,
                        }
                        for call in response.tool_calls
                    ],
                }
            )

            external_read = self._external_read(messages)
            for index, call in enumerate(response.tool_calls):
                call_id = call.call_id or messages[-1]["tool_calls"][index]["id"]
                result_text, status = await self._execute_call(
                    call, call_id, conversation_id, steps, external_read
                )
                if status == "error":
                    failures[call.name] = failures.get(call.name, 0) + 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": call.name,
                        "content": result_text,
                    }
                )

            needs_escalation = (
                any(count >= MAX_FAILURES_PER_TOOL for count in failures.values()) or steps > 3
            )
            if needs_escalation and not escalated and self.router.online_ready():
                escalated = True
                await self.emit(
                    {
                        "type": "notice",
                        "data": {
                            "message": (
                                "The local model is struggling; continuing with the online model."
                            )
                        },
                    }
                )

            if step == MAX_STEPS - 1:
                final_text = (
                    "I could not finish this within the allowed steps. Try narrowing the request."
                )

        if not final_text:
            final_text = (
                "I could not produce an answer. Check that the local model is running, "
                "then try again."
            )

        await self.emit({"type": "state", "state": "speaking", "detail": ""})
        return AgentResult(text=final_text, steps=steps, used_online=used_online)

    def _external_read(self, messages: list[dict[str, Any]]) -> bool:
        return any(
            message.get("role") == "tool" and "<dati_esterni" in str(message.get("content", ""))
            for message in messages
        )

    async def _execute_call(
        self,
        call: ToolInvocation,
        call_id: str,
        conversation_id: str,
        step: int,
        external_read: bool,
    ) -> tuple[str, str]:
        spec = get_tool(call.name)
        if spec is None:
            self.db.log_tool_call(
                conversation_id=conversation_id,
                step=step,
                tool=call.name[:80],
                category="unknown",
                risk="unknown",
                args_redacted=redact_arguments(call.arguments),
                status="error",
                duration_ms=0,
                error=f"Unknown tool: {call.name}",
            )
            return f"Unknown tool: {call.name}.", "error"

        if not self.settings.tool_enabled(spec.name):
            return f"The tool {spec.name} is disabled in Settings.", "blocked"

        try:
            arguments = validate_arguments(spec, call.arguments)
        except ToolError as exc:
            self.db.log_tool_call(
                conversation_id=conversation_id,
                step=step,
                tool=spec.name,
                category=spec.category.value,
                risk=spec.risk.value,
                args_redacted=redact_arguments(call.arguments),
                status="error",
                duration_ms=0,
                error=str(exc),
            )
            return f"Invalid arguments: {exc}", "error"

        if spec.risk in (Risk.CONFIRM, Risk.DANGEROUS):
            await self.emit(
                {
                    "type": "tool_call",
                    "data": {
                        "tool": spec.name,
                        "category": spec.category.value,
                        "risk": spec.risk.value,
                        "arguments": redact_arguments(arguments),
                        "status": "awaiting_confirmation",
                    },
                }
            )
            if not await self._confirm(spec, arguments, external_read):
                self.db.log_tool_call(
                    conversation_id=conversation_id,
                    step=step,
                    tool=spec.name,
                    category=spec.category.value,
                    risk=spec.risk.value,
                    args_redacted=redact_arguments(arguments),
                    status="denied",
                    duration_ms=0,
                )
                return "The user declined this action.", "denied"

        await self.emit(
            {
                "type": "tool_call",
                "data": {
                    "tool": spec.name,
                    "category": spec.category.value,
                    "risk": spec.risk.value,
                    "arguments": redact_arguments(arguments),
                    "status": "running",
                },
            }
        )
        status, text, duration = await asyncio.to_thread(execute_tool, spec, arguments)
        self.db.log_tool_call(
            conversation_id=conversation_id,
            step=step,
            tool=spec.name,
            category=spec.category.value,
            risk=spec.risk.value,
            args_redacted=redact_arguments(arguments),
            status=status,
            duration_ms=duration,
            error=text if status == "error" else "",
            output_preview=text[:200],
        )
        await self.emit(
            {
                "type": "tool_result",
                "data": {
                    "tool": spec.name,
                    "risk": spec.risk.value,
                    "status": status,
                    "output": text[:500],
                    "duration_ms": duration,
                },
            }
        )
        return text, status


def parse_tool_arguments(raw: str) -> dict[str, Any]:
    """Small helper used by tests and the WS layer for confirm payloads."""
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        raise ToolError("Arguments must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ToolError("Arguments must be a JSON object.")
    return parsed
