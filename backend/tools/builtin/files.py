"""File tools. Deletion prefers the Recycle Bin and never deletes permanently."""

from __future__ import annotations

import os
from pathlib import Path

from backend.tools.external import wrap_external
from backend.tools.registry import Category, Risk, ToolError, tool

SKIPPED_DIRS = {
    "AppData",
    "Application Data",
    "Local Settings",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
}
MAX_SEARCH_RESULTS = 20
MAX_VISITED = 20_000


def _home() -> Path:
    return Path.home().resolve()


def _user_path(raw: str, *, must_exist: bool = True) -> Path:
    text = raw.strip().strip('"')
    if not text:
        raise ToolError("The path is empty.")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = _home() / path
    try:
        path = path.resolve(strict=False)
    except OSError as exc:
        raise ToolError(f"Invalid path: {exc}") from exc

    if not str(path).startswith(str(_home())):
        raise ToolError("Access outside the user folder is not allowed.")
    if must_exist and not path.exists():
        raise ToolError(f"Path not found: {path.name}")
    return path


@tool(category=Category.FILES, risk=Risk.SAFE)
def cerca_file(query: str, cartella: str = "") -> str:
    """Search the user folder for files whose name contains a query.

    Use when the user asks where a file is. Results are capped at 20.

    Args:
        query: part of the file name, at least two characters.
        cartella: optional folder to search in, relative to the user folder.
    """
    needle = query.strip().lower()
    if len(needle) < 2:
        raise ToolError("Use at least two characters for the search.")
    root = _user_path(cartella) if cartella.strip() else _home()
    if not root.is_dir():
        raise ToolError("The search folder is not a directory.")

    matches: list[str] = []
    for visited, (current, dirs, files) in enumerate(os.walk(root)):
        dirs[:] = [name for name in dirs if name not in SKIPPED_DIRS and not name.startswith(".")]
        if visited > MAX_VISITED:
            break
        for name in files:
            if needle in name.lower():
                matches.append(str(Path(current) / name))
                if len(matches) >= MAX_SEARCH_RESULTS:
                    break
        if len(matches) >= MAX_SEARCH_RESULTS:
            break

    if not matches:
        return f"No files matching '{query}'."
    return "\n".join(matches)


@tool(category=Category.FILES, risk=Risk.SAFE, tags=("external",))
def leggi_file(percorso: str, max_caratteri: int = 4000) -> str:
    """Read a text file from the user folder.

    Use when the user asks to open or summarise a document. Binary files are
    rejected.

    Args:
        percorso: file path, absolute or relative to the user folder.
        max_caratteri: maximum characters to return, 100-20000.
    """
    path = _user_path(percorso)
    if not path.is_file():
        raise ToolError("The path is not a file.")
    limit = max(100, min(20_000, int(max_caratteri)))
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ToolError(f"Could not read the file: {exc}") from exc
    if b"\x00" in raw[:4096]:
        raise ToolError("This looks like a binary file and will not be read.")

    text = raw.decode("utf-8", errors="replace")
    if len(text) > limit:
        text = text[:limit] + "\n...[truncated]"
    return wrap_external("file:" + path.name, text)


@tool(category=Category.FILES, risk=Risk.CONFIRM)
def sposta_file(sorgente: str, destinazione: str) -> str:
    """Move or rename a file or folder inside the user folder.

    Use when the user asks to move or rename something. Existing destinations
    are never overwritten.

    Args:
        sorgente: current path.
        destinazione: target path or target folder.
    """
    import shutil

    source = _user_path(sorgente)
    target = _user_path(destinazione, must_exist=False)
    if target.is_dir():
        target = target / source.name
    if target.exists():
        raise ToolError("The destination already exists; nothing was moved.")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    except OSError as exc:
        raise ToolError(f"Move failed: {exc}") from exc
    return f"Moved {source.name} to {target.parent}."


@tool(category=Category.FILES, risk=Risk.DANGEROUS)
def elimina_file(percorso: str) -> str:
    """Send a file or folder to the Recycle Bin.

    Use only when the user explicitly asks to delete something. The item is
    moved to the Recycle Bin, never deleted permanently.

    Args:
        percorso: path to remove.
    """
    path = _user_path(percorso)
    try:
        from send2trash import send2trash
    except ImportError as exc:
        raise ToolError("Recycle Bin support is unavailable, so nothing was deleted.") from exc
    try:
        send2trash(str(path))
    except Exception as exc:
        raise ToolError(f"Could not move the item to the Recycle Bin: {exc}") from exc
    return f"Sent {path.name} to the Recycle Bin."
