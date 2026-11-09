"""Veyra backend entry point.

The Tauri shell starts this process, reads one JSON handshake line from
stdout (port and session token) and connects the interface to it. The server
binds to 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import json
import logging
import secrets
import socket
import sys

from backend.api.app import create_app
from backend.config import SettingsStore
from backend.context import RuntimeContext, set_context
from backend.logging_setup import configure_logging
from backend.memory.db import Database
from backend.paths import app_data_dir, db_path

logger = logging.getLogger(__name__)


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="veyra-backend", description="Veyra local backend")
    parser.add_argument("--port", type=int, default=0, help="port to bind; 0 picks a free one")
    parser.add_argument("--token", default="", help="session token; generated when omitted")
    parser.add_argument("--host", default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--handshake",
        action="store_true",
        help="print the JSON handshake line on stdout (used by the desktop shell)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.log_level, console=not args.handshake)

    if args.host != "127.0.0.1":
        print("Veyra refuses to bind outside 127.0.0.1.", file=sys.stderr)
        return 2

    token = args.token or secrets.token_urlsafe(32)
    port = args.port or pick_free_port()

    settings_store = SettingsStore()
    settings = settings_store.load()
    db = Database(db_path())
    set_context(RuntimeContext(settings=settings, db=db))

    app = create_app(settings_store, db, token)

    if args.handshake:
        print(
            json.dumps(
                {
                    "type": "veyra-ready",
                    "port": port,
                    "token": token,
                    "version": "0.1.0",
                    "data_dir": str(app_data_dir()),
                }
            ),
            flush=True,
        )

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=port, log_config=None, access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
