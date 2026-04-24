"""
src/models/responses.py
────────────────────────
Pure data containers for algorithm output.
Single Responsibility: hold result data fields only. No formatting, no I/O.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.models.entities import Edge


@dataclass
class RouteResult:
    """
    Structured result returned by DijkstraRouter.find_shortest_path().
    Pure data class — no display or formatting logic.
    """
    path:            List[str]     = field(default_factory=list)
    total_time_h:    float         = math.inf
    total_time_min:  float         = math.inf
    total_dist_km:   float         = 0.0
    iterations:      int           = 0
    time_of_day:     str           = 'morning'
    edge_types_used: List[str]     = field(default_factory=list)
    hops:            int           = 0
    found:           bool          = False
    error:           Optional[str] = None
    segments:        List[dict]    = field(default_factory=list)


@dataclass
class MSTResult:
    """
    Structured result returned by kruskal_mst().
    Pure data class — no display or formatting logic.
    """
    mst_edges:         List['Edge'] = field(default_factory=list)
    total_cost:        float        = 0.0
    nodes_covered:     int          = 0
    fully_connected:   bool         = False
    skipped_edges:     List[str]    = field(default_factory=list)
    components_before: int          = 0
    components_after:  int          = 0
