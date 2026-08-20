#!/usr/bin/env python3
"""Validate this repository's AGENTS Markdown inventory and local links."""

from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git", ".cache", ".release-pipeline", ".esphome", ".esphome_cache",
    ".pytest_cache", ".next", "dist", "node_modules", "public", ".wrangler",
    ".wrangler-dry-run", "__pycache__",
}
ENTRY = re.compile(r"^\|\s*`([^`]+\.md)`\s*\|\s*`?(evergreen|current|historical|generated)`?\s*\|", re.MULTILINE)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    agent = (ROOT / "AGENTS.md").read_text()
    block = agent.split("<!-- docs-index:start -->", 1)[1].split("<!-- docs-index:end -->", 1)[0]
    entries = ENTRY.findall(block)
    indexed = [path for path, _ in entries]
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.md")
        if not any(part in EXCLUDED for part in path.parts)
    }
    failures = []
    for path in sorted(actual - set(indexed)):
        failures.append(f"Markdown not indexed: {path}")
    for path in sorted(set(indexed) - actual):
        failures.append(f"Indexed Markdown missing: {path}")
    for path in sorted({value for value in indexed if indexed.count(value) > 1}):
        failures.append(f"Markdown indexed more than once: {path}")
    statuses = dict(entries)
    version = (ROOT / "VERSION").read_text().strip()
    for relative in sorted(actual):
        path = ROOT / relative
        content = path.read_text(errors="replace")
        if statuses.get(relative) == "evergreen" and version in content:
            failures.append(f"Current version in evergreen Markdown: {relative}")
        for target in LINK.findall(content):
            value = target.strip().split(maxsplit=1)[0].strip("<>")
            if not value or value.startswith(("#", "http://", "https://", "mailto:")):
                continue
            local = unquote(value.split("#", 1)[0].split("?", 1)[0])
            if local and not (path.parent / local).resolve().exists():
                failures.append(f"Dead local link in {relative}: {value}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"OK: {len(actual)} Markdown objects indexed and linked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
