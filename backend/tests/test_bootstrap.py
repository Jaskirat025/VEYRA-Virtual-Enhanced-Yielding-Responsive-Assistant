from __future__ import annotations

import asyncio

import pytest
from backend.bootstrap import BootstrapManager
from backend.config import SettingsStore


async def wait_until_idle(manager: BootstrapManager) -> None:
    for _ in range(100):
        if not manager.snapshot()["running"]:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("downloads did not finish")


@pytest.mark.asyncio
async def test_downloads_start_together_and_complete(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    started: list[str] = []
    gate = asyncio.Event()

    async def runner(job, settings):
        started.append(job.id)
        await gate.wait()
        job.progress = 0.5
        job.status = "done"

    manager = BootstrapManager(
        store,
        runners={"local_model": runner, "speech_model": runner},
    )

    snapshot = await manager.start()
    assert snapshot["running"] is True
    assert snapshot["complete"] is False

    for _ in range(100):
        if len(started) == 2:
            break
        await asyncio.sleep(0.01)
    assert sorted(started) == ["local_model", "speech_model"]

    gate.set()
    await wait_until_idle(manager)
    result = manager.snapshot()
    assert result["complete"] is True
    assert result["failed"] is False
    assert {job["status"] for job in result["jobs"]} == {"done"}


@pytest.mark.asyncio
async def test_failed_job_can_retry_without_restarting_done_job(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    attempts = {"local_model": 0, "speech_model": 0}

    async def runner(job, settings):
        attempts[job.id] += 1
        if job.id == "local_model" and attempts[job.id] == 1:
            raise RuntimeError("offline")
        job.status = "done"

    manager = BootstrapManager(
        store,
        runners={"local_model": runner, "speech_model": runner},
    )

    await manager.start()
    await wait_until_idle(manager)
    assert manager.snapshot()["failed"] is True

    await manager.start()
    await wait_until_idle(manager)
    result = manager.snapshot()
    assert result["complete"] is True
    assert result["failed"] is False
    assert attempts == {"local_model": 2, "speech_model": 1}
