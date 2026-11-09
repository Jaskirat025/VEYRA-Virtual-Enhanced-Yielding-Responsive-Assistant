#!/usr/bin/env python3
"""Repository hygiene gate for VEYRA.

Fails when the repository contains credentials, personal data, or artefacts
that must stay on the developer machine (environment files, databases, model
weights, logs, private keys).

Two independent passes:

1. Tracked artefacts: ``git ls-files`` must not include sensitive files.
2. Working tree: every project text file (tracked, staged or untracked but not
   ignored) is scanned for credential shapes, personal e-mail addresses and
   hard-coded user directories. Ignored directories such as dependency caches
   and build output are never read.

``.env`` and ``.env.example`` are skipped in the content pass: the example file
intentionally contains obvious placeholders, and any real ``.env`` is already
blocked by the tracked-artefact pass and by ``.gitignore``.

Run before every commit:

    python scripts/check_hygiene.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

# Large enough for documents, small enough to keep the check fast.
MAX_FILE_BYTES = 512 * 1024

# Generated, vendored or disposable directories.
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    ".cargo",
    ".rustup",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    "target",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "models",
    "voices",
}

FORBIDDEN_TRACKED_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "credentials.json",
    "client_secret.json",
    "secrets.json",
    "token.json",
}

FORBIDDEN_TRACKED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-journal",
    ".gguf",
    ".onnx",
    ".pt",
    ".pth",
    ".safetensors",
    ".log",
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}

# Each entry is (human label, compiled pattern). Keep the false-positive rate
# low: a match must look like real data, not like documentation.
PATTERNS = (
    (
        "Windows user directory",
        re.compile(r"[A-Za-z]:\\(?:Users|Documents and Settings)\\"),
    ),
    (
        "home directory path",
        re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+"),
    ),
    (
        "e-mail address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "OpenAI-style API key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    ),
    (
        "Google API key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    ),
    (
        "GitHub token",
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    ),
    (
        "GitHub fine-grained token",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    ),
    (
        "AWS access key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
    (
        "Slack token",
        re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    ),
    (
        "JSON Web Token",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ),
    (
        "private key block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
)


def _display_excerpt(value: str) -> str:
    """Return a short, redacted excerpt so CI logs do not reproduce a secret."""
    cleaned = " ".join(value.split())
    if len(cleaned) <= 12:
        return cleaned
    return f"{cleaned[:12]}..."


def check_tracked_artefacts(failures: list[str]) -> None:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        print("hygiene: git is unavailable; skipping the tracked-artefact pass")
        return

    if completed.returncode != 0:
        print("hygiene: not a git repository; skipping the tracked-artefact pass")
        return

    for raw_name in completed.stdout.decode("utf-8", errors="replace").split("\0"):
        if not raw_name:
            continue
        path = Path(raw_name)
        if path.name.lower() in FORBIDDEN_TRACKED_NAMES:
            failures.append(f"tracked sensitive artefact: {raw_name}")
        elif path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
            failures.append(f"tracked sensitive artefact: {raw_name}")


def git_project_files() -> list[str] | None:
    """Return tracked, staged and untracked-not-ignored paths, or None."""
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if completed.returncode != 0:
        return None
    return [name for name in completed.stdout.decode("utf-8", errors="replace").split("\0") if name]


def iter_text_files():
    """Yield (relative path, text) for every readable, non-binary project file."""
    project_files = git_project_files()
    if project_files is None:
        candidates = sorted(ROOT.rglob("*"))
    else:
        candidates = [ROOT / name for name in project_files]

    for path in candidates:
        try:
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
        except (OSError, ValueError):
            continue

        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.resolve() == SELF:
            continue
        if path.name.lower().startswith(".env"):
            continue

        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue

        if b"\x00" in raw[:4096]:
            continue

        yield relative.as_posix(), raw.decode("utf-8", errors="replace")


def check_content(failures: list[str]) -> int:
    scanned = 0
    for relative, text in iter_text_files():
        scanned += 1
        for label, pattern in PATTERNS:
            for match in pattern.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                failures.append(
                    f"{relative}:{line_number}: {label} ({_display_excerpt(match.group(0))})"
                )
    return scanned


def main() -> int:
    failures: list[str] = []

    check_tracked_artefacts(failures)
    scanned = check_content(failures)

    if failures:
        print("VEYRA hygiene check FAILED\n")
        for failure in failures:
            print(f"  - {failure}")
        print(
            f"\n{len(failures)} finding(s). Remove the data instead of allowlisting it; "
            "only documented placeholders may stay."
        )
        return 1

    print(
        f"VEYRA hygiene check passed: {scanned} text files scanned. "
        "No secrets, personal data or sensitive tracked artefacts."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
