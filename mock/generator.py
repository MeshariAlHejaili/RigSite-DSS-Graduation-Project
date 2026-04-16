"""Mock data generator that simulates the Raspberry Pi client."""
from __future__ import annotations

import argparse
import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

from scenarios import camera_fault, drift, kick, loss, normal

_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_ENV_PATH):
    load_dotenv(_ENV_PATH)

SCENARIOS = {
    "normal": normal,
    "kick": kick,
    "loss": loss,
    "drift": drift,
    "camera_fault": camera_fault,
}


def _build_payload(scenario: str, sample_index: int) -> dict:
    if scenario == "cycle":
        phase = sample_index % 40
        if phase < 20:
            return normal(sample_index)
        if phase < 30:
            return kick(sample_index)
        return loss(sample_index)
    return SCENARIOS[scenario](sample_index)


async def run(
    scenario: str,
    interval: float,
    samples_per_interval: int,
    url: str,
) -> None:
    sample_index = 0
    sample_delay = interval / max(1, samples_per_interval)

    while True:
        try:
            async with websockets.connect(url) as websocket:
                while True:
                    for _ in range(samples_per_interval):
                        payload = _build_payload(scenario, sample_index)
                        await websocket.send(json.dumps(payload))
                        print(json.dumps(payload, indent=2))
                        sample_index += 1
                        await asyncio.sleep(sample_delay)
        except (OSError, websockets.WebSocketException):
            print("Retrying connection...")
            await asyncio.sleep(3)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        default="normal",
        choices=[*SCENARIOS.keys(), "cycle"],
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds per collection window. Default: 1.0",
    )
    parser.add_argument(
        "--samples-per-interval",
        type=int,
        default=1,
        help="How many payloads to emit inside each interval window. Default: 1",
    )
    parser.add_argument(
        "--url",
        default=os.getenv("MOCK_INGEST_URL", "ws://localhost:8000/ws/ingest"),
        help="Target ingest WebSocket URL.",
    )
    args = parser.parse_args()

    samples_per_interval = max(1, args.samples_per_interval)

    try:
        asyncio.run(run(args.scenario, args.interval, samples_per_interval, args.url))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
