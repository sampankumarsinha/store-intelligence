
"""Terminal live dashboard polling Store Intelligence API."""
from __future__ import annotations

import os
import time
from datetime import datetime

import httpx

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

API_URL = os.getenv("API_URL", "http://localhost:8000")
STORE_ID = os.getenv("STORE_ID", "STORE_001")
POLL_SEC = float(os.getenv("POLL_SEC", "2"))


def fetch_metrics(client: httpx.Client) -> dict:
    r = client.get(f"{API_URL}/stores/{STORE_ID}/metrics", timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_health(client: httpx.Client) -> dict:
    r = client.get(f"{API_URL}/health", timeout=10)
    r.raise_for_status()
    return r.json()


def render_plain(metrics: dict, health: dict) -> str:
    last_ts = health.get("last_event_timestamp_per_store", {}).get(STORE_ID, "n/a")
    return (
        f"\n=== Store Intelligence Live ({STORE_ID}) ===\n"
        f"Time: {datetime.utcnow().isoformat()}Z\n"
        f"Unique visitors: {metrics.get('unique_visitors', 0)}\n"
        f"Queue depth: {metrics.get('current_queue_depth', 0)}\n"
        f"Conversion rate: {metrics.get('conversion_rate', 0)}%\n"
        f"Latest event: {last_ts}\n"
        f"API status: {health.get('status')}\n"
    )


def build_table(metrics: dict, health: dict) -> Table:
    table = Table(title=f"Live Dashboard — {STORE_ID}")
    table.add_column("Metric")
    table.add_column("Value")
    last_ts = health.get("last_event_timestamp_per_store", {}).get(STORE_ID, "n/a")
    table.add_row("Unique visitors", str(metrics.get("unique_visitors", 0)))
    table.add_row("Queue depth", str(metrics.get("current_queue_depth", 0)))
    table.add_row("Conversion rate", f"{metrics.get('conversion_rate', 0)}%")
    table.add_row("Abandonment rate", f"{metrics.get('abandonment_rate', 0)}%")
    table.add_row("Latest event", str(last_ts))
    table.add_row("API status", str(health.get("status")))
    table.add_row("Updated", datetime.utcnow().strftime("%H:%M:%S UTC"))
    return table


def main():
    with httpx.Client() as client:
        if not HAS_RICH:
            while True:
                try:
                    metrics = fetch_metrics(client)
                    health = fetch_health(client)
                    print(render_plain(metrics, health))
                except Exception as exc:
                    print(f"Error: {exc}")
                time.sleep(POLL_SEC)
            return

        console = Console()
        with Live(console=console, refresh_per_second=2) as live:
            while True:
                try:
                    metrics = fetch_metrics(client)
                    health = fetch_health(client)
                    live.update(Panel(build_table(metrics, health)))
                except Exception as exc:
                    live.update(Panel(f"Error connecting to API: {exc}"))
                time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
