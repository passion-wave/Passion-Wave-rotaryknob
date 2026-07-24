#!/usr/bin/env python3
"""Timestamp the ESP32/S3 link and library status during an S3 restart."""

import argparse
import asyncio
from pathlib import Path
import time

import yaml
from aioesphomeapi import APIClient


NAMES = {
    "S3 Link Connected",
    "ESP32 Library Proxy Status",
    "UART Protocol Errors",
}


async def monitor(host: str, seconds: int, secrets_path: Path) -> None:
    secrets = yaml.safe_load(secrets_path.read_text())
    client = APIClient(
        host,
        6053,
        "",
        noise_psk=secrets["api_encryption_key"],
    )
    await client.connect(login=True)
    entities, _ = await client.list_entities_services()
    names_by_key = {entity.key: entity.name for entity in entities if entity.name in NAMES}
    started = time.monotonic()
    last_values: dict[str, object] = {}

    def on_state(state) -> None:
        name = names_by_key.get(state.key)
        if name is None:
            return
        value = getattr(state, "state", None)
        if last_values.get(name) == value:
            return
        last_values[name] = value
        print(f"{time.monotonic() - started:7.3f}s  {name}: {value}", flush=True)

    client.subscribe_states(on_state)
    await asyncio.sleep(seconds)
    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.2.104")
    parser.add_argument("--seconds", type=int, default=45)
    parser.add_argument(
        "--secrets",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "esphome" / "secrets.yaml",
    )
    args = parser.parse_args()
    asyncio.run(monitor(args.host, args.seconds, args.secrets))


if __name__ == "__main__":
    main()
