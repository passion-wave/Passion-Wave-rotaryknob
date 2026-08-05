"""Tests for the dependency-free PassionWave media contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1] / "custom_components" / "passion_wave" / "media.py"
)
SPEC = importlib.util.spec_from_file_location("passion_wave_media", MODULE_PATH)
assert SPEC and SPEC.loader
MEDIA = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MEDIA
SPEC.loader.exec_module(MEDIA)


class MediaContractTests(unittest.TestCase):
    def test_latest_playback_queue_collapses_pending_commands(self) -> None:
        queue = MEDIA.LatestPlaybackQueue()
        first = queue.submit(
            kind=5,
            index=1,
            media_id="track://first",
            media_type="track",
        )
        second = queue.submit(
            kind=5,
            index=2,
            media_id="track://second",
            media_type="track",
        )

        self.assertFalse(queue.is_current(first.generation))
        self.assertTrue(queue.is_current(second.generation))
        self.assertEqual(second, queue.latest_after(first.generation))

    def test_stale_completion_does_not_clear_newer_playback(self) -> None:
        queue = MEDIA.LatestPlaybackQueue()
        first = queue.submit(
            kind=4,
            index=0,
            media_id="playlist://first",
            media_type="playlist",
        )
        second = queue.submit(
            kind=5,
            index=0,
            media_id="track://second",
            media_type="track",
        )

        queue.complete(first.generation)
        self.assertEqual(second, queue.latest_after(first.generation))
        queue.complete(second.generation)
        self.assertIsNone(queue.latest_after(first.generation))

    def test_repeated_identical_track_has_a_distinct_generation(self) -> None:
        queue = MEDIA.LatestPlaybackQueue()
        first = queue.submit(
            kind=5,
            index=2,
            media_id="track://same",
            media_type="track",
        )
        second = queue.submit(
            kind=5,
            index=2,
            media_id="track://same",
            media_type="track",
        )

        self.assertGreater(second.generation, first.generation)
        self.assertFalse(queue.is_current(first.generation))
        self.assertTrue(queue.is_current(second.generation))

    def test_bounded_page(self) -> None:
        self.assertEqual((0, 1), MEDIA.bounded_page(-4, 0, 64))
        self.assertEqual((5, 64), MEDIA.bounded_page(5, 99, 64))

    def test_library_normalization_preserves_paging(self) -> None:
        result = MEDIA.normalize_library_page(
            {
                "items": [
                    {"name": "A", "uri": "library://playlist/1"},
                    {"title": "B", "id": "library://playlist/2"},
                ],
                "total": 7,
            },
            "playlist",
            2,
            2,
        )
        self.assertEqual(2, result["returned"])
        self.assertEqual(7, result["total"])
        self.assertTrue(result["has_more"])
        self.assertEqual("library://playlist/2", result["items"][1]["uri"])

    def test_library_visibility_filter_is_applied_before_paging(self) -> None:
        response = {
            "items": [
                {
                    "name": f"Playlist {index}",
                    "uri": f"library://playlist/{index}",
                }
                for index in range(8)
            ]
        }
        result = MEDIA.filter_library_page(
            response,
            "playlist",
            1,
            2,
            (
                "library://playlist/1",
                "library://playlist/4",
                "library://playlist/7",
            ),
        )
        self.assertEqual(3, result["total"])
        self.assertEqual(
            ["library://playlist/4", "library://playlist/7"],
            [item["uri"] for item in result["items"]],
        )
        self.assertFalse(result["has_more"])

    def test_missing_total_keeps_full_page_open_ended(self) -> None:
        result = MEDIA.normalize_library_page(
            {
                "items": [
                    {"name": f"Playlist {index}", "uri": f"playlist://{index}"}
                    for index in range(4)
                ]
            },
            "playlist",
            0,
            4,
        )
        self.assertEqual(0, result["total"])
        self.assertTrue(result["has_more"])

    def test_missing_total_closes_partial_final_page(self) -> None:
        result = MEDIA.normalize_library_page(
            {"items": [{"name": "Last", "uri": "playlist://last"}]},
            "playlist",
            40,
            40,
        )
        self.assertEqual(41, result["total"])
        self.assertFalse(result["has_more"])

    def test_browse_response_is_sliced_before_transport(self) -> None:
        children = [
            {
                "title": f"Artist - Track {index}",
                "media_content_id": f"track://{index}",
            }
            for index in range(20)
        ]
        result = MEDIA.normalize_browse_page(
            {"media_player.kitchen": {"children": children}},
            "media_player.kitchen",
            5,
            4,
        )
        self.assertEqual(4, result["returned"])
        self.assertEqual(20, result["total"])
        self.assertEqual("track://5", result["items"][0]["uri"])
        self.assertEqual("Track 5", result["items"][0]["title"])
        self.assertEqual("Artist", result["items"][0]["artists"][0]["name"])
        self.assertTrue(result["has_more"])

    def test_browse_media_object_is_converted_before_slicing(self) -> None:
        class BrowseMediaResponse:
            def as_dict(self) -> dict[str, object]:
                return {
                    "children": [
                        {
                            "title": "Artist - Track",
                            "media_content_id": "track://object",
                            "media_content_type": "music",
                        }
                    ]
                }

        result = MEDIA.normalize_browse_page(
            {"media_player.kitchen": BrowseMediaResponse()},
            "media_player.kitchen",
            0,
            16,
        )
        self.assertEqual(1, result["returned"])
        self.assertEqual(1, result["total"])
        self.assertEqual("Track", result["items"][0]["title"])
        self.assertEqual("Artist", result["items"][0]["artists"][0]["name"])
        self.assertEqual("track://object", result["items"][0]["uri"])


if __name__ == "__main__":
    unittest.main()
