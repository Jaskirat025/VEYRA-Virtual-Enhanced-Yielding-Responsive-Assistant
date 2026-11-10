"""First-run downloads for the local model and the speech model.

The two assets are independent, so they start at the same time. Progress is
kept in memory and polled by the interface. A failed job can be retried
without restarting the other one.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from backend.brain.llm import fetch_ollama_models, ollama_url
from backend.config import AppSettings, SettingsStore
from backend.paths import models_dir

logger = logging.getLogger(__name__)

Runner = Callable[["DownloadJob", AppSettings], Awaitable[None]]


@dataclass
class DownloadJob:
    id: str
    label: str
    status: str = "pending"
    progress: float | None = None
    detail: str = ""
    downloaded: int = 0
    total: int = 0
    error: str = ""
    started_at: float | None = None
    finished_at: float | None = None
    task: asyncio.Task[None] | None = field(default=None, repr=False, compare=False)

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "progress": self.progress,
            "detail": self.detail,
            "downloaded": self.downloaded,
            "total": self.total,
            "error": self.error,
        }


def _stt_marker(settings: AppSettings) -> Path:
    model = re.sub(r"[^A-Za-z0-9_.-]+", "-", settings.audio.stt_model).strip("-") or "model"
    compute = re.sub(r"[^A-Za-z0-9_.-]+", "-", settings.audio.stt_compute_type).strip("-")
    return models_dir() / f".stt-{model}-{compute or 'default'}.ready"


async def download_local_model(job: DownloadJob, settings: AppSettings) -> None:
    """Pull the configured Ollama model, reporting byte progress when available."""
    model = settings.models.local_model
    base_url = ollama_url()
    try:
        installed = await fetch_ollama_models(base_url, timeout=2.5)
    except Exception as exc:
        raise RuntimeError(
            "The local model runtime did not start. Restart VEYRA and try again."
        ) from exc

    if model in installed:
        job.status = "skipped"
        job.progress = 1.0
        job.detail = "Already installed."
        return

    job.detail = "Contacting Ollama"
    timeout = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)
    try:
        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream(
                "POST",
                f"{base_url}/api/pull",
                json={"name": model, "stream": True},
            ) as response,
        ):
            if response.status_code >= 400:
                detail = (await response.aread()).decode("utf-8", "replace")[:300]
                raise RuntimeError(
                    f"Ollama returned {response.status_code}: {detail or 'no detail'}"
                )
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                error = event.get("error")
                if error:
                    raise RuntimeError(f"Ollama: {str(error)[:300]}")
                status = str(event.get("status") or "").strip()
                if status:
                    job.detail = status
                total = event.get("total")
                completed = event.get("completed")
                if isinstance(total, (int, float)) and total > 0:
                    job.total = int(total)
                    job.downloaded = int(completed or 0)
                    job.progress = min(0.99, max(0.0, job.downloaded / job.total))
                if status == "success":
                    job.progress = 1.0
    except httpx.HTTPError as exc:
        raise RuntimeError(
            "The model download was interrupted. Check the connection and try again."
        ) from exc

    job.status = "done"
    job.progress = 1.0
    job.detail = f"{model} is ready."


async def download_speech_model(job: DownloadJob, settings: AppSettings) -> None:
    """Download the faster-whisper model into the Veyra data folder."""
    marker = _stt_marker(settings)
    if marker.is_file():
        job.status = "skipped"
        job.progress = 1.0
        job.detail = "Already installed."
        return

    download_root = models_dir() / "whisper"
    download_root.mkdir(parents=True, exist_ok=True)
    job.detail = "Downloading the speech model"

    def work() -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "Speech support is not installed. Install the Windows requirements."
            ) from exc
        WhisperModel(
            settings.audio.stt_model,
            device="cpu",
            compute_type=settings.audio.stt_compute_type,
            download_root=str(download_root),
        )

    try:
        await asyncio.to_thread(work)
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Could not download the speech model: {exc}") from exc

    marker.write_text("ok\n", encoding="utf-8")
    job.status = "done"
    job.progress = 1.0
    job.detail = "Speech model is ready."


class BootstrapManager:
    """Run the first-run downloads concurrently and expose their state."""

    def __init__(
        self,
        settings_store: SettingsStore,
        runners: dict[str, Runner] | None = None,
    ) -> None:
        self._settings_store = settings_store
        self._jobs = [
            DownloadJob("local_model", "Local model"),
            DownloadJob("speech_model", "Speech recognition"),
        ]
        self._runners = runners or {
            "local_model": download_local_model,
            "speech_model": download_speech_model,
        }
        self._lock = asyncio.Lock()

    def snapshot(self) -> dict[str, Any]:
        jobs = [job.public() for job in self._jobs]
        return {
            "running": any(job["status"] == "running" for job in jobs),
            "complete": all(job["status"] in {"done", "skipped"} for job in jobs),
            "failed": any(job["status"] == "error" for job in jobs),
            "jobs": jobs,
        }

    async def start(self) -> dict[str, Any]:
        """Start pending and failed jobs; completed jobs are left alone."""
        async with self._lock:
            settings = self._settings_store.load()
            for job in self._jobs:
                if job.status == "running" or job.status in {"done", "skipped"}:
                    continue
                job.status = "running"
                job.progress = None
                job.detail = "Starting"
                job.downloaded = 0
                job.total = 0
                job.error = ""
                job.started_at = time.time()
                job.finished_at = None
                job.task = asyncio.create_task(self._execute(job, settings))
        return self.snapshot()

    async def _execute(self, job: DownloadJob, settings: AppSettings) -> None:
        try:
            runner = self._runners[job.id]
            await runner(job, settings)
            if job.status == "running":
                job.status = "done"
                job.progress = 1.0
        except asyncio.CancelledError:
            job.status = "error"
            job.error = "Cancelled."
            job.detail = "Cancelled."
            raise
        except Exception as exc:
            logger.warning("First-run download %s failed: %s", job.id, exc)
            message = str(exc)[:500] or "Download failed."
            job.status = "error"
            job.error = message
            job.detail = message
        finally:
            job.finished_at = time.time()
