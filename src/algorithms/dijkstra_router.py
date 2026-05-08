from __future__ import annotations

import heapq
import math
from typing import List, Optional

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.models.responses import RouteResult

class DijkstraRouter:

    DEFAULT_EDGE_TYPES = ['existing_road', 'potential_road', 'bus', 'metro']

    def __init__(self, graph: Graph, edge_types: Optional[List[str]] = None,
                 weight_engine: Optional[WeightEngine] = None):
        if not isinstance(graph, Graph):
            raise TypeError(f"DijkstraRouter requires a Graph instance, got {type(graph)}")
        self.graph      = graph
        self.edge_types = edge_types
        self._we = weight_engine or WeightEngine()

    def find_shortest_path(
        self,
        start_node_id: str,
        end_node_id:   str,
        time_of_day:   str = 'morning',
        avoid_edges:   set | None = None,
    ) -> RouteResult:
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

        dist        = {nid: math.inf for nid in self.graph.nodes}
        dist[src]   = 0.0
        predecessor = {nid: None for nid in self.graph.nodes}
        heap        = [(0.0, 0, src)]
        counter     = 0
        visited: set[str] = set()
        iterations  = 0

        while heap:
            current_time, _, current_node = heapq.heappop(heap)
            iterations += 1
            if current_node in visited:
                continue
            visited.add(current_node)
            if current_node == dst:
                break
            if current_time > dist[current_node]:
                continue

            for neighbor_id, edge in self.graph.adj_list.get(current_node, []):
                if self.edge_types is not None and edge.edge_type not in self.edge_types:
                    continue
                if avoid_edges and self.graph.ek(edge.from_id, edge.to_id) in avoid_edges:
                    continue
                if neighbor_id not in self.graph.nodes:
                    continue
                new_time = current_time + self._we.get_edge_weight(edge, tod)
                if new_time < dist[neighbor_id]:
                    dist[neighbor_id]        = new_time
                    predecessor[neighbor_id] = (current_node, edge)
                    counter += 1
                    heapq.heappush(heap, (new_time, counter, neighbor_id))

        if dist[dst] == math.inf:
            return RouteResult(
                found=False, iterations=iterations, time_of_day=tod,
                error=(f"No path from '{src}' to '{dst}' using "
                       f"{self.edge_types or self.DEFAULT_EDGE_TYPES}."),
            )

        path, segments, types_used = self._reconstruct_path(src, dst, predecessor, tod)
        return RouteResult(
            path=path, total_time_h=dist[dst], total_time_min=dist[dst] * 60.0,
            total_dist_km=sum(s['dist_km'] for s in segments),
            iterations=iterations, time_of_day=tod, edge_types_used=types_used,
            hops=len(segments), found=True, segments=segments,
        )

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

    def compare_times(self, start_node_id, end_node_id, periods=None):
        if periods is None:
            periods = list(WeightEngine.VALID_TIME_OF_DAY)
        return {p: self.find_shortest_path(start_node_id, end_node_id, p) for p in periods}
