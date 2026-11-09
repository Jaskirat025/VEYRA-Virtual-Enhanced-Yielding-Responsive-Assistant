"""Dynamic tool selection.

The model is never given every tool. A deterministic keyword pre-classifier
maps the request to one or more categories, and only those tools are exposed.
Optional embedding-based ranking can be enabled later without changing the
interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.tools.registry import Category, ToolSpec

KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.SYSTEM: (
        "open",
        "close",
        "launch",
        "volume",
        "mute",
        "brightness",
        "screenshot",
        "screen",
        "ram",
        "memory",
        "cpu",
        "battery",
        "clipboard",
        "copy",
        "window",
        "windows",
        "app",
        "apri",
        "chiudi",
        "luminosita",
        "schermo",
        "appunti",
        "finestre",
        "打开",
        "关闭",
        "音量",
        "亮度",
    ),
    Category.UI: (
        "click",
        "type",
        "press",
        "shortcut",
        "keyboard",
        "mouse",
        "clicca",
        "scrivi",
        "scorciatoia",
        "点击",
        "输入",
        "快捷键",
    ),
    Category.FILES: (
        "file",
        "folder",
        "document",
        "move",
        "delete",
        "trash",
        "recycle",
        "cerca",
        "leggi",
        "sposta",
        "elimina",
        "cartella",
        "documento",
        "文件",
        "文件夹",
        "移动",
        "删除",
    ),
    Category.CALC: (
        "calculate",
        "calc",
        "math",
        "sum",
        "multiply",
        "divide",
        "percent",
        "percentage",
        "equation",
        "solve",
        "convert",
        "chart",
        "graph",
        "plot",
        "quanto fa",
        "quanto vale",
        "percentuale",
        "diviso",
        "moltiplicato",
        "somma",
        "differenza",
        "equazione",
        "risolvi",
        "converti",
        "grafico",
        "计算",
        "方程",
        "图表",
    ),
    Category.CODE: (
        "python",
        "script",
        "simulate",
        "simulation",
        "numpy",
        "scipy",
        "run code",
        "esegui",
        "simula",
        "codice",
        "运行",
        "代码",
    ),
    Category.GITHUB: (
        "github",
        "repo",
        "repository",
        "issue",
        "commit",
        "pull request",
        "仓库",
        "提交",
    ),
    Category.GOOGLE: (
        "gmail",
        "mail",
        "email",
        "inbox",
        "calendar",
        "event",
        "meeting",
        "agenda",
        "posta",
        "calendario",
        "evento",
        "邮件",
        "日历",
    ),
    Category.MEMORY: (
        "note",
        "remember",
        "memo",
        "timer",
        "alarm",
        "remind",
        "nota",
        "ricorda",
        "promemoria",
        "sveglia",
        "笔记",
        "提醒",
        "计时器",
    ),
}

META_TOOL = "chiedi_chiarimento"
MAX_TOOLS = 6


@dataclass
class Selection:
    categories: list[Category]
    tools: list[ToolSpec]


def detect_categories(text: str) -> list[Category]:
    lowered = text.lower()
    scores: dict[Category, int] = {}
    for category, words in KEYWORDS.items():
        score = 0
        for word in words:
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", lowered):
                score += 1
        if score:
            scores[category] = score

    if not scores:
        return [Category.SYSTEM, Category.MEMORY]

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0].value))
    return [category for category, _ in ordered[:2]]


def select_tools(text: str, registry: dict[str, ToolSpec], is_enabled) -> Selection:
    """Return the categories and tools relevant to ``text``."""
    categories = detect_categories(text)
    chosen: list[ToolSpec] = []

    for category in categories:
        for spec in registry.values():
            if spec.category is not category:
                continue
            if not is_enabled(spec.name):
                continue
            if spec not in chosen:
                chosen.append(spec)

    meta = registry.get(META_TOOL)
    if meta is not None and meta not in chosen:
        # Keep one slot for clarification so the model can ask instead of guess.
        chosen = chosen[: MAX_TOOLS - 1] + [meta]
    else:
        chosen = chosen[:MAX_TOOLS]

    if not chosen:
        chosen = [spec for spec in registry.values() if spec.category is Category.META][:MAX_TOOLS]

    return Selection(categories=categories, tools=chosen)
