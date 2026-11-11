"""WebSocket session: one live connection between the UI and the agent."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from backend.audio import stt, wake
from backend.audio.recorder import AudioUnavailable
from backend.audio.voice import listen_once
from backend.brain.agent import Agent, ConfirmBroker
from backend.brain.llm import LLMError
from backend.config import SettingsStore
from backend.memory.db import Database

logger = logging.getLogger(__name__)

REMINDER_PREFIX = {"en": "Reminder: ", "it": "Promemoria: ", "zh": "提醒："}


class Session:
    def __init__(
        self,
        websocket: WebSocket,
        settings_store: SettingsStore,
        db: Database,
        broker: ConfirmBroker,
    ) -> None:
        self.websocket = websocket
        self.settings_store = settings_store
        self.db = db
        self.broker = broker
        self._send_lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._wake_task: asyncio.Task | None = None
        self._wake_stop: threading.Event | None = None
        self._proactive_job: asyncio.Task | None = None
        self._last_activity = 0.0
        self._closing = False
        self.conversation_id: str = ""

    async def emit(self, event: dict[str, Any]) -> None:
        async with self._send_lock:
            # The window can close at any moment; a failed send is expected.
            with contextlib.suppress(Exception):
                await self.websocket.send_json(event)

    async def run(self) -> None:
        await self.websocket.accept()
        settings = self.settings_store.load()
        self.conversation_id = self.db.get_value("last_conversation_id")
        await self.emit(
            {
                "type": "ready",
                "data": {
                    "model": settings.models.local_model,
                    "assistant_name": settings.assistant_name,
                    "language": settings.interface.language,
                    "low_power": settings.interface.low_power,
                    "wake_available": wake.available(settings.audio),
                },
            }
        )
        await self.emit({"type": "state", "state": "idle", "detail": ""})

        self._last_activity = time.monotonic()
        timer_task = asyncio.create_task(self._timer_watch())
        proactive_task = asyncio.create_task(self._proactive_watch())
        memory_task = asyncio.create_task(self._memory_watch())
        await self._start_wake_listening()
        try:
            while True:
                payload = await self.websocket.receive_json()
                await self._handle(payload)
        except WebSocketDisconnect:
            pass
        except Exception:
            logger.exception("WebSocket session ended unexpectedly")
        finally:
            self._closing = True
            timer_task.cancel()
            proactive_task.cancel()
            memory_task.cancel()
            self._cancel_proactive_job()
            await self._stop_wake_listening()
            self.broker.cancel_all()

    async def _handle(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        kind = payload.get("type")

        if kind == "user_text":
            text = str(payload.get("text", "")).strip()
            if not text:
                return
            self._cancel_proactive_job()
            if self._task and not self._task.done():
                await self.emit(
                    {"type": "error", "message": "Still working on the previous request."}
                )
                return
            await self._stop_wake_listening()
            self._task = asyncio.create_task(self._run_agent(text))
            self._task.add_done_callback(self._task_done)
            return

        if kind == "confirm_response":
            request_id = str(payload.get("request_id", ""))
            approved = bool(payload.get("approved", False))
            if not self.broker.resolve(request_id, approved):
                await self.emit({"type": "error", "message": "That confirmation already expired."})
            return

        if kind == "cancel":
            self._cancel_proactive_job()
            if self._task and not self._task.done():
                self._task.cancel()
            self.broker.cancel_all()
            await self.emit({"type": "state", "state": "idle", "detail": "cancelled"})
            return

        if kind == "ping":
            await self.emit({"type": "pong"})
            return

        if kind == "start_listening":
            if self._task and not self._task.done():
                return
            self._cancel_proactive_job()
            await self._stop_wake_listening()
            self._task = asyncio.create_task(self._listen())
            self._task.add_done_callback(self._task_done)
            return

        await self.emit({"type": "error", "message": f"Unknown message type: {kind}"})

    def _task_done(self, _task: asyncio.Task) -> None:
        if self._closing:
            return
        with contextlib.suppress(RuntimeError):
            asyncio.create_task(self._start_wake_listening())

    async def _start_wake_listening(self) -> None:
        """Start the wake-word loop only when no recording is in progress."""
        if self._closing:
            return
        if self._wake_task and not self._wake_task.done():
            return
        if self._task and not self._task.done():
            return
        settings = self.settings_store.load()
        if not wake.available(settings.audio):
            return

        stop = threading.Event()
        self._wake_stop = stop
        loop = asyncio.get_running_loop()

        def detected() -> None:
            if stop.is_set() or self._closing:
                return
            with contextlib.suppress(RuntimeError):
                asyncio.run_coroutine_threadsafe(self._on_wake(), loop)

        self._wake_task = asyncio.create_task(
            asyncio.to_thread(wake.listen, settings.audio, stop, detected)
        )
        self._wake_task.add_done_callback(self._wake_done)

    def _wake_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error:
            logger.info("Wake-word listener stopped: %s", error)

    async def _stop_wake_listening(self) -> None:
        stop = self._wake_stop
        task = self._wake_task
        self._wake_stop = None
        self._wake_task = None
        if stop is not None:
            stop.set()
        if task is not None and not task.done():
            with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
                await asyncio.wait_for(task, timeout=2)

    async def _on_wake(self) -> None:
        if self._closing:
            return
        if self._task and not self._task.done():
            return
        self._cancel_proactive_job()
        await self._stop_wake_listening()
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._listen())
        self._task.add_done_callback(self._task_done)

    async def _run_agent(self, text: str) -> None:
        settings = self.settings_store.load()
        self._last_activity = time.monotonic()
        self.conversation_id = self.db.ensure_conversation(
            self.conversation_id or None, title=text[:60]
        )
        self.db.set_value("last_conversation_id", self.conversation_id)
        self.db.add_message(self.conversation_id, "user", text)
        await self.emit(
            {
                "type": "transcript",
                "data": {
                    "role": "user",
                    "text": text,
                    "conversation_id": self.conversation_id,
                },
            }
        )

        history = self.db.recent_messages(self.conversation_id, limit=12)[:-1]
        agent = Agent(settings, self.db, self.emit, self.broker)

        try:
            result = await agent.run(text, self.conversation_id, history)
        except LLMError as exc:
            await self.emit({"type": "state", "state": "error", "detail": str(exc)})
            await self.emit({"type": "error", "message": str(exc)})
            return
        except asyncio.CancelledError:
            await self.emit({"type": "state", "state": "idle", "detail": "cancelled"})
            return
        except Exception:
            logger.exception("Agent run failed")
            await self.emit(
                {"type": "error", "message": "Something went wrong while thinking. Try again."}
            )
            return

        self.db.add_message(self.conversation_id, "assistant", result.text)
        await self.emit(
            {
                "type": "transcript",
                "data": {
                    "role": "assistant",
                    "text": result.text,
                    "conversation_id": self.conversation_id,
                    "used_online": result.used_online,
                },
            }
        )
        await self.emit({"type": "state", "state": "idle", "detail": ""})
        if settings.voice.speak_replies:
            await self.emit({"type": "speak", "data": {"text": result.text}})

    async def _listen(self) -> None:
        settings = self.settings_store.load()
        loop = asyncio.get_running_loop()

        def level(value: float) -> None:
            asyncio.run_coroutine_threadsafe(
                self.emit(
                    {
                        "type": "audio_level",
                        "data": {"source": "mic", "level": min(1.0, value / 8000.0)},
                    }
                ),
                loop,
            )

        await self._stop_wake_listening()
        await self.emit({"type": "state", "state": "listening", "detail": ""})
        try:
            try:
                text = await asyncio.to_thread(listen_once, settings, None, level)
            except (AudioUnavailable, Exception) as exc:
                await self.emit({"type": "state", "state": "idle", "detail": ""})
                await self.emit({"type": "error", "message": f"Listening failed: {exc}"})
                return

            await self.emit({"type": "state", "state": "idle", "detail": ""})
            await self._run_agent(text)
        finally:
            await self._start_wake_listening()

    async def _memory_watch(self) -> None:
        """Drop the speech model when free RAM falls below the configured floor."""
        try:
            import psutil
        except ImportError:
            return
        try:
            while True:
                await asyncio.sleep(30)
                settings = self.settings_store.load()
                available_mb = int(psutil.virtual_memory().available / 1024 / 1024)
                if available_mb >= settings.ram_floor_mb:
                    continue
                if self._task and not self._task.done():
                    continue
                await asyncio.to_thread(stt.unload)
                logger.info(
                    "Unloaded the speech model: %s MB available, floor is %s MB",
                    available_mb,
                    settings.ram_floor_mb,
                )
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Memory watcher stopped")

    def _cancel_proactive_job(self) -> None:
        job = self._proactive_job
        if job and not job.done():
            job.cancel()

    async def _proactive_watch(self) -> None:
        try:
            while True:
                await asyncio.sleep(15)
                settings = self.settings_store.load()
                if not settings.proactive.enabled or not self.conversation_id:
                    continue
                if self._task and not self._task.done():
                    continue
                idle_for = time.monotonic() - self._last_activity
                if idle_for < settings.proactive.interval_minutes * 60:
                    continue

                job = asyncio.create_task(self._proactive_check_in(settings))
                self._proactive_job = job
                try:
                    await job
                except asyncio.CancelledError:
                    if self._closing:
                        raise
                    continue
                finally:
                    self._proactive_job = None
                    self._last_activity = time.monotonic()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Proactive watcher stopped")

    async def _proactive_check_in(self, settings) -> None:
        history = self.db.recent_messages(self.conversation_id, limit=8)
        if not history:
            return
        agent = Agent(settings, self.db, self.emit, self.broker)
        text = await agent.proactive(history)
        if not text:
            return
        self.db.add_message(self.conversation_id, "assistant", text)
        await self.emit(
            {
                "type": "transcript",
                "data": {
                    "role": "assistant",
                    "text": text,
                    "conversation_id": self.conversation_id,
                },
            }
        )
        if settings.voice.speak_replies:
            await self.emit({"type": "speak", "data": {"text": text}})

    async def _timer_watch(self) -> None:
        try:
            while True:
                await asyncio.sleep(15)
                settings = self.settings_store.load()
                for timer in self.db.due_timers():
                    self.db.complete_timer(int(timer["id"]))
                    await self.emit(
                        {
                            "type": "timer_due",
                            "data": {"label": timer["label"], "id": timer["id"]},
                        }
                    )
                    if settings.voice.speak_replies:
                        prefix = REMINDER_PREFIX.get(
                            settings.interface.language, REMINDER_PREFIX["en"]
                        )
                        await self.emit(
                            {
                                "type": "speak",
                                "data": {"text": f"{prefix}{timer['label']}"},
                            }
                        )
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Timer watcher stopped")
            return
