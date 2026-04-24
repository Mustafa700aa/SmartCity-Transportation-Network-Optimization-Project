"""
src/core/weight_engine.py
Business logic: BPR travel-time formula and time-of-day management.
Single Responsibility: compute and cache edge weights only.

Design note: WeightEngine holds a *reference* to Graph.weight_cache (the same
dict object, not a copy). When Graph.add_edge() calls weight_cache.clear(),
this engine's view is automatically invalidated — no extra wiring needed.
"""
from __future__ import annotations
from src.models.entities import Edge


class WeightEngine:

    VALID_TIME_OF_DAY = ('morning', 'afternoon', 'evening', 'night')
    TIME_OF_DAY_ALIASES = {
        'morning':      'morning',
        'morning peak': 'morning',
        'am peak':      'morning',
        'afternoon':    'afternoon',
        'evening':      'evening',
        'evening peak': 'evening',
        'pm peak':      'evening',
        'night':        'night',
    }

    def __init__(self, weight_cache: dict):
        # Shared reference to Graph.weight_cache — same object, not a copy.
        self._cache = weight_cache

    # ── Time normalization ────────────────────────────────────────────────────
    @classmethod
    def normalize_time_of_day(cls, time_of_day: str) -> str:
        key = ' '.join(
            str(time_of_day).strip().lower()
            .replace('_', ' ').replace('-', ' ').split()
        )
        t = cls.TIME_OF_DAY_ALIASES.get(key)
        if t is None:
            raise ValueError(
                f"Invalid time_of_day '{time_of_day}'. "
                f"Expected one of: {', '.join(cls.VALID_TIME_OF_DAY)}"
            )
        return t

    # ── Weight calculation (BPR) ──────────────────────────────────────────────
    def get_edge_weight(self, edge: Edge, time_of_day: str = 'morning') -> float:
        t, d = self.normalize_time_of_day(time_of_day), edge.distance_km or 1.0
        cache_key = (
            edge.from_id, edge.to_id, edge.edge_type, t, d,
            edge.capacity, edge.condition, edge.construction_cost,
            edge.daily_passengers, edge.buses_assigned,
            edge.traffic_flow.get(t),
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if edge.edge_type == 'existing_road':
            traffic, cap, cond = edge.traffic_flow.get(t), edge.capacity or 2500.0, edge.condition or 7.0
            ratio = max(0.0, (traffic or 0.0) / cap) if cap else 0.0
            # BPR travel-time model: T = T0 * (1 + alpha * (V/C)^beta).
            alpha, beta = 0.15, 4.0
            bpr_factor  = 1.0 + alpha * (ratio ** beta)
            cond_factor = 1.0 + max(0.0, 7.0 - cond) * 0.02
            value = (d / 38.0) * bpr_factor * cond_factor
        elif edge.edge_type == 'potential_road':
            value = d / 42.0
        elif edge.edge_type == 'bus':
            p, buses = edge.daily_passengers or 0.0, edge.buses_assigned
            value = (d / 24.0) * (1.0 + min(1.2, p / 100000.0)) * (
                max(0.65, 1.15 - min(buses, 40) * 0.012) if buses else 1.0
            )
        elif edge.edge_type == 'metro':
            value = (d / 45.0) * (1.0 + min(0.6, (edge.daily_passengers or 0.0) / 3000000.0))
        else:
            value = d / 30.0

        self._cache[cache_key] = value
        return value
