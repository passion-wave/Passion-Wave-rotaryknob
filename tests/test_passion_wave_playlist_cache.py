"""Regression tests for full-playlist fetch amplification during paging."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import homeassistant  # noqa: F401

from custom_components.passion_wave import async_setup


def test_playlist_pages_share_one_browse_and_refresh_on_reopen():
    async def run():
        handlers = {}
        response = {"media_player.test": {"children": [
            {"title": f"Track {i}", "media_content_id": f"track://{i}"}
            for i in range(620)
        ]}}
        services = SimpleNamespace(
            async_register=lambda domain, name, handler, **kwargs: handlers.update({name: handler}),
            async_call=AsyncMock(return_value=response),
        )
        hass = SimpleNamespace(services=services)
        entry = SimpleNamespace(entry_id="entry-a", data={"media_player": "media_player.test"}, options={})
        await async_setup(hass, {})
        with patch("custom_components.passion_wave._get_loaded_entry", return_value=entry):
            async def page(offset):
                return await handlers["get_playlist_tracks"](SimpleNamespace(data={
                    "config_entry_id": entry.entry_id, "playlist_id": "library://playlist/1",
                    "offset": offset, "limit": 16,
                }))
            pages = [await page(offset) for offset in range(0, 620, 16)]
            assert services.async_call.await_count == 1
            assert sum(p["returned"] for p in pages) == 620
            assert pages[1]["items"][0]["uri"] == "track://16"
            await page(0)
            assert services.async_call.await_count == 2
    asyncio.run(run())


def test_cache_separates_accounts_players_and_provider_uris():
    from custom_components.passion_wave.media import PlaylistBrowseCache

    async def run():
        cache = PlaylistBrowseCache()
        fetch = AsyncMock(side_effect=["a", "b", "c", "d"])
        keys = [
            ("knob-a", "ma-a", "player-a", "spotify--a://playlist/1"),
            ("knob-b", "ma-a", "player-a", "spotify--a://playlist/1"),
            ("knob-a", "ma-a", "player-b", "spotify--a://playlist/1"),
            ("knob-a", "ma-a", "player-a", "spotify--b://playlist/1"),
        ]
        for key, expected in zip(keys, "abcd", strict=True):
            assert await cache.get(key, fetch) == expected
        for key, expected in zip(keys, "abcd", strict=True):
            assert await cache.get(key, fetch) == expected
        assert fetch.await_count == 4
    asyncio.run(run())


def test_concurrent_pages_coalesce_and_cancelled_waiter_does_not_cancel_fetch():
    from custom_components.passion_wave.media import PlaylistBrowseCache

    async def run():
        cache = PlaylistBrowseCache()
        started, finish = asyncio.Event(), asyncio.Event()
        calls = 0
        async def fetch():
            nonlocal calls
            calls += 1
            started.set()
            await finish.wait()
            return "tracks"
        first = asyncio.create_task(cache.get(("a",), fetch, refresh=True))
        await started.wait()
        second = asyncio.create_task(cache.get(("a",), fetch))
        await asyncio.sleep(0)
        first.cancel()
        try:
            await first
        except asyncio.CancelledError:
            pass
        finish.set()
        assert await second == "tracks"
        assert await cache.get(("a",), fetch) == "tracks"
        assert calls == 1
    asyncio.run(run())


def test_failed_refresh_cannot_serve_stale_tracks():
    from custom_components.passion_wave.media import PlaylistBrowseCache

    async def run():
        cache = PlaylistBrowseCache()
        fetch = AsyncMock(side_effect=["old", RuntimeError("provider unavailable"), "new"])
        assert await cache.get(("a",), fetch) == "old"
        try:
            await cache.get(("a",), fetch, refresh=True)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Provider error was swallowed")
        assert await cache.get(("a",), fetch) == "new"
    asyncio.run(run())


def test_cache_expires_and_evicts_oldest_playlist():
    from custom_components.passion_wave.media import PlaylistBrowseCache

    async def run():
        fetch = AsyncMock(return_value="tracks")
        expired = PlaylistBrowseCache(ttl=0)
        await expired.get(("a",), fetch)
        await expired.get(("a",), fetch)
        assert fetch.await_count == 2
        bounded = PlaylistBrowseCache(maximum=1)
        await bounded.get(("a",), fetch)
        await bounded.get(("b",), fetch)
        await bounded.get(("a",), fetch)
        assert fetch.await_count == 5
    asyncio.run(run())


def test_cache_refresh_with_home_assistant_eager_task_factory():
    from custom_components.passion_wave.media import PlaylistBrowseCache

    async def run():
        loop = asyncio.get_running_loop()
        loop.set_task_factory(asyncio.eager_task_factory)
        cache = PlaylistBrowseCache()
        fetch = AsyncMock(side_effect=["old", "new"])
        assert await cache.get(("a",), fetch) == "old"
        assert await cache.get(("a",), fetch, refresh=True) == "new"
        assert fetch.await_count == 2
    asyncio.run(run())
