"""Provider routing: local by default, online for hard requests with fallback."""

from __future__ import annotations

import re

from backend.brain.llm import ChatProvider, OllamaProvider, OnlineProvider
from backend.config import AppSettings
from backend.secrets import get_secret

HARD_PATTERNS = (
    r"```",
    r"\brefactor\b",
    r"\bdebug\b",
    r"\barchitect",
    r"\banaly[sz]e\b",
    r"\bstep by step\b",
    r"\bexplain in detail\b",
    r"\bwrite (?:a|the) (?:long|full)\b",
    r"\brifattor",
    r"\banalizz",
    r"\bspiega in dettaglio\b",
    r"\bscrivi (?:un|il) (?:lungo|completo)\b",
    r"详细",
    r"重构",
)

ONLINE_PREFIX = ("http://", "https://")


def looks_hard(text: str) -> bool:
    if len(text) > 500:
        return True
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in HARD_PATTERNS)


class Router:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def update(self, settings: AppSettings) -> None:
        self.settings = settings

    def online_ready(self) -> bool:
        models = self.settings.models
        return bool(
            models.online_enabled
            and models.online_base_url.startswith(ONLINE_PREFIX)
            and models.online_model
            and get_secret("online_api_key")
        )

    def local_provider(self) -> OllamaProvider:
        models = self.settings.models
        return OllamaProvider(
            base_url="http://127.0.0.1:11434",
            model=models.local_model,
            temperature=models.temperature,
            context_tokens=models.context_tokens,
        )

    def online_provider(self) -> OnlineProvider:
        models = self.settings.models
        key = get_secret("online_api_key") or ""
        return OnlineProvider(
            base_url=models.online_base_url,
            model=models.online_model,
            api_key=key,
            temperature=max(models.temperature, 0.1),
        )

    def provider_for(self, text: str, escalated: bool = False) -> ChatProvider:
        if self.online_ready() and (escalated or looks_hard(text)):
            return self.online_provider()
        return self.local_provider()

    def fallback_for(self, provider: ChatProvider) -> ChatProvider | None:
        if provider.name == "online":
            return self.local_provider()
        if self.online_ready():
            return self.online_provider()
        return None
