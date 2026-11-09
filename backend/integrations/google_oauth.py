"""Google OAuth for Gmail and Calendar.

The OAuth client belongs to the VEYRA build, not to each user. Release builds
embed a Desktop client configuration generated from repository secrets; local
development can supply the same values through environment variables. User
tokens stay in the OS credential store.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.secrets import get_secret, set_secret

CLIENT_FILE = Path(__file__).resolve().parents[1] / "google_client.json"
CLIENT_ID_ENV = "VEYRA_GOOGLE_CLIENT_ID"
CLIENT_SECRET_ENV = "VEYRA_GOOGLE_CLIENT_SECRET"

READ_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]
WRITE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleAuthError(Exception):
    """A user-actionable OAuth failure."""


def _installed_config(client_id: str, client_secret: str) -> dict[str, Any]:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["http://localhost"],
        }
    }


def _validate_client_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise GoogleAuthError("The Google client configuration must be a JSON object.")
    installed = config.get("installed") or config.get("web")
    if not isinstance(installed, dict):
        raise GoogleAuthError("This is not a Google OAuth client configuration.")
    client_id = installed.get("client_id")
    client_secret = installed.get("client_secret")
    if not isinstance(client_id, str) or not client_id.endswith(".apps.googleusercontent.com"):
        raise GoogleAuthError("The Google OAuth client id is invalid.")
    if not isinstance(client_secret, str) or not client_secret.strip():
        raise GoogleAuthError("The Google OAuth client secret is missing.")
    return config


def _config_from_env() -> dict[str, Any] | None:
    client_id = os.environ.get(CLIENT_ID_ENV, "").strip()
    client_secret = os.environ.get(CLIENT_SECRET_ENV, "").strip()
    if not client_id and not client_secret:
        return None
    if not client_id or not client_secret:
        raise GoogleAuthError(f"Set both {CLIENT_ID_ENV} and {CLIENT_SECRET_ENV}, or neither.")
    return _validate_client_config(_installed_config(client_id, client_secret))


def builtin_client_config() -> dict[str, Any] | None:
    """Return the project-owned client embedded in this build, if available."""
    from_env = _config_from_env()
    if from_env is not None:
        return from_env
    if not CLIENT_FILE.exists():
        return None
    try:
        raw = json.loads(CLIENT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GoogleAuthError("The bundled Google client configuration is invalid.") from exc
    return _validate_client_config(raw)


def client_configured() -> bool:
    """Report whether this build can start a Google sign-in flow."""
    try:
        if builtin_client_config() is not None:
            return True
    except GoogleAuthError:
        return False
    return bool(get_secret("google_client_json"))


def save_client_config(config: dict) -> None:
    """Store an advanced/development client configuration as a fallback."""
    validated = _validate_client_config(config)
    set_secret("google_client_json", json.dumps(validated))


def connect(allow_write: bool = False) -> str:
    config = builtin_client_config()
    if config is None:
        raw = get_secret("google_client_json")
        if not raw:
            raise GoogleAuthError("Google sign-in is not configured in this build.")
        try:
            config = _validate_client_config(json.loads(raw))
        except (ValueError, TypeError, GoogleAuthError) as exc:
            raise GoogleAuthError("The stored Google client configuration is invalid.") from exc

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GoogleAuthError("Google support is not installed.") from exc

    scopes = READ_SCOPES + (WRITE_SCOPES if allow_write else [])
    flow = InstalledAppFlow.from_client_config(config, scopes)
    credentials = flow.run_local_server(
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )
    set_secret("google_token_json", credentials.to_json())
    return "Google account connected."
