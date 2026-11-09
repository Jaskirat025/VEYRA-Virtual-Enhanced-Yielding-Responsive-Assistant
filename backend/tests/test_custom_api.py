from __future__ import annotations

import httpx
import pytest
from backend.brain.prompts import build_system_prompt
from backend.config import AppSettings, CustomApiSettings
from backend.tools.builtin import custom_api as custom_api_module
from backend.tools.registry import Risk, ToolError, get_tool
from pydantic import ValidationError


def make_api(**overrides) -> CustomApiSettings:
    data = {
        "id": "exa",
        "name": "Exa search",
        "description": "Search the web for current sources.",
        "base_url": "https://api.exa.ai",
        "path": "/search",
        "method": "POST",
        "auth_header": "x-api-key",
        "auth_prefix": "",
        "headers": {"content-type": "application/json"},
    }
    data.update(overrides)
    return CustomApiSettings(**data)


def install_fake_client(monkeypatch, status: int = 200, text: str = '{"results":["one"]}'):
    calls: list[tuple[str, str, dict]] = []

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method: str, url: str, **kwargs):
            calls.append((method, url, kwargs))
            return httpx.Response(
                status,
                text=text,
                request=httpx.Request(method, url),
            )

    monkeypatch.setattr(custom_api_module.httpx, "Client", FakeClient)
    return calls


def test_custom_api_is_confirmation_gated():
    spec = get_tool("chiama_api")
    assert spec is not None
    assert spec.category.value == "custom"
    assert spec.risk is Risk.CONFIRM


def test_custom_api_posts_json_with_configured_secret(context, monkeypatch):
    context.settings.custom_apis = [make_api()]
    monkeypatch.setattr(custom_api_module, "get_secret", lambda name: "secret-value")
    calls = install_fake_client(monkeypatch)

    result = custom_api_module.chiama_api(
        "exa",
        '{"query":"latest AI news","numResults":3}',
    )

    assert "<dati_esterni fonte='custom_api:exa'>" in result
    assert '"one"' in result
    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url == "https://api.exa.ai/search"
    assert kwargs["headers"]["x-api-key"] == "secret-value"
    assert kwargs["headers"]["content-type"] == "application/json"
    assert kwargs["json"] == {"query": "latest AI news", "numResults": 3}


def test_custom_api_get_uses_query_parameters(context, monkeypatch):
    context.settings.custom_apis = [
        make_api(method="GET", path="/search", auth_header="x-api-key", auth_prefix="")
    ]
    monkeypatch.setattr(custom_api_module, "get_secret", lambda name: "")
    calls = install_fake_client(monkeypatch)

    custom_api_module.chiama_api("exa", '{"query":"news","limit":5}')

    _, _, kwargs = calls[0]
    assert kwargs["params"] == {"query": "news", "limit": "5"}
    assert "json" not in kwargs
    assert "x-api-key" not in kwargs["headers"]


def test_disabled_and_unknown_apis_are_rejected(context):
    context.settings.custom_apis = [make_api(enabled=False)]
    with pytest.raises(ToolError, match="disabled"):
        custom_api_module.chiama_api("exa", "{}")
    with pytest.raises(ToolError, match="Unknown"):
        custom_api_module.chiama_api("other", "{}")


def test_invalid_payload_and_http_error_are_safe(context, monkeypatch):
    context.settings.custom_apis = [make_api()]
    monkeypatch.setattr(custom_api_module, "get_secret", lambda name: "secret-value")

    with pytest.raises(ToolError, match="valid JSON"):
        custom_api_module.chiama_api("exa", "not-json")

    install_fake_client(monkeypatch, status=500, text="upstream failed for secret-value")
    with pytest.raises(ToolError) as error:
        custom_api_module.chiama_api("exa", "{}")
    assert "HTTP 500" in str(error.value)
    assert "secret-value" not in str(error.value)


def test_custom_api_definitions_reject_unsafe_fields():
    with pytest.raises(ValidationError):
        CustomApiSettings(
            id="bad",
            name="Bad",
            base_url="file:///etc/passwd",
        )
    with pytest.raises(ValidationError):
        make_api(path="../private")
    with pytest.raises(ValidationError):
        make_api(headers={"Authorization": "literal-secret"})
    with pytest.raises(ValidationError):
        make_api(auth_header="Host")
    with pytest.raises(ValidationError):
        AppSettings(custom_apis=[make_api(), make_api(name="Duplicate")])


def test_prompt_lists_only_names_not_urls_or_keys():
    prompt = build_system_prompt(
        AppSettings(custom_apis=[make_api(description="Useful for research.")])
    )
    assert "chiama_api" in prompt
    assert "exa: Exa search" in prompt
    assert "https://api.exa.ai" not in prompt
    assert "secret" not in prompt.lower()
