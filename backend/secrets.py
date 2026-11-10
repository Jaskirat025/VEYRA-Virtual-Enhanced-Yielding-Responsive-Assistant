"""Secret storage.

Real credentials are kept in Windows Credential Manager through ``keyring``.
If keyring is unavailable (Linux development container, tests), an in-memory
store is used and a warning is logged. Secrets are never written to disk and
are never returned by the HTTP API.
"""

from __future__ import annotations

import contextlib
import logging
import os

logger = logging.getLogger(__name__)

SERVICE_NAME = "Veyra"

_ENV_FALLBACK = {
    "online_api_key": "VEYRA_ONLINE_API_KEY",
    "github_token": "VEYRA_GITHUB_TOKEN",
}

_memory_store: dict[str, str] = {}
_keyring_available: bool | None = None


def _keyring():
    """Return the keyring module, or None when it cannot be used."""
    global _keyring_available
    if _keyring_available is False:
        return None
    try:
        import keyring

        _keyring_available = True
        return keyring
    except Exception:  # pragma: no cover - depends on the host
        _keyring_available = False
        logger.warning("keyring unavailable; using an in-memory secret store for this session")
        return None


def set_secret(name: str, value: str) -> None:
    if not value:
        delete_secret(name)
        return

    backend = _keyring()
    if backend is not None:
        try:
            backend.set_password(SERVICE_NAME, name, value)
            return
        except Exception as exc:  # pragma: no cover - depends on the host
            logger.warning("keyring write failed (%s); keeping the value in memory", exc)
    _memory_store[name] = value


def get_secret(name: str) -> str | None:
    env_name = _ENV_FALLBACK.get(name)
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]

    backend = _keyring()
    if backend is not None:
        try:
            value = backend.get_password(SERVICE_NAME, name)
            if value:
                return value
        except Exception:  # pragma: no cover - depends on the host
            pass
    return _memory_store.get(name)


def delete_secret(name: str) -> None:
    _memory_store.pop(name, None)
    backend = _keyring()
    if backend is None:
        return
    # Deleting a missing entry raises on some backends; that is fine.
    with contextlib.suppress(Exception):
        backend.delete_password(SERVICE_NAME, name)


def secret_status(names) -> dict[str, bool]:
    """Report which secrets exist without revealing their values."""
    return {name: bool(get_secret(name)) for name in names}


def clear_memory_store() -> None:
    """Test helper: drop values held in the in-memory fallback."""
    _memory_store.clear()
