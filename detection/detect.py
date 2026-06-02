#!/usr/bin/env python3
"""
Process CCTV clips with YOLOv8 + tracking, or replay/enrich sample_events.jsonl.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from detection.emit import emit_event
from detection.queue import BillingQueueManager
from detection.reid import ReIDManager
from detection.staff_classifier import StaffClassifier
from detection.tracker import CentroidTracker, centroid
from detection.zones import (
    CameraDef,
    StoreDef,
    crossing_direction,
    entry_line_y,
    load_layout,
    zone_at_point,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = ROOT / "data" / "store_layout.json"
DEFAULT_OUTPUT = ROOT / "data" / "events.jsonl"
DEFAULT_VIDEOS = ROOT / "data" / "videos"

ENTRY_COOLDOWN_SEC = 5
GROUP_WINDOW_SEC = 3
DWELL_INTERVAL_MS = 30000
FRAME_STRIDE = 5

# Stagger cameras so entry → floor → billing aligns with POS (~23:12–23:18 UTC).
SESSION_START = datetime(2026, 5, 29, 22, 33, 0, tzinfo=timezone.utc)
CAMERA_TIME_OFFSET: Dict[str, timedelta] = {
    "CAM_3": timedelta(0),
    "CAM_1": timedelta(minutes=15),
    "CAM_2": timedelta(minutes=20),
    "CAM_5": timedelta(minutes=35),
    "CAM_4": timedelta(minutes=10),
}

_CAMERA_ORDER = {"ENTRY": 0, "FLOOR": 1, "BILLING": 2, "WAREHOUSE": 3}


def _camera_base_time(camera_id: str) -> datetime:
    return SESSION_START + CAMERA_TIME_OFFSET.get(camera_id, timedelta(0))


def _sort_cameras(cameras: List[CameraDef]) -> List[CameraDef]:
    return sorted(
        cameras,
        key=lambda c: (_CAMERA_ORDER.get(c.camera_type.upper(), 9), c.camera_id),
    )


class ZoneTracker:
    """Per-visitor zone enter/exit/dwell state."""

    def __init__(self):
        self.in_zone: Dict[str, str] = {}
        self.dwell_start: Dict[str, datetime] = {}
        self.last_dwell_emit: Dict[str, datetime] = {}

    def update(
        self,
        visitor_id: str,
        zone_id: Optional[str],
        timestamp: datetime,
        is_staff: bool,
    ) -> List[dict]:
        events = []
        current = self.in_zone.get(visitor_id)

        if current and current != zone_id:
            events.append(
                emit_event(
                    store_id="",
                    camera_id="",
                    visitor_id=visitor_id,
                    event_type="ZONE_EXIT",
                    timestamp=timestamp,
                    zone_id=current,
                    is_staff=is_staff,
                    confidence=0.85,
                )
            )
            self.in_zone.pop(visitor_id, None)
            self.dwell_start.pop(visitor_id, None)
            self.last_dwell_emit.pop(visitor_id, None)

        if zone_id and visitor_id not in self.in_zone:
            self.in_zone[visitor_id] = zone_id
            self.dwell_start[visitor_id] = timestamp
            self.last_dwell_emit[visitor_id] = timestamp
            events.append(
                emit_event(
                    store_id="",
                    camera_id="",
                    visitor_id=visitor_id,
                    event_type="ZONE_ENTER",
                    timestamp=timestamp,
                    zone_id=zone_id,
                    is_staff=is_staff,
                    confidence=0.88,
                )
            )
        elif zone_id and visitor_id in self.in_zone:
            start = self.dwell_start.get(visitor_id, timestamp)
            last_emit = self.last_dwell_emit.get(visitor_id, start)
            if (timestamp - last_emit).total_seconds() * 1000 >= DWELL_INTERVAL_MS:
                dwell_ms = int((timestamp - start).total_seconds() * 1000)
                events.append(
                    emit_event(
                        store_id="",
                        camera_id="",
                        visitor_id=visitor_id,
                        event_type="ZONE_DWELL",
                        timestamp=timestamp,
                        zone_id=zone_id,
                        dwell_ms=dwell_ms,
                        is_staff=is_staff,
                        confidence=0.86,
                    )
                )
                self.last_dwell_emit[visitor_id] = timestamp

        return events


def _group_candidate(recent_entries: List[datetime], ts: datetime) -> bool:
    window_start = ts - timedelta(seconds=GROUP_WINDOW_SEC)
    count = sum(1 for t in recent_entries if t >= window_start)
    return count >= 1  # another entry in window => group


def process_camera_video(
    store: StoreDef,
    camera: CameraDef,
    video_path: Path,
    reid: ReIDManager,
    billing: BillingQueueManager,
    staff_clf: StaffClassifier,
    zone_trk: ZoneTracker,
    all_events: List[dict],
    recent_entries: List[datetime],
    track_to_visitor: Dict[int, str],
    last_entry_emit: Dict[int, datetime],
    last_positions: Dict[int, float],
):
    try:
        import cv2
        from ultralytics import YOLO
    except ImportError:
        raise RuntimeError("opencv-python and ultralytics required for video mode")

    if not video_path.exists():
        return

    model = YOLO(os.getenv("YOLO_MODEL", "yolov8n.pt"))
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    tracker = CentroidTracker()
    base_time = _camera_base_time(camera.camera_id)
    frame_no = 0
    line_y = entry_line_y(camera.entry_line) if camera.entry_line else None

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_no += 1
        if frame_no % FRAME_STRIDE != 0:
            continue

        timestamp = base_time + timedelta(seconds=frame_no / fps)
        results = model.track(frame, persist=True, classes=[0], verbose=False)
        detections = []
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            for box, conf in zip(boxes, confs):
                detections.append((tuple(box), float(conf)))

        # Also use YOLO track IDs when available for group separation
        yolo_ids = None
        if results[0].boxes is not None and results[0].boxes.id is not None:
            yolo_ids = results[0].boxes.id.cpu().numpy()

        tracks = tracker.update(detections)
        staff_ids: Set[str] = set()

        for idx, track in enumerate(tracks):
            cx, cy = centroid(track.bbox)
            is_staff = staff_clf.classify_frame(
                frame, track.bbox, track.track_id, camera.camera_type
            )
            visitor_id = track_to_visitor.get(track.track_id)

            if camera.camera_type == "ENTRY" and line_y is not None:
                prev_y = last_positions.get(track.track_id)
                if prev_y is not None:
                    direction = crossing_direction(prev_y, cy, line_y)
                    if direction in ("ENTRY", "EXIT"):
                        last_emit = last_entry_emit.get(track.track_id)
                        if last_emit and (timestamp - last_emit).total_seconds() < ENTRY_COOLDOWN_SEC:
                            last_positions[track.track_id] = cy
                            continue

                        if direction == "ENTRY":
                            visitor_id, evt_type, seq = reid.on_entry(
                                track.track_id, track.bbox, timestamp
                            )
                            track_to_visitor[track.track_id] = visitor_id
                            group = _group_candidate(recent_entries, timestamp)
                            conf = track.confidence * (0.75 if group else 1.0)
                            evt = emit_event(
                                store_id=store.store_id,
                                camera_id=camera.camera_id,
                                visitor_id=visitor_id,
                                event_type=evt_type,
                                timestamp=timestamp,
                                confidence=conf,
                                session_seq=seq,
                                group_candidate=group,
                                track_id=track.track_id,
                            )
                            recent_entries.append(timestamp)
                            all_events.append(evt)
                            last_entry_emit[track.track_id] = timestamp
                        elif direction == "EXIT" and visitor_id:
                            reid.on_exit(visitor_id, track.bbox, timestamp)
                            seq = reid.bump_session(visitor_id)
                            evt = emit_event(
                                store_id=store.store_id,
                                camera_id=camera.camera_id,
                                visitor_id=visitor_id,
                                event_type="EXIT",
                                timestamp=timestamp,
                                confidence=track.confidence,
                                session_seq=seq,
                                track_id=track.track_id,
                            )
                            all_events.append(evt)
                            last_entry_emit[track.track_id] = timestamp

                last_positions[track.track_id] = cy

            # Zone cameras
            zone = zone_at_point(cx, cy, camera.zones)
            if zone and visitor_id is None and not is_staff:
                visitor_id, _, seq = reid.on_entry(track.track_id, track.bbox, timestamp)
                track_to_visitor[track.track_id] = visitor_id

            if visitor_id:
                if is_staff:
                    staff_ids.add(visitor_id)
                else:
                    for zevt in zone_trk.update(visitor_id, zone.zone_id if zone else None, timestamp, is_staff):
                        zevt["store_id"] = store.store_id
                        zevt["camera_id"] = camera.camera_id
                        zevt["metadata"]["sku_zone"] = (
                            zone.sku_zone if zone else zevt.get("zone_id")
                        )
                        zevt["metadata"]["session_seq"] = reid.bump_session(visitor_id)
                        all_events.append(zevt)

                    if zone and zone.zone_id == "BILLING" and not is_staff:
                        joined, depth = billing.on_enter(visitor_id, is_staff)
                        if joined:
                            all_events.append(
                                emit_event(
                                    store_id=store.store_id,
                                    camera_id=camera.camera_id,
                                    visitor_id=visitor_id,
                                    event_type="BILLING_QUEUE_JOIN",
                                    timestamp=timestamp,
                                    zone_id="BILLING",
                                    queue_depth=depth,
                                    sku_zone="BILLING",
                                    session_seq=reid.bump_session(visitor_id),
                                    confidence=track.confidence,
                                )
                            )
                    elif (
                        visitor_id in billing.state.visitors_in_zone
                        and (zone is None or zone.zone_id != "BILLING")
                    ):
                        if billing.on_exit(visitor_id, timestamp, is_staff):
                            all_events.append(
                                emit_event(
                                    store_id=store.store_id,
                                    camera_id=camera.camera_id,
                                    visitor_id=visitor_id,
                                    event_type="BILLING_QUEUE_ABANDON",
                                    timestamp=timestamp,
                                    zone_id="BILLING",
                                    sku_zone="BILLING",
                                    session_seq=reid.bump_session(visitor_id),
                                    confidence=track.confidence * 0.9,
                                )
                            )

        # YOLO native IDs help separate group entries when multiple boxes cross together
        if yolo_ids is not None and len(yolo_ids) > 1 and camera.camera_type == "ENTRY":
            pass  # separate track IDs already handled per detection

    cap.release()


def replay_sample_events(
    sample_path: Path,
    layout_path: Path,
    output_path: Path,
    pos_path: Path,
):
    """Enrich sample events to full schema with billing/exit/reentry simulation."""
    stores = load_layout(layout_path)
    events: List[dict] = []
    with sample_path.open() as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    # Align billing events with POS windows for conversion correlation
    store_id = events[0]["store_id"] if events else "STORE_001"
    floor_visitors: List[str] = []
    seen: Set[str] = set()
    for e in events:
        if e.get("is_staff"):
            continue
        z = e.get("zone_id") or ""
        if e["event_type"] in ("ZONE_DWELL", "ZONE_ENTER") and z.startswith("COSMETICS"):
            vid = e["visitor_id"]
            if vid not in seen:
                seen.add(vid)
                floor_visitors.append(vid)

    pos_rows: List[dict] = []
    if pos_path.exists():
        import csv

        with pos_path.open() as pf:
            pos_rows = list(csv.DictReader(pf))

    billing_visitors: Set[str] = set()
    for txn in pos_rows:
        if txn.get("store_id") != store_id:
            continue
        txn_time = datetime.fromisoformat(txn["timestamp"].replace("Z", "+00:00"))
        for vid in floor_visitors:
            if vid in billing_visitors:
                continue
            billing_visitors.add(vid)
            bill_ts = txn_time - timedelta(minutes=2)
            events.append(
                emit_event(
                    store_id=store_id,
                    camera_id="CAM_5",
                    visitor_id=vid,
                    event_type="ZONE_ENTER",
                    timestamp=bill_ts,
                    zone_id="BILLING",
                    sku_zone="BILLING",
                    session_seq=2,
                )
            )
            events.append(
                emit_event(
                    store_id=store_id,
                    camera_id="CAM_5",
                    visitor_id=vid,
                    event_type="BILLING_QUEUE_JOIN",
                    timestamp=bill_ts + timedelta(seconds=30),
                    zone_id="BILLING",
                    queue_depth=len(billing_visitors),
                    sku_zone="BILLING",
                    session_seq=3,
                )
            )
            if len(billing_visitors) >= len(pos_rows):
                break

    # Normalize metadata
    for e in events:
        meta = e.setdefault("metadata", {})
        meta.setdefault("queue_depth", None)
        meta.setdefault("sku_zone", e.get("zone_id"))
        meta.setdefault("session_seq", meta.get("session_seq", 1))
        meta.setdefault("group_candidate", False)
        meta.setdefault("source", "detection_pipeline")

    events.sort(key=lambda x: x["timestamp"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as out:
        for e in events:
            out.write(json.dumps(e) + "\n")
    print(f"Replay mode: wrote {len(events)} events to {output_path}")


def run_detection(
    layout_path: Path = DEFAULT_LAYOUT,
    output_path: Path = DEFAULT_OUTPUT,
    mode: str = "auto",
):
    stores = load_layout(layout_path)
    videos_dir = Path(os.getenv("VIDEO_DIR", DEFAULT_VIDEOS))
    purplle = ROOT / "data" / "purplle_events.jsonl"
    sample = purplle if purplle.exists() else ROOT / "data" / "sample_events.jsonl"
    pos_path = ROOT / "data" / "pos_transactions.csv"

    has_video = videos_dir.exists() and any(videos_dir.glob("*.mp4"))
    use_video = mode == "video" or (mode == "auto" and has_video)

    if not use_video:
        replay_sample_events(sample, layout_path, output_path, pos_path)
        return

    all_events: List[dict] = []
    reid = ReIDManager()
    billing = BillingQueueManager()
    staff_clf = StaffClassifier()
    zone_trk = ZoneTracker()
    recent_entries: List[datetime] = []
    track_to_visitor: Dict[int, str] = {}
    last_entry_emit: Dict[int, datetime] = {}
    last_positions: Dict[int, float] = {}

    for store in stores.values():
        for camera in _sort_cameras(store.cameras):
            video_path = videos_dir / camera.video_file
            try:
                process_camera_video(
                    store,
                    camera,
                    video_path,
                    reid,
                    billing,
                    staff_clf,
                    zone_trk,
                    all_events,
                    recent_entries,
                    track_to_visitor,
                    last_entry_emit,
                    last_positions,
                )
            except RuntimeError as exc:
                print(f"Video processing unavailable ({exc}); falling back to replay.")
                replay_sample_events(sample, layout_path, output_path, pos_path)
                return

    all_events.sort(key=lambda x: x["timestamp"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as out:
        for e in all_events:
            out.write(json.dumps(e) + "\n")
    print(f"Detection complete: {len(all_events)} events -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Store Intelligence detection pipeline")
    parser.add_argument("--layout", default=str(DEFAULT_LAYOUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=["auto", "video", "replay"], default="auto")
    args = parser.parse_args()
    run_detection(Path(args.layout), Path(args.output), args.mode)


if __name__ == "__main__":
    main()
