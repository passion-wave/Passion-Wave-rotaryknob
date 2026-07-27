#!/usr/bin/env python3
"""Monitor EC1 raw PCNT direction counters without exposing API credentials."""

import argparse
import asyncio
from pathlib import Path
import time

import yaml
from aioesphomeapi import APIClient


NAMES = {
    "EC1 Encoder Left Pulses",
    "EC1 Encoder Right Pulses",
    "EC1 Encoder Net Count",
    "EC1 Encoder Read Errors",
    "EC1 Encoder Maximum Batch",
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
    values: dict[str, float] = {}

    def on_state(state) -> None:
        name = names_by_key.get(state.key)
        if name is not None:
            values[name] = float(state.state)

    client.subscribe_states(on_state)
    deadline = time.monotonic() + 5
    while len(values) < len(names_by_key) and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
    if "EC1 Encoder Left Pulses" not in values or "EC1 Encoder Right Pulses" not in values:
        await client.disconnect()
        raise RuntimeError("EC1 diagnostic entities were not received")

    origin = values.copy()
    previous = values.copy()
    print("Jetzt nur in die problematische Abwaertsrichtung drehen.", flush=True)
    for elapsed in range(1, seconds + 1):
        await asyncio.sleep(1)
        left = values["EC1 Encoder Left Pulses"] - origin["EC1 Encoder Left Pulses"]
        right = values["EC1 Encoder Right Pulses"] - origin["EC1 Encoder Right Pulses"]
        new_left = values["EC1 Encoder Left Pulses"] - previous["EC1 Encoder Left Pulses"]
        new_right = values["EC1 Encoder Right Pulses"] - previous["EC1 Encoder Right Pulses"]
        errors = values.get("EC1 Encoder Read Errors", 0) - origin.get("EC1 Encoder Read Errors", 0)
        print(
            f"{elapsed:02d}s  neu links={new_left:+.0f}  neu rechts={new_right:+.0f}  "
            f"gesamt links={left:.0f} rechts={right:.0f}  fehler={errors:.0f}",
            flush=True,
        )
        previous = values.copy()

    left = values["EC1 Encoder Left Pulses"] - origin["EC1 Encoder Left Pulses"]
    right = values["EC1 Encoder Right Pulses"] - origin["EC1 Encoder Right Pulses"]
    errors = values.get("EC1 Encoder Read Errors", 0) - origin.get("EC1 Encoder Read Errors", 0)
    print("\nAuswertung:")
    if left > 0 and right == 0 and errors == 0:
        print("Der Abwaerts-/Linkskanal kommt sauber am S3 an; der Fehler liegt in der UI-Zuordnung.")
    elif left == 0 and right == 0:
        print("Keine Rohpulse empfangen; Pin, EC1-Leitung oder Drehrichtung pruefen.")
    elif left == 0 and right > 0:
        print("Die Bewegung kommt auf dem Rechtskanal an; die dokumentierte Richtung ist vertauscht.")
    elif left > 0 and right > 0:
        print("Beide Leitungen pulsen bei nur einer Drehrichtung; EC1-Signal oder Pinzuordnung pruefen.")
    else:
        print("Rohdaten erhalten; Ausgabe zusammen mit der beobachteten UI-Reaktion auswerten.")
    await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="passion-wave-managed-2-s3.local")
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument(
        "--secrets",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "esphome" / "secrets.yaml",
    )
    args = parser.parse_args()
    asyncio.run(monitor(args.host, args.seconds, args.secrets))


if __name__ == "__main__":
    main()
