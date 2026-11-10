"""FastAPI application: HTTP endpoints, token auth and the WebSocket route."""

from __future__ import annotations

import asyncio
import logging
import re
import secrets as py_secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend import __version__
from backend.api.ws import Session
from backend.audio.stt import available as stt_available
from backend.audio.tts import SpeechUnavailable, synthesize
from backend.bootstrap import BootstrapManager
from backend.brain.agent import ConfirmBroker
from backend.brain.llm import LLMError, fetch_ollama_models
from backend.config import AppSettings, SettingsStore
from backend.memory.db import Database
from backend.paths import app_data_dir
from backend.secrets import delete_secret, get_secret, secret_status, set_secret
from backend.tools.registry import ensure_tools_loaded

logger = logging.getLogger(__name__)

SECRET_NAMES = (
    "online_api_key",
    "github_token",
)
CUSTOM_API_SECRET_PREFIX = "custom_api_"
_CUSTOM_API_ID = re.compile(r"[a-z][a-z0-9_-]{1,31}")
DEV_ORIGINS = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]


class SettingsPatch(BaseModel):
    patch: dict[str, Any]


class SecretPayload(BaseModel):
    name: str
    value: str


class KVPayload(BaseModel):
    value: str


KV_KEYS = {"onboarded", "last_conversation_id"}


def _token_from_request(request: Request) -> str:
    header = request.headers.get("x-veyra-token", "")
    if header:
        return header
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:]
    return ""


def _check_token(expected: str, provided: str) -> bool:
    return bool(provided) and py_secrets.compare_digest(expected, provided)


def _allowed_secret_name(name: str) -> bool:
    if name in SECRET_NAMES:
        return True
    if not name.startswith(CUSTOM_API_SECRET_PREFIX):
        return False
    return bool(_CUSTOM_API_ID.fullmatch(name[len(CUSTOM_API_SECRET_PREFIX) :]))


def create_app(
    settings_store: SettingsStore,
    db: Database,
    token: str,
    broker: ConfirmBroker | None = None,
    bootstrap: BootstrapManager | None = None,
) -> FastAPI:
    settings_store.load()
    app = FastAPI(title="Veyra", version=__version__, docs_url=None, redoc_url=None)
    app.state.settings_store = settings_store
    app.state.db = db
    app.state.token = token
    app.state.broker = broker or ConfirmBroker()
    app.state.bootstrap = bootstrap or BootstrapManager(settings_store)
    ensure_tools_loaded()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=DEV_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["content-type", "x-veyra-token", "authorization"],
    )

    @app.middleware("http")
    async def require_token(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        provided = _token_from_request(request)
        if not _check_token(token, provided):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        current = settings_store.load()
        ram_mb = 0
        try:
            import psutil

            ram_mb = int(psutil.virtual_memory().used / 1024 / 1024)
        except Exception:
            pass
        return {
            "status": "ok",
            "version": __version__,
            "model": current.models.local_model,
            "online_enabled": current.models.online_enabled,
            "ram_mb": ram_mb,
            "data_dir": str(app_data_dir()),
        }

    @app.get("/api/kv/{key}")
    async def read_kv(key: str) -> dict[str, Any]:
        if key not in KV_KEYS:
            raise HTTPException(status_code=400, detail="unknown key")
        return {"key": key, "value": db.get_value(key)}

    @app.put("/api/kv/{key}")
    async def write_kv(key: str, payload: KVPayload) -> dict[str, Any]:
        if key not in KV_KEYS:
            raise HTTPException(status_code=400, detail="unknown key")
        db.set_value(key, payload.value[:2000])
        return {"key": key, "value": payload.value[:2000]}

    @app.get("/api/settings")
    async def read_settings() -> dict[str, Any]:
        return {"settings": settings_store.load().model_dump()}

    @app.put("/api/settings")
    async def write_settings(payload: SettingsPatch) -> dict[str, Any]:
        if not isinstance(payload.patch, dict):
            raise HTTPException(status_code=400, detail="patch must be an object")
        try:
            updated = settings_store.update(payload.patch)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        logger.info("Settings updated")
        return {"settings": updated.model_dump()}

    @app.get("/api/secrets/status")
    async def secret_state() -> dict[str, Any]:
        return {"status": secret_status(SECRET_NAMES)}

    @app.post("/api/secrets")
    async def write_secret(payload: SecretPayload) -> dict[str, Any]:
        if not _allowed_secret_name(payload.name):
            raise HTTPException(status_code=400, detail="unknown secret name")
        value = payload.value.strip()
        set_secret(payload.name, value)
        return {"saved": True, "status": secret_status(SECRET_NAMES)}

    @app.delete("/api/secrets/{name}")
    async def remove_secret(name: str) -> dict[str, Any]:
        if not _allowed_secret_name(name):
            raise HTTPException(status_code=400, detail="unknown secret name")
        delete_secret(name)
        return {"deleted": True, "status": secret_status(SECRET_NAMES)}

    @app.get("/api/tools")
    async def list_tools() -> dict[str, Any]:
        current = settings_store.load()
        registry = ensure_tools_loaded()
        tools = [
            {
                "name": spec.name,
                "category": spec.category.value,
                "risk": spec.risk.value,
                "description": spec.description.splitlines()[0],
                "enabled": current.tool_enabled(spec.name),
                "tags": list(spec.tags),
            }
            for spec in registry.values()
        ]
        tools.sort(key=lambda item: (item["category"], item["name"]))
        return {"tools": tools}

    @app.get("/api/tools/log")
    async def tool_log(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
        return {"entries": db.tool_log(limit)}

    @app.get("/api/messages")
    async def messages(conversation_id: str, limit: int = Query(default=200, ge=1, le=500)):
        return {"messages": db.messages(conversation_id, limit)}

    @app.get("/api/conversations")
    async def conversations():
        return {"conversations": db.conversations()}

    @app.get("/api/ollama/models")
    async def ollama_models() -> dict[str, Any]:
        try:
            models = await fetch_ollama_models("http://127.0.0.1:11434")
        except Exception as exc:
            return {"ok": False, "models": [], "error": f"Ollama is not reachable: {exc}"}
        return {"ok": True, "models": models}

    @app.get("/api/bootstrap/status")
    async def bootstrap_status() -> dict[str, Any]:
        return app.state.bootstrap.snapshot()

    @app.post("/api/bootstrap/start")
    async def bootstrap_start() -> dict[str, Any]:
        return await app.state.bootstrap.start()

    @app.get("/api/onboarding/check")
    async def onboarding_check() -> dict[str, Any]:
        try:
            models = await fetch_ollama_models("http://127.0.0.1:11434")
            ollama = {"ok": True, "models": models}
        except Exception as exc:
            ollama = {"ok": False, "models": [], "error": str(exc)}
        return {
            "ollama": ollama,
            "speech": stt_available(),
            "data_dir": str(app_data_dir()),
        }

    @app.get("/api/tts")
    async def tts(text: str = Query(default="", max_length=1200)) -> Response:
        current = settings_store.load()
        try:
            audio = await asyncio.to_thread(synthesize, text, current.voice)
        except SpeechUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return Response(content=audio, media_type="audio/wav")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        provided = websocket.query_params.get("token", "")
        origin = websocket.headers.get("origin", "")
        if not _check_token(token, provided):
            await websocket.close(code=4401)
            return
        if origin and not any(origin.startswith(allowed) for allowed in DEV_ORIGINS):
            await websocket.close(code=4403)
            return
        session = Session(websocket, settings_store, db, app.state.broker)
        await session.run()

    return app


async def provider_ping(settings: AppSettings) -> bool:
    """Used by tests and the status bar to check the local model."""
    try:
        await fetch_ollama_models("http://127.0.0.1:11434", timeout=1.5)
        return True
    except (LLMError, Exception):
        return False


__all__ = ["create_app", "get_secret"]
