"""Bounded Music Assistant response handling for PassionWave."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def bounded_page(offset: int, limit: int, maximum: int) -> tuple[int, int]:
    """Return safe paging values."""
    return max(0, int(offset)), min(max(1, int(limit)), maximum)


def unwrap_response(response: Any) -> Mapping[str, Any]:
    """Unwrap the response envelopes used by HA and ESPHome actions."""
    current = response
    for key in ("response", "service_response", "result", "content"):
        if not isinstance(current, Mapping):
            break
        nested = current.get(key)
        if isinstance(nested, Mapping):
            current = nested
    return current if isinstance(current, Mapping) else {}


def normalize_library_page(
    response: Any,
    media_type: str,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Normalize a Music Assistant library page into the firmware contract."""
    root = unwrap_response(response)
    source = root.get("items", [])
    items = (
        source if isinstance(source, Sequence) and not isinstance(source, str) else []
    )

    normalized: list[dict[str, str]] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        name = str(
            item.get("name") or item.get("title") or f"Eintrag {offset + index + 1}"
        )
        uri = str(
            item.get("uri") or item.get("id") or item.get("media_content_id") or ""
        )
        item_id = str(item.get("item_id") or item.get("playlist_item_id") or "")
        normalized.append(
            {
                "name": name,
                "title": name,
                "uri": uri,
                "item_id": item_id,
                "media_type": str(
                    item.get("media_type") or item.get("type") or media_type
                ),
            }
        )

    returned = len(normalized)
    explicit_more = root.get("has_more")
    has_more = bool(explicit_more) if explicit_more is not None else returned >= limit
    total_value = root.get("total")
    try:
        total = max(offset + returned, int(total_value))
    except (TypeError, ValueError):
        # Music Assistant currently omits a total. A full page therefore means
        # "unknown total", not "this page ends the catalog".
        total = 0 if has_more else offset + returned
    if total > offset + returned:
        has_more = True

    return {
        "offset": offset,
        "limit": limit,
        "returned": returned,
        "total": total,
        "has_more": has_more,
        "items": normalized,
    }


def filter_library_page(
    response: Any,
    media_type: str,
    offset: int,
    limit: int,
    allowed_uris: Sequence[str],
) -> dict[str, Any]:
    """Filter a complete MA catalog and return one firmware-sized page."""
    complete = normalize_library_page(response, media_type, 0, 1)
    allowed = set(allowed_uris)
    selected = [item for item in complete["items"] if item["uri"] in allowed]
    page = selected[offset : offset + limit]
    return {
        "offset": offset,
        "limit": limit,
        "returned": len(page),
        "total": len(selected),
        "has_more": offset + len(page) < len(selected),
        "items": page,
    }


def normalize_browse_page(
    response: Any,
    entity_id: str,
    offset: int,
    limit: int,
) -> dict[str, Any]:
    """Slice a browse_media tree in HA before it reaches the bridge."""
    root = unwrap_response(response)
    node: Any = root.get(entity_id, root)
    node = unwrap_response(node)
    source = node.get("children", [])
    children = (
        source if isinstance(source, Sequence) and not isinstance(source, str) else []
    )
    total = len(children)

    items: list[dict[str, Any]] = []
    for item in children[offset : offset + limit]:
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or item.get("name") or "")
        artist = str(item.get("artist") or "")
        artists = item.get("artists")
        if (
            not artist
            and isinstance(artists, Sequence)
            and not isinstance(artists, str)
            and artists
        ):
            first_artist = artists[0]
            artist = str(
                first_artist.get("name", "")
                if isinstance(first_artist, Mapping)
                else first_artist
            )
        # Music Assistant's HA browse adapter encodes the first artist into
        # the title as "Artist - Track" instead of exposing an artists field.
        if not artist and " - " in title:
            artist, title = title.split(" - ", 1)
        items.append(
            {
                "name": title,
                "title": title,
                "uri": str(item.get("media_content_id") or item.get("uri") or ""),
                "media_type": str(item.get("media_content_type") or "track"),
                "artists": [{"name": artist}] if artist else [],
                "image": str(item.get("thumbnail") or item.get("image") or ""),
            }
        )

    return {
        "offset": offset,
        "limit": limit,
        "returned": len(items),
        "total": total,
        "has_more": offset + len(items) < total,
        "items": items,
    }
