"""Slow providers must retain callback ownership without duplicate playback."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import custom_components.passion_wave.broker as broker


def _setup(monkeypatch):
    coordinator = broker._PlaybackCoordinator()
    entry = SimpleNamespace(entry_id="test")
    hass = SimpleNamespace(services=SimpleNamespace(async_call=AsyncMock()))
    results = []
    monkeypatch.setattr(broker, "_PLAYBACK_PROGRESS_SECONDS", 0.001)
    monkeypatch.setattr(broker, "_validated_media_target", lambda _: "media_player.test")

    async def complete(_hass, _entry, command, result):
        results.append((command.generation, result))

    monkeypatch.setattr(broker, "_async_complete_media", complete)
    return hass, entry, coordinator, results


def _submit(coordinator, uri="spotify--account-a://playlist/one"):
    return coordinator.queue.submit(
        kind=4, index=3, media_id=uri, media_type="playlist"
    )


def test_slow_start_sends_progress_then_one_terminal_result(monkeypatch):
    async def run():
        hass, entry, coordinator, results = _setup(monkeypatch)
        command = _submit(coordinator)
        release = asyncio.Event()
        # AsyncMock must await the simulated service, just as HA does.
        async def service(*args, **kwargs):
            await release.wait()

        hass.services.async_call.side_effect = service
        task = asyncio.create_task(
            broker._async_run_playback_coordinator(hass, entry, coordinator)
        )
        async with asyncio.timeout(1):
            while len(results) < 4:
                await asyncio.sleep(0.001)
        assert results == [(command.generation, 127)] * len(results)
        assert not task.done()
        assert hass.services.async_call.await_count == 1
        assert hass.services.async_call.call_args.args[2]["media_id"] == command.media_id
        release.set()
        await task
        assert results[-1] == (command.generation, 0)
        count = len(results)
        await asyncio.sleep(0.005)
        assert len(results) == count
        assert coordinator.queue.latest_after(0) is None

    asyncio.run(run())


def test_timeout_cancels_wait_and_reports_timeout_once(monkeypatch):
    async def run():
        hass, entry, coordinator, results = _setup(monkeypatch)
        command = _submit(coordinator)
        monkeypatch.setattr(broker, "_PLAYBACK_TIMEOUT_SECONDS", 0.02)
        cancelled = asyncio.Event()

        async def service(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        hass.services.async_call.side_effect = service
        await broker._async_run_playback_coordinator(hass, entry, coordinator)
        assert cancelled.is_set()
        assert results[-1] == (command.generation, 6)
        assert [result for _, result in results if result != 127] == [6]
        assert hass.services.async_call.await_count == 1
        assert coordinator.queue.latest_after(0) is None

    asyncio.run(run())


def test_superseded_start_cannot_complete_new_selection(monkeypatch):
    async def run():
        hass, entry, coordinator, results = _setup(monkeypatch)
        first = _submit(coordinator)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def service(*args, **kwargs):
            entered.set()
            await release.wait()

        hass.services.async_call.side_effect = service
        task = asyncio.create_task(
            broker._async_run_playback_coordinator(hass, entry, coordinator)
        )
        await entered.wait()
        newest = _submit(coordinator, "spotify--account-b://playlist/two")
        async with asyncio.timeout(1):
            while not results:
                await asyncio.sleep(0.001)
        assert all(item == (newest.generation, 127) for item in results)
        release.set()
        await task
        assert results[-1] == (newest.generation, 0)
        assert all(generation == newest.generation for generation, _ in results)
        assert hass.services.async_call.await_count == 2
        assert first.generation != newest.generation
        assert hass.services.async_call.call_args.args[2]["media_id"] == newest.media_id

    asyncio.run(run())


def test_unload_cancels_progress_and_does_not_send_success(monkeypatch):
    async def run():
        hass, entry, coordinator, results = _setup(monkeypatch)
        _submit(coordinator)
        entered = asyncio.Event()

        async def service(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        hass.services.async_call.side_effect = service
        task = asyncio.create_task(
            broker._async_run_playback_coordinator(hass, entry, coordinator)
        )
        await entered.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        count = len(results)
        await asyncio.sleep(0.005)
        assert len(results) == count
        assert all(result == 127 for _, result in results)
        assert coordinator.task is None

    asyncio.run(run())
