"""
src/algorithms/astar.py
────────────────────────
Emergency Navigation — A* Search Algorithm.
Single Responsibility: heuristic-guided pathfinding only.
No print(). No CLI. No formatting.

Formula:  f(n) = g(n) + h(n)
  g(n): Actual travel time from start → n, via WeightEngine.get_edge_weight() (BPR).
  h(n): Euclidean distance heuristic → dist_km / 60.0
        (admissible: 60 km/h > actual free-flow 38 km/h, so h never overestimates).

Admissibility proof:
  Actual edge weight = (d / 38.0) × BPR_factor ≥ d / 38.0 > d / 60.0 = h(n)
  ∴ h(n) ≤ true_cost  →  A* finds the optimal path.  ✅
"""
from __future__ import annotations

import heapq
import math
from typing import List, Optional

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.models.responses import RouteResult

_HEURISTIC_MAX_SPEED_KMH: float = 60.0


class AStarRouter:
    """
    Heuristic-guided shortest-path engine using the A* algorithm.

    Compared to DijkstraRouter, A* focuses exploration toward the goal
    using geographic coordinates, significantly reducing the number of
    nodes expanded — especially useful for hospital routing where the
    destination has a clear geographic direction.
    """

    DEFAULT_EDGE_TYPES = ['existing_road', 'potential_road', 'bus', 'metro']

    def __init__(self, graph: Graph, edge_types: Optional[List[str]] = None):
        if not isinstance(graph, Graph):
            raise TypeError(f"AStarRouter requires a Graph instance, got {type(graph)}")
        self.graph      = graph
        self.edge_types = edge_types
        self._we = WeightEngine(graph.weight_cache)

    def find_shortest_path(
        self,
        start_node_id: str,
        end_node_id:   str,
        time_of_day:   str = 'morning',
    ) -> RouteResult:
        """Find the fastest path using A* with Euclidean distance heuristic."""
        result = self._validate_inputs(start_node_id, end_node_id, time_of_day)
        if result is not None:
            return result

        src = self.graph.sid(start_node_id)
        dst = self.graph.sid(end_node_id)
        tod = WeightEngine.normalize_time_of_day(time_of_day)

        if src == dst:
            return RouteResult(path=[src], total_time_h=0.0, total_time_min=0.0,
                               total_dist_km=0.0, iterations=0, time_of_day=tod,
                               edge_types_used=[], hops=0, found=True, segments=[])

        g_score: dict[str, float] = {nid: math.inf for nid in self.graph.nodes}
        g_score[src] = 0.0

        f_score: dict[str, float] = {nid: math.inf for nid in self.graph.nodes}
        f_score[src] = self._heuristic(src, dst)

        predecessor: dict[str, tuple | None] = {nid: None for nid in self.graph.nodes}

        heap    = [(f_score[src], 0, src)]
        counter = 0
        visited: set[str] = set()
        iterations = 0

        while heap:
            f, _, current = heapq.heappop(heap)
            iterations += 1

            if current in visited:
                continue
            visited.add(current)

            if current == dst:
                break

            if f > f_score[current]:
                continue

            for neighbor_id, edge in self.graph.adj_list.get(current, []):
                if self.edge_types is not None and edge.edge_type not in self.edge_types:
                    continue
                if neighbor_id not in self.graph.nodes:
                    continue

                tentative_g = g_score[current] + self._we.get_edge_weight(edge, tod)

                if tentative_g < g_score[neighbor_id]:
                    g_score[neighbor_id]    = tentative_g
                    f_score[neighbor_id]    = tentative_g + self._heuristic(neighbor_id, dst)
                    predecessor[neighbor_id] = (current, edge)
                    counter += 1
                    heapq.heappush(heap, (f_score[neighbor_id], counter, neighbor_id))

        if g_score[dst] == math.inf:
            return RouteResult(
                found=False, iterations=iterations, time_of_day=tod,
                error=(f"No path from '{src}' to '{dst}' using "
                       f"{self.edge_types or self.DEFAULT_EDGE_TYPES}."),
            )

        path, segments, types_used = self._reconstruct_path(src, dst, predecessor, tod)
        return RouteResult(
            path=path, total_time_h=g_score[dst], total_time_min=g_score[dst] * 60.0,
            total_dist_km=sum(s['dist_km'] for s in segments),
            iterations=iterations, time_of_day=tod, edge_types_used=types_used,
            hops=len(segments), found=True, segments=segments,
        )

    def compare_times(self, start_node_id: str, end_node_id: str,
                      periods: list | None = None) -> dict[str, RouteResult]:
        """Run all 4 time periods and return comparative results."""
        if periods is None:
            periods = list(WeightEngine.VALID_TIME_OF_DAY)
        return {p: self.find_shortest_path(start_node_id, end_node_id, p) for p in periods}

    def _heuristic(self, node_a_id: str, node_b_id: str) -> float:
        """Admissible Euclidean distance heuristic (dist_km / 60 km/h)."""
        na = self.graph.nodes.get(node_a_id)
        nb = self.graph.nodes.get(node_b_id)
        if not na or not nb:
            return 0.0
        dx = (na.x - nb.x) * 96.0
        dy = (na.y - nb.y) * 111.0
        return math.sqrt(dx * dx + dy * dy) / _HEURISTIC_MAX_SPEED_KMH

    def _validate_inputs(self, start_node_id, end_node_id, time_of_day):
        src = self.graph.sid(start_node_id)
        dst = self.graph.sid(end_node_id)
        if src not in self.graph.nodes:
            return RouteResult(found=False, error=f"Start node '{src}' not found.")
        if dst not in self.graph.nodes:
            return RouteResult(found=False, error=f"End node '{dst}' not found.")
        try:
            WeightEngine.normalize_time_of_day(time_of_day)
        except ValueError as e:
            return RouteResult(found=False, error=str(e))
        return None

    def _reconstruct_path(self, src, dst, predecessor, tod):
        path_rev, segs_rev, types = [], [], []
        current = dst
        while current != src:
            parent_node, edge = predecessor[current]
            path_rev.append(current)
            w = self._we.get_edge_weight(edge, tod)
            segs_rev.append({'from': parent_node, 'to': current, 'type': edge.edge_type,
                             'dist_km': edge.distance_km or 0.0, 'time_h': w})
            types.append(edge.edge_type)
            current = parent_node
        path_rev.append(src)
        return list(reversed(path_rev)), list(reversed(segs_rev)), list(reversed(types))
