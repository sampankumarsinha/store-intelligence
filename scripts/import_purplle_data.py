#!/usr/bin/env python3
"""Import Purplle sample events + POS into data/ for the Store Intelligence API."""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from detection.purplle_adapter import convert_purplle_jsonl, convert_purplle_pos_csv
DEFAULT_EVENTS = ROOT / "detection" / "sample_eventsbe42122.jsonl"
DEFAULT_POS = ROOT / "detection" / "POS - sample transactionsb1e826f.csv"
STORE2_VIDEOS = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Store 2"

def main() -> None:
    parser = argparse.ArgumentParser(description="Import Purplle challenge datasets")
    parser.add_argument("--events", type=Path, default=DEFAULT_EVENTS)
    parser.add_argument("--pos", type=Path, default=DEFAULT_POS)
    parser.add_argument("--output-events", type=Path, default=ROOT / "data" / "purplle_events.jsonl")
    parser.add_argument(
        "--output-pos",
        type=Path,
        default=ROOT / "data" / "pos_transactions_purplle.csv",
        help="Purplle POS output (does not overwrite challenge pos_transactions.csv)",
    )
    parser.add_argument("--also-sample", action="store_true", help="Copy converted events to data/sample_events.jsonl")
    parser.add_argument("--link-store2-videos", action="store_true")
    args = parser.parse_args()

    if not args.events.exists():
        raise SystemExit(f"Purplle events file not found: {args.events}")
    if not args.pos.exists():
        raise SystemExit(f"Purplle POS file not found: {args.pos}")

    n_events = convert_purplle_jsonl(args.events, args.output_events)
    n_orders = convert_purplle_pos_csv(args.pos, args.output_pos)
    print(f"Converted {n_events} events → {args.output_events}")
    print(f"Converted {n_orders} POS orders → {args.output_pos}")

    if args.also_sample:
        shutil.copy(args.output_events, ROOT / "data" / "sample_events.jsonl")
        print(f"Copied to {ROOT / 'data' / 'sample_events.jsonl'}")

    purplle_dir = ROOT / "data" / "purplle"
    purplle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.events, purplle_dir / "sample_events_raw.jsonl")
    shutil.copy(args.pos, purplle_dir / "pos_transactions_raw.csv")

    if args.link_store2_videos and STORE2_VIDEOS.exists():
        videos = ROOT / "data" / "videos_store2"
        videos.mkdir(parents=True, exist_ok=True)
        mapping = {
            "entry 1.mp4": "entry_1.mp4",
            "entry 2.mp4": "entry_2.mp4",
            "zone.mp4": "zone.mp4",
            "billing_area.mp4": "billing_area.mp4",
        }
        for src_name, dst_name in mapping.items():
            src = STORE2_VIDEOS / src_name
            dst = videos / dst_name
            if src.exists() and not dst.exists():
                try:
                    dst.symlink_to(src)
                except OSError:
                    shutil.copy(src, dst)
        print(f"Store 2 videos linked under {videos}")

    print("\nIngest Purplle CCTV events (store ST1076):")
    print(f"  python scripts/ingest_events.py {args.output_events}")
    print("\nNote: Purplle POS file uses store ST1008 (different store/day than CCTV sample ST1076).")


if __name__ == "__main__":
    main()
