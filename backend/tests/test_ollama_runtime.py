from __future__ import annotations

from backend.brain.llm import DEFAULT_OLLAMA_URL, ollama_url


def test_ollama_url_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("VEYRA_OLLAMA_URL", raising=False)
    assert ollama_url() == DEFAULT_OLLAMA_URL


def test_ollama_url_uses_bundled_runtime_port(monkeypatch):
    monkeypatch.setenv("VEYRA_OLLAMA_URL", "http://127.0.0.1:11435/")
    assert ollama_url() == "http://127.0.0.1:11435"
