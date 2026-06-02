"""Zone and entry-line helpers loaded from store_layout.json."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

Point = Tuple[float, float]


@dataclass
class ZoneDef:
    zone_id: str
    polygon: List[Point]
    sku_zone: Optional[str] = None


@dataclass
class CameraDef:
    camera_id: str
    video_file: str
    camera_type: str
    entry_line: Optional[List[Point]] = None
    zones: List[ZoneDef] = None

    def __post_init__(self):
        if self.zones is None:
            self.zones = []


@dataclass
class StoreDef:
    store_id: str
    cameras: List[CameraDef]


def _point_in_polygon(x: float, y: float, polygon: List[Point]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
            inside = not inside
        j = i
    return inside


def load_layout(path: str | Path) -> Dict[str, StoreDef]:
    raw = json.loads(Path(path).read_text())
    stores: Dict[str, StoreDef] = {}
    for store in raw.get("stores", []):
        cameras = []
        for cam in store.get("cameras", []):
            zones = [
                ZoneDef(
                    zone_id=z["zone_id"],
                    polygon=[(p[0], p[1]) for p in z["polygon"]],
                    sku_zone=z.get("sku_zone", z["zone_id"]),
                )
                for z in cam.get("zones", [])
            ]
            entry_line = None
            if cam.get("entry_line"):
                entry_line = [(p[0], p[1]) for p in cam["entry_line"]]
            cameras.append(
                CameraDef(
                    camera_id=cam["camera_id"],
                    video_file=cam["video_file"],
                    camera_type=cam.get("type", "FLOOR"),
                    entry_line=entry_line,
                    zones=zones,
                )
            )
        stores[store["store_id"]] = StoreDef(store_id=store["store_id"], cameras=cameras)
    return stores


def entry_line_y(entry_line: List[Point]) -> float:
    """Average Y of entry line (horizontal line assumption)."""
    return sum(p[1] for p in entry_line) / len(entry_line)


def zone_at_point(x: float, y: float, zones: List[ZoneDef]) -> Optional[ZoneDef]:
    for zone in zones:
        if _point_in_polygon(x, y, zone.polygon):
            return zone
    return None


def crossing_direction(prev_y: float, curr_y: float, line_y: float) -> Optional[str]:
    """
    Return ENTRY when crossing from above line to below (inbound),
    EXIT when crossing from below to above (outbound).
    Image coords: Y increases downward — 'outside' is smaller Y.
    """
    if prev_y < line_y <= curr_y:
        return "ENTRY"
    if prev_y > line_y >= curr_y:
        return "EXIT"
    return None
