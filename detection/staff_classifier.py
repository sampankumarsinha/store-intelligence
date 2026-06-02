"""Staff detection via uniform color heuristic and staff-only zones."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

BBox = Tuple[float, float, float, float]


class StaffClassifier:
    """
    Heuristic staff detector:
    - Dark uniform (low saturation, low brightness variance) in upper body crop
    - Frequent presence in WAREHOUSE / staff-tagged camera types
    """

    def __init__(self, staff_camera_types: Optional[set] = None):
        self.staff_camera_types = staff_camera_types or {"STAFF", "WAREHOUSE"}
        self._track_staff_votes: dict[int, int] = {}

    def classify_frame(
        self,
        frame: np.ndarray,
        bbox: BBox,
        track_id: int,
        camera_type: str,
    ) -> bool:
        if camera_type.upper() in self.staff_camera_types:
            return True

        x1, y1, x2, y2 = map(int, bbox)
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return self._track_staff_votes.get(track_id, 0) >= 3

        crop = frame[y1 : y1 + int((y2 - y1) * 0.45), x1:x2]
        if crop.size == 0:
            return False

        hsv = self._rgb_to_hsv(crop)
        sat = hsv[:, :, 1].mean()
        val = hsv[:, :, 2].mean()
        # Dark retail uniform heuristic
        uniform_like = val < 90 and sat < 80

        votes = self._track_staff_votes.get(track_id, 0)
        if uniform_like:
            votes += 1
        else:
            votes = max(0, votes - 1)
        self._track_staff_votes[track_id] = votes
        return votes >= 3

    @staticmethod
    def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
        rgb_f = rgb.astype(np.float32) / 255.0
        r, g, b = rgb_f[:, :, 0], rgb_f[:, :, 1], rgb_f[:, :, 2]
        cmax = np.maximum(np.maximum(r, g), b)
        cmin = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin
        h = np.zeros_like(cmax)
        s = np.where(cmax > 0, delta / cmax, 0.0)
        v = cmax
        hsv = np.stack([h, s * 255, v * 255], axis=2)
        return hsv
