from __future__ import annotations

import asyncio

from backend.brain.agent import Agent, ConfirmBroker
from backend.brain.llm import LLMResponse, ToolInvocation
from backend.brain.prompts import build_system_prompt
from backend.config import AppSettings


class ScriptedProvider:
    name = "local"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def chat(self, messages, tools):
        self.calls += 1
        if not self.responses:
            raise AssertionError("provider called more often than expected")
        return self.responses.pop(0)


class FakeRouter:
    def __init__(self, provider):
        self.provider = provider
        self.settings = None

    def update(self, settings):
        self.settings = settings

    def online_ready(self):
        return False

    def provider_for(self, text, escalated=False):
        return self.provider

    def fallback_for(self, provider):
        return None


def build_agent(database, events, provider, approve=True):
    settings = AppSettings()
    broker = ConfirmBroker()

    async def emit(event):
        events.append(event)
        if event["type"] == "tool_confirm_request":
            request_id = event["data"]["request_id"]
            asyncio.get_running_loop().call_soon(broker.resolve, request_id, approve)

    agent = Agent(settings, database, emit, broker, router=FakeRouter(provider))
    return agent


def test_safe_tool_runs_and_answer_is_returned(database, context):
    events = []
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolInvocation(name="calcola", arguments={"espressione": "6*7"})],
            ),
            LLMResponse(text="The answer is 42."),
        ]
    )
    agent = build_agent(database, events, provider)
    result = asyncio.run(agent.run("calculate 6*7", "c1", []))
    assert result.text == "The answer is 42."
    assert any(event["type"] == "tool_result" for event in events)
    log = database.tool_log()
    assert log[0]["tool"] == "calcola"
    assert log[0]["status"] == "ok"


def test_dangerous_tool_requires_confirmation_and_records_denial(database, context):
    events = []
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolInvocation(name="esegui_python", arguments={"codice": "print(1)"})],
            ),
            LLMResponse(text="Understood, I will not run it."),
        ]
    )
    agent = build_agent(database, events, provider, approve=False)
    result = asyncio.run(agent.run("run some python", "c2", []))
    assert result.text.startswith("Understood")
    assert any(event["type"] == "tool_confirm_request" for event in events)
    assert database.tool_log()[0]["status"] == "denied"


def test_approved_dangerous_tool_executes_in_sandbox(database, context):
    events = []
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[
                    ToolInvocation(name="esegui_python", arguments={"codice": "print(21*2)"})
                ],
            ),
            LLMResponse(text="The snippet printed 42."),
        ]
    )
    agent = build_agent(database, events, provider, approve=True)
    result = asyncio.run(agent.run("run python to double 21", "c3", []))
    assert result.text == "The snippet printed 42."
    results = [event for event in events if event["type"] == "tool_result"]
    assert results and "42" in results[-1]["data"]["output"]


def test_invalid_arguments_are_reported_without_execution(database, context):
    events = []
    provider = ScriptedProvider(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolInvocation(name="calcola", arguments={"espressione": 7})],
            ),
            LLMResponse(text="I need a valid expression."),
        ]
    )
    agent = build_agent(database, events, provider)
    result = asyncio.run(agent.run("calculate something", "c4", []))
    assert result.text == "I need a valid expression."
    assert database.tool_log()[0]["status"] == "error"


def test_unknown_tool_is_rejected(database, context):
    events = []
    provider = ScriptedProvider(
        [
            LLMResponse(text="", tool_calls=[ToolInvocation(name="rm_rf", arguments={})]),
            LLMResponse(text="That tool does not exist."),
        ]
    )
    agent = build_agent(database, events, provider)
    asyncio.run(agent.run("delete everything", "c5", []))
    assert "Unknown tool" in database.tool_log()[-1]["error"]


def test_external_content_detection():
    agent = Agent(AppSettings(), None, None, ConfirmBroker())  # type: ignore[arg-type]
    messages = [{"role": "tool", "content": "<dati_esterni fonte='gmail'>hello</dati_esterni>"}]
    assert agent._external_read(messages) is True
    assert agent._external_read([{"role": "tool", "content": "plain"}]) is False


def test_system_prompt_uses_assistant_name_and_requires_tools():
    prompt = build_system_prompt(AppSettings(assistant_name="Nova"))
    assert "Nova" in prompt
    assert "call the math tools" in prompt.lower()
    assert "dati_esterni" in prompt
