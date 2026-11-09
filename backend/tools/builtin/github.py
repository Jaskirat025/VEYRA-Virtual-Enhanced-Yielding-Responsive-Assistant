"""GitHub tools using the user's personal token."""

from __future__ import annotations

import re

import httpx

from backend.context import get_context
from backend.secrets import get_secret
from backend.tools.external import wrap_external
from backend.tools.registry import Category, Risk, ToolError, tool

API = "https://api.github.com"
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _token() -> str:
    token = get_secret("github_token")
    if not token:
        raise ToolError("GitHub is not connected. Add a personal token in Settings > Accounts.")
    return token


def _request(method: str, path: str, **kwargs) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Veyra",
        "Authorization": f"Bearer {_token()}",
    }
    try:
        with httpx.Client(timeout=20, headers=headers) as client:
            response = client.request(method, f"{API}{path}", **kwargs)
    except httpx.HTTPError as exc:
        raise ToolError("GitHub is unreachable. Check the connection.") from exc

    if response.status_code == 401:
        raise ToolError("GitHub rejected the token. Replace it in Settings.")
    if response.status_code == 403:
        raise ToolError("GitHub denied the request (rate limit or missing scope).")
    if response.status_code == 404:
        raise ToolError("GitHub resource not found.")
    if response.status_code >= 400:
        raise ToolError(f"GitHub returned error {response.status_code}.")
    try:
        return response.json()
    except ValueError as exc:
        raise ToolError("GitHub returned an invalid response.") from exc


def _repository(value: str) -> str:
    repo = value.strip()
    if not REPO_PATTERN.match(repo):
        raise ToolError("Repository must look like 'owner/name'.")
    return repo


def _require_write() -> None:
    settings = get_context().settings
    if settings.integrations.github_read_only:
        raise ToolError("GitHub is in read-only mode. Enable writing in Settings > Accounts.")


@tool(category=Category.GITHUB, risk=Risk.SAFE, tags=("external",))
def lista_repo(limite: int = 10) -> str:
    """List the repositories of the connected GitHub account.

    Use when the user asks which repositories exist.

    Args:
        limite: number of repositories, 1-50.
    """
    count = max(1, min(50, int(limite)))
    data = _request("GET", "/user/repos", params={"per_page": count, "sort": "updated"})
    if not isinstance(data, list) or not data:
        return "No repositories found."
    lines = [
        f"{repo.get('full_name')} ({'private' if repo.get('private') else 'public'}, "
        f"updated {str(repo.get('updated_at', ''))[:10]})"
        for repo in data
    ]
    return wrap_external("github", "\n".join(lines))


@tool(category=Category.GITHUB, risk=Risk.SAFE, tags=("external",))
def leggi_issue(repository: str, numero: int) -> str:
    """Read a GitHub issue or pull request.

    Use when the user asks about a specific issue by number.

    Args:
        repository: repository in the form "owner/name".
        numero: issue or pull request number.
    """
    repo = _repository(repository)
    data = _request("GET", f"/repos/{repo}/issues/{int(numero)}")
    if not isinstance(data, dict):
        raise ToolError("Unexpected GitHub response.")
    body = (data.get("body") or "")[:2000]
    content = (
        f"#{data.get('number')} {data.get('title')}\n"
        f"state: {data.get('state')} | author: {(data.get('user') or {}).get('login')}\n"
        f"{body}"
    )
    return wrap_external(f"github:{repo}", content)


@tool(category=Category.GITHUB, risk=Risk.SAFE, tags=("external",))
def ultimi_commit(repository: str, limite: int = 5) -> str:
    """List the latest commits of a repository.

    Use when the user asks what changed recently in a project.

    Args:
        repository: repository in the form "owner/name".
        limite: number of commits, 1-20.
    """
    repo = _repository(repository)
    count = max(1, min(20, int(limite)))
    data = _request("GET", f"/repos/{repo}/commits", params={"per_page": count})
    if not isinstance(data, list) or not data:
        return "No commits found."
    lines = []
    for item in data:
        commit = item.get("commit") or {}
        message = str(commit.get("message", "")).splitlines()[0][:120]
        author = (commit.get("author") or {}).get("name", "")
        lines.append(f"{item.get('sha', '')[:7]} {message} ({author})")
    return wrap_external(f"github:{repo}", "\n".join(lines))


@tool(category=Category.GITHUB, risk=Risk.CONFIRM)
def crea_issue(repository: str, titolo: str, corpo: str = "") -> str:
    """Create a GitHub issue.

    Use only when the user explicitly asks to open an issue. Creating an issue
    is public for public repositories, so confirmation is required.

    Args:
        repository: repository in the form "owner/name".
        titolo: issue title.
        corpo: optional issue body.
    """
    _require_write()
    repo = _repository(repository)
    title = titolo.strip()
    if not title:
        raise ToolError("The issue title is empty.")
    data = _request(
        "POST",
        f"/repos/{repo}/issues",
        json={"title": title[:200], "body": corpo[:10_000]},
    )
    if not isinstance(data, dict):
        raise ToolError("Unexpected GitHub response.")
    return f"Opened issue #{data.get('number')}: {data.get('html_url')}"
