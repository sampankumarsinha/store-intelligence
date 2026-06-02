"""Re-entry detection using trajectory and appearance proxies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

BBox = Tuple[float, float, float, float]


@dataclass
class VisitorProfile:
    visitor_id: str
    last_exit_at: Optional[datetime] = None
    last_bbox: Optional[BBox] = None
    last_centroid: Optional[Tuple[float, float]] = None
    session_seq: int = 0
    active: bool = True


class ReIDManager:
    def __init__(self, reentry_window_seconds: int = 600):
        self.reentry_window = timedelta(seconds=reentry_window_seconds)
        self._profiles: Dict[str, VisitorProfile] = {}
        self._counter = 0

    def _new_visitor_id(self) -> str:
        self._counter += 1
        return f"VIS_{self._counter:06d}"

    @staticmethod
    def _bbox_area(bbox: BBox) -> float:
        x1, y1, x2, y2 = bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @staticmethod
    def _centroid(bbox: BBox) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return (x1 + x2) / 2, (y1 + y2) / 2

    def _similarity(
        self,
        profile: VisitorProfile,
        bbox: BBox,
        centroid: Tuple[float, float],
    ) -> float:
        if profile.last_bbox is None or profile.last_centroid is None:
            return 0.0
        area_ratio = min(
            self._bbox_area(bbox), self._bbox_area(profile.last_bbox)
        ) / max(self._bbox_area(bbox), self._bbox_area(profile.last_bbox), 1.0)
        dx = centroid[0] - profile.last_centroid[0]
        dy = centroid[1] - profile.last_centroid[1]
        dist = (dx * dx + dy * dy) ** 0.5
        dist_score = max(0.0, 1.0 - dist / 400.0)
        return 0.5 * area_ratio + 0.5 * dist_score

    def on_entry(
        self,
        track_id: int,
        bbox: BBox,
        timestamp: datetime,
    ) -> Tuple[str, str, int]:
        """
        Returns (visitor_id, event_type, session_seq).
        event_type is ENTRY or REENTRY.
        """
        centroid = self._centroid(bbox)
        best_profile: Optional[VisitorProfile] = None
        best_score = 0.55

        for profile in self._profiles.values():
            if profile.active or profile.last_exit_at is None:
                continue
            gap = timestamp - profile.last_exit_at
            if gap > self.reentry_window or gap.total_seconds() < 0:
                continue
            score = self._similarity(profile, bbox, centroid)
            if score >= best_score and score > (
                self._similarity(best_profile, bbox, centroid) if best_profile else 0
            ):
                best_profile = profile
                best_score = score

        if best_profile is not None:
            best_profile.active = True
            best_profile.session_seq += 1
            best_profile.last_bbox = bbox
            best_profile.last_centroid = centroid
            return best_profile.visitor_id, "REENTRY", best_profile.session_seq

        visitor_id = self._new_visitor_id()
        profile = VisitorProfile(visitor_id=visitor_id, session_seq=1, active=True)
        profile.last_bbox = bbox
        profile.last_centroid = centroid
        self._profiles[visitor_id] = profile
        return visitor_id, "ENTRY", 1

    def on_exit(self, visitor_id: str, bbox: BBox, timestamp: datetime):
        profile = self._profiles.get(visitor_id)
        if not profile:
            return
        profile.active = False
        profile.last_exit_at = timestamp
        profile.last_bbox = bbox
        profile.last_centroid = self._centroid(bbox)
        profile.session_seq += 1

    def bump_session(self, visitor_id: str) -> int:
        profile = self._profiles.get(visitor_id)
        if not profile:
            return 1
        profile.session_seq += 1
        return profile.session_seq
