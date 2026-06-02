"""Billing queue depth and abandonment logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Set


@dataclass
class BillingState:
    visitors_in_zone: Set[str] = field(default_factory=set)
    joined_queue: Set[str] = field(default_factory=set)
    left_at: Dict[str, datetime] = field(default_factory=dict)


class BillingQueueManager:
    def __init__(self, abandon_window_seconds: int = 300):
        self.abandon_window = timedelta(seconds=abandon_window_seconds)
        self.state = BillingState()

    def queue_depth(self, staff_ids: Set[str]) -> int:
        return len(self.state.visitors_in_zone - staff_ids)

    def on_enter(self, visitor_id: str, is_staff: bool) -> tuple[bool, int]:
        if is_staff:
            return False, self.queue_depth(set())
        was_outside = visitor_id not in self.state.visitors_in_zone
        self.state.visitors_in_zone.add(visitor_id)
        depth_before = self.queue_depth(set()) - (1 if was_outside else 0)
        emit_join = was_outside and depth_before > 0
        if emit_join:
            self.state.joined_queue.add(visitor_id)
        return emit_join, max(depth_before, 0)

    def on_exit(
        self,
        visitor_id: str,
        timestamp: datetime,
        is_staff: bool,
    ) -> bool:
        if is_staff:
            self.state.visitors_in_zone.discard(visitor_id)
            return False
        was_inside = visitor_id in self.state.visitors_in_zone
        self.state.visitors_in_zone.discard(visitor_id)
        if was_inside and visitor_id in self.state.joined_queue:
            self.state.left_at[visitor_id] = timestamp
            return True
        return False

    def check_abandonment(
        self,
        visitor_id: str,
        timestamp: datetime,
        converted_visitors: Set[str],
    ) -> bool:
        left = self.state.left_at.get(visitor_id)
        if left is None:
            return False
        if visitor_id in converted_visitors:
            del self.state.left_at[visitor_id]
            return False
        if timestamp - left >= self.abandon_window:
            del self.state.left_at[visitor_id]
            self.state.joined_queue.discard(visitor_id)
            return True
        return False
