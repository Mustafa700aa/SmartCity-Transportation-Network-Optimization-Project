from __future__ import annotations

from typing import List, Optional

from src.core.graph import Graph
from src.models.responses import RouteResult, PreemptionEvent, PreemptionLog

_CONGESTION_THRESHOLDS = {
    'FREE':     (0,     500),
    'LIGHT':    (500,   1200),
    'MODERATE': (1200,  2000),
    'HEAVY':    (2000,  3000),
    'GRIDLOCK': (3000,  float('inf')),
}

# Estimated seconds saved by forcing green at each congestion level
_DELAY_SAVED_SEC = {
    'FREE':     5,
    'LIGHT':    15,
    'MODERATE': 40,
    'HEAVY':    90,
    'GRIDLOCK': 150,
}

class GreedyPreemptionSystem:

    def __init__(self, graph: Graph):
        if not isinstance(graph, Graph):
            raise TypeError(
                f"GreedyPreemptionSystem requires a Graph instance, got {type(graph)}"
            )
        self._graph = graph

    def generate_preemption_log(
        self,
        route_result: RouteResult,
        time_of_day: Optional[str] = None,
    ) -> PreemptionLog:
        warnings: List[str] = []

        if not route_result.found or not route_result.path:
            return PreemptionLog(
                route_path=[], time_of_day='unknown', total_nodes=0,
                overrides_applied=0, total_delay_saved_sec=0,
                fully_cleared=False,
                warnings=['Route not found — preemption aborted.'],
            )

        tod = time_of_day or route_result.time_of_day or 'morning'
        path: List[str] = route_result.path
        segments = route_result.segments or []

        # Build a quick lookup: node_id → (edge_type_in, edge_type_out)
        edge_in_map, edge_out_map = self._build_edge_maps(path, segments)

        events: List[PreemptionEvent] = []
        cumulative_saved = 0

        for step, node_id in enumerate(path, start=1):
            node = self._graph.nodes.get(node_id)
            if node is None:
                warnings.append(f"Node '{node_id}' not found in graph — skipped.")
                continue

            # Assess local congestion (greedy input)
            traffic_vol = self._get_traffic_volume(node_id, tod, path, step)
            congestion  = self._classify_congestion(traffic_vol)
            delay_saved = _DELAY_SAVED_SEC[congestion]
            cumulative_saved += delay_saved

            # Determine position note
            if step == 1:
                note = 'ORIGIN — ambulance departs'
            elif step == len(path):
                note = 'DESTINATION — ambulance arrives'
            else:
                note = f'Intersection {step} of {len(path)}'

            event = PreemptionEvent(
                step=step,
                node_id=node_id,
                node_name=node.name,
                node_type=node.type,
                signal_forced='GREEN',
                congestion_level=congestion,
                traffic_volume=traffic_vol,
                delay_saved_sec=delay_saved,
                edge_type_in=edge_in_map.get(node_id),
                edge_type_out=edge_out_map.get(node_id),
                cumulative_saved_sec=cumulative_saved,
                note=note,
            )
            events.append(event)

        overrides = len(events)
        return PreemptionLog(
            route_path=path,
            time_of_day=tod,
            total_nodes=len(path),
            overrides_applied=overrides,
            total_delay_saved_sec=cumulative_saved,
            fully_cleared=(overrides == len(path)),
            events=events,
            warnings=warnings,
        )

    def _build_edge_maps(
        self,
        path: List[str],
        segments: list,
    ) -> tuple[dict[str, str], dict[str, str]]:
        edge_in:  dict[str, str] = {}
        edge_out: dict[str, str] = {}

        for seg in segments:
            from_id    = seg.get('from', '')
            to_id      = seg.get('to',   '')
            edge_type  = seg.get('type', 'unknown')
            edge_out[from_id] = edge_type
            edge_in[to_id]    = edge_type

        return edge_in, edge_out

    def _get_traffic_volume(
        self,
        node_id: str,
        tod: str,
        path: List[str],
        step: int,
    ) -> float:
        # Try traffic data for edges connecting this node to its path neighbours
        total, count = 0.0, 0

        neighbours_in_path: List[str] = []
        if step > 1:
            neighbours_in_path.append(path[step - 2])
        if step < len(path):
            neighbours_in_path.append(path[step])

        for neighbour in neighbours_in_path:
            key = self._graph.ek(node_id, neighbour)
            flow_dict = self._graph.traffic.get(key)
            if flow_dict:
                vol = flow_dict.get(tod) or flow_dict.get('morning') or 0.0
                total += vol
                count += 1

        if count:
            return total / count

        # Fallback: scan all edges adjacent to the node in the adj_list
        for _, edge in self._graph.adj_list.get(node_id, []):
            flow_dict = edge.traffic_flow
            if flow_dict:
                vol = flow_dict.get(tod) or flow_dict.get('morning') or 0.0
                total += vol
                count += 1

        if count:
            return total / count

        for _, edge in self._graph.adj_list.get(node_id, []):
            if edge.edge_type in ('bus', 'metro') and edge.daily_passengers:
                hourly_equiv = edge.daily_passengers / 16.0 / 30.0
                total += hourly_equiv
                count += 1

        # Minimum 800 veh/h for transit-connected intersections (LIGHT).
        return (total / count) if count else 800.0

    @staticmethod
    def _classify_congestion(volume: float) -> str:
        for level, (lo, hi) in _CONGESTION_THRESHOLDS.items():
            if lo <= volume < hi:
                return level
        return 'GRIDLOCK'
