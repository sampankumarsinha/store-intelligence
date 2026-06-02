"""Simple centroid + IoU multi-object tracker (ByteTrack-style fallback)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

BBox = Tuple[float, float, float, float]


def iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0.0, inter_x2 - inter_x1)
    ih = max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def centroid(box: BBox) -> Tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


@dataclass
class Track:
    track_id: int
    bbox: BBox
    confidence: float
    missed: int = 0
    history: List[Tuple[float, float]] = field(default_factory=list)

    def update(self, bbox: BBox, confidence: float):
        self.bbox = bbox
        self.confidence = confidence
        self.missed = 0
        cx, cy = centroid(bbox)
        self.history.append((cx, cy))
        if len(self.history) > 30:
            self.history.pop(0)


class CentroidTracker:
    def __init__(self, iou_threshold: float = 0.3, max_missed: int = 15):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self._next_id = 1
        self.tracks: Dict[int, Track] = {}

    def update(self, detections: List[Tuple[BBox, float]]) -> List[Track]:
        matched: set[int] = set()
        updated: List[Track] = []

        for bbox, conf in detections:
            best_id = None
            best_iou = self.iou_threshold
            for tid, track in self.tracks.items():
                if tid in matched:
                    continue
                score = iou(bbox, track.bbox)
                if score >= best_iou:
                    best_iou = score
                    best_id = tid

            if best_id is not None:
                self.tracks[best_id].update(bbox, conf)
                matched.add(best_id)
                updated.append(self.tracks[best_id])
            else:
                tid = self._next_id
                self._next_id += 1
                track = Track(track_id=tid, bbox=bbox, confidence=conf)
                cx, cy = centroid(bbox)
                track.history.append((cx, cy))
                self.tracks[tid] = track
                updated.append(track)

        for tid in list(self.tracks.keys()):
            if tid not in matched:
                self.tracks[tid].missed += 1
                if self.tracks[tid].missed > self.max_missed:
                    del self.tracks[tid]

        return updated
