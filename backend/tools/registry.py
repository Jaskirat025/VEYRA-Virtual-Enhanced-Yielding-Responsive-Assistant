"""Tool registry.

A tool is a typed Python function decorated with :func:`tool`. The decorator
builds a JSON schema from type hints and the docstring, and records the
declared category, risk level and tags. The model never sees every tool: the
pre-classifier selects a small, relevant subset.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, get_args, get_origin, get_type_hints


class Risk(StrEnum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"


class Category(StrEnum):
    SYSTEM = "system"
    UI = "ui"
    FILES = "files"
    CALC = "calc"
    CODE = "code"
    GITHUB = "github"
    GOOGLE = "google"
    MEMORY = "memory"
    COMMUNICATION = "communication"
    META = "meta"


class ToolError(Exception):
    """An expected failure whose message is safe for the user and the model."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    category: Category
    risk: Risk
    parameters: dict[str, Any]
    func: Callable[..., Any]
    tags: tuple[str, ...] = ()
    enabled_by_default: bool = True

    def to_llm_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_REGISTRY: dict[str, ToolSpec] = {}
_ARG_LINE = re.compile(r"^\s{0,8}([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$")
_SUPPORTED = (str, int, float, bool)


def _arg_docs(docstring: str) -> dict[str, str]:
    """Extract ``name: description`` lines from an Args section."""
    docs: dict[str, str] = {}
    in_args = False
    for line in (docstring or "").splitlines():
        stripped = line.strip()
        if stripped.lower() in {"args:", "arguments:", "parameters:"}:
            in_args = True
            continue
        if in_args and stripped and not line.startswith((" ", "\t")):
            in_args = False
        if in_args:
            match = _ARG_LINE.match(line)
            if match:
                docs[match.group(1)] = match.group(2).strip()
    return docs


def _schema_for(annotation: Any, description: str) -> dict[str, Any]:
    origin = get_origin(annotation)

    if origin is Literal:
        values = list(get_args(annotation))
        kind = "string" if all(isinstance(value, str) for value in values) else "number"
        return {"type": kind, "enum": values, "description": description}

    if annotation in _SUPPORTED:
        kind = {str: "string", int: "integer", float: "number", bool: "boolean"}[annotation]
        return {"type": kind, "description": description}

    if origin in (list, list):
        (item_type,) = get_args(annotation) or (str,)
        if item_type is not str:
            raise TypeError("Only list[str] parameters are supported")
        return {
            "type": "array",
            "items": {"type": "string"},
            "description": description,
        }

    raise TypeError(f"Unsupported parameter type: {annotation!r}")


def tool(
    category: Category,
    risk: Risk,
    *,
    tags: tuple[str, ...] = (),
    enabled_by_default: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function as a Veyra tool."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if func.__name__ in _REGISTRY:
            raise ValueError(f"Duplicate tool name: {func.__name__}")

        hints = get_type_hints(func)
        signature = inspect.signature(func)
        docs = _arg_docs(func.__doc__ or "")
        properties: dict[str, Any] = {}
        required: list[str] = []

        for name, parameter in signature.parameters.items():
            if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                raise TypeError(f"Tool {func.__name__} may not use *args or **kwargs")
            annotation = hints.get(name, str)
            prop = _schema_for(annotation, docs.get(name, name.replace("_", " ")))
            if parameter.default is not inspect.Parameter.empty:
                prop["default"] = parameter.default
            else:
                required.append(name)
            properties[name] = prop

        description = (func.__doc__ or "").strip()
        if not description:
            raise ValueError(f"Tool {func.__name__} needs a docstring: it is the tool prompt")

        _REGISTRY[func.__name__] = ToolSpec(
            name=func.__name__,
            description=description,
            category=category,
            risk=risk,
            parameters={
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
            func=func,
            tags=tags,
            enabled_by_default=enabled_by_default,
        )
        return func

    return decorator


def get_registry() -> dict[str, ToolSpec]:
    return _REGISTRY


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def clear_registry() -> None:
    """Test helper: forget registered tools."""
    _REGISTRY.clear()


def _coerce(name: str, prop: dict[str, Any], value: Any) -> Any:
    kind = prop.get("type")
    if "enum" in prop:
        if value not in prop["enum"]:
            raise ToolError(
                f"Argument '{name}' must be one of: {', '.join(map(str, prop['enum']))}"
            )
        return value

    if kind == "string":
        if not isinstance(value, str):
            raise ToolError(f"Argument '{name}' must be a string.")
        if len(value) > 4000:
            raise ToolError(f"Argument '{name}' is too long (max 4000 characters).")
        return value

    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ToolError(f"Argument '{name}' must be an integer.")
        return value

    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ToolError(f"Argument '{name}' must be a number.")
        return float(value)

    if kind == "boolean":
        if not isinstance(value, bool):
            raise ToolError(f"Argument '{name}' must be true or false.")
        return value

    if kind == "array":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ToolError(f"Argument '{name}' must be a list of strings.")
        if len(value) > 50:
            raise ToolError(f"Argument '{name}' has too many items (max 50).")
        return value

    raise ToolError(f"Argument '{name}' has an unsupported schema.")


def validate_arguments(spec: ToolSpec, arguments: Any) -> dict[str, Any]:
    """Validate model-provided arguments against the generated schema."""
    if not isinstance(arguments, dict):
        raise ToolError("Arguments must be a JSON object.")

    properties: dict[str, Any] = spec.parameters.get("properties", {})
    required = set(spec.parameters.get("required", []))

    unknown = set(arguments) - set(properties)
    if unknown:
        raise ToolError(f"Unknown argument(s): {', '.join(sorted(unknown))}.")

    missing = required - set(arguments)
    if missing:
        raise ToolError(f"Missing argument(s): {', '.join(sorted(missing))}.")

    return {name: _coerce(name, properties[name], value) for name, value in arguments.items()}


def _load_builtin_tools() -> None:
    from backend.tools import builtin  # noqa: F401  (import side effect: registration)


def ensure_tools_loaded() -> dict[str, ToolSpec]:
    """Import the built-in tool modules once and return the registry."""
    if not _REGISTRY:
        _load_builtin_tools()
    return _REGISTRY
