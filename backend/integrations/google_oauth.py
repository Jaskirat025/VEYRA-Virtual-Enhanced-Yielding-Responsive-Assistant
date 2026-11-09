"""Google OAuth for Gmail and Calendar.

Each user creates a Desktop OAuth client in their own Google Cloud project and
pastes the client configuration into Settings. The client secret and the
refresh token are stored in Windows Credential Manager; a temporary file is
used only for the duration of the flow.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.secrets import get_secret, set_secret

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


def save_client_config(config: dict) -> None:
    if not isinstance(config, dict):
        raise GoogleAuthError("The client configuration must be a JSON object.")
    installed = config.get("installed") or config.get("web")
    if not isinstance(installed, dict) or not installed.get("client_id"):
        raise GoogleAuthError("This is not a Google OAuth client file.")
    if installed.get("client_id", "").endswith(".apps.googleusercontent.com") is False:
        raise GoogleAuthError("The client id looks invalid.")
    set_secret("google_client_json", json.dumps(config))


def connect(allow_write: bool = False) -> str:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise GoogleAuthError("Google support is not installed.") from exc

    raw = get_secret("google_client_json")
    if not raw:
        raise GoogleAuthError("Import your Google OAuth client first.")

    scopes = READ_SCOPES + (WRITE_SCOPES if allow_write else [])
    with tempfile.TemporaryDirectory(prefix="veyra-google-") as folder:
        client_file = Path(folder) / "client.json"
        client_file.write_text(raw, encoding="utf-8")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes)
        credentials = flow.run_local_server(port=0, open_browser=True)

    set_secret("google_token_json", credentials.to_json())
    return "Google account connected."
