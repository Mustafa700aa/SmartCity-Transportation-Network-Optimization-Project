from __future__ import annotations

import logging
import math
from typing import List, Optional

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.models.responses import GreenSlot, GreenLightSchedule

_log = logging.getLogger(__name__)

class GreedySignalOptimizer:

    DEFAULT_CYCLE_DURATION = 120   # seconds, typical Cairo intersection
    DEFAULT_MIN_GREEN      = 10   # seconds, prevents starvation floor

    def __init__(self, graph: Graph):
        if not isinstance(graph, Graph):
            raise TypeError(
                f"GreedySignalOptimizer requires a Graph instance, got {type(graph)}"
            )
        self._graph = graph

    def compute_schedule(
        self,
        node_id:        str,
        time_of_day:    str = 'morning',
        cycle_duration: int = 120,
        min_green:      int = 10,
    ) -> GreenLightSchedule:
        nid = self._graph.sid(node_id)

        # Validate time_of_day via project's canonical normalizer
        try:
            tod = WeightEngine.normalize_time_of_day(time_of_day)
        except ValueError:
            _log.warning(
                "Invalid time_of_day '%s' in GreedySignalOptimizer — defaulting to 'morning'.",
                time_of_day,
            )
            tod = 'morning'

        node = self._graph.nodes.get(nid)
        node_name = node.name if node else 'Unknown'

        incoming = self._get_incoming_traffic(nid, tod)

        if not incoming:
            return GreenLightSchedule(
                node_id=nid, node_name=node_name, slots=[],
                total_time=cycle_duration, time_of_day=tod,
                incoming_roads=0,
                analysis="No incoming roads with traffic data detected.",
            )

        k = len(incoming)

        incoming.sort(key=lambda x: x[0], reverse=True)

        total_flow       = sum(flow for flow, _, _, _ in incoming)
        guaranteed_total = min_green * k
        remaining_budget = cycle_duration - guaranteed_total

        slots: List[GreenSlot] = []
        time_accumulator = 0

        for rank, (flow, from_id, from_name, road_id) in enumerate(incoming, start=1):
            if remaining_budget > 0 and total_flow > 0:
                extra = remaining_budget * (flow / total_flow)
            else:
                extra = 0.0

            # Last slot absorbs rounding residual to keep total == cycle_duration
            if rank == k:
                green_time = cycle_duration - time_accumulator
            else:
                green_time = max(min_green, math.floor(min_green + extra))

            time_accumulator += green_time

            slots.append(GreenSlot(
                road_id=road_id,
                from_node=from_id,
                from_name=from_name,
                traffic_flow=flow,
                green_duration=green_time,
                priority_rank=rank,
            ))

        analysis = self._build_analysis(slots, nid, node_name, tod, min_green, k)

        return GreenLightSchedule(
            node_id=nid, node_name=node_name, slots=slots,
            total_time=cycle_duration, time_of_day=tod,
            incoming_roads=k, analysis=analysis,
        )

    def compute_batch(
        self,
        node_ids:       List[str],
        time_of_day:    str = 'morning',
        cycle_duration: int = 120,
        min_green:      int = 10,
    ) -> List[GreenLightSchedule]:
        return [
            self.compute_schedule(nid, time_of_day, cycle_duration, min_green)
            for nid in node_ids
        ]

    def _get_incoming_traffic(
        self, node_id: str, tod: str,
    ) -> List[tuple]:
        result = []
        seen_roads: set = set()

        for neighbor_id, edge in self._graph.adj_list.get(node_id, []):
            # Only existing roads have traffic_flow data
            if edge.edge_type != 'existing_road':
                continue

            # Deduplicate (undirected graph stores A→B and B→A)
            road_key = self._graph.ek(node_id, neighbor_id)
            if road_key in seen_roads:
                continue
            seen_roads.add(road_key)

            # Get traffic flow for this time period (vehicles/hour)
            flow = edge.traffic_flow.get(tod, 0.0) if edge.traffic_flow else 0.0
            if flow <= 0:
                continue

            neighbor_node = self._graph.nodes.get(neighbor_id)
            from_name = neighbor_node.name if neighbor_node else 'Unknown'
            road_id = f"{neighbor_id}-{node_id}"

            result.append((flow, neighbor_id, from_name, road_id))

        return result

    @staticmethod
    def _build_analysis(
        slots:     List[GreenSlot],
        node_id:   str,
        node_name: str,
        tod:       str,
        min_green: int,
        k:         int,
    ) -> str:
        high = slots[0]  if slots else None
        low  = slots[-1] if slots else None
        ratio = (high.traffic_flow / low.traffic_flow) if (
            low and low.traffic_flow > 0) else float("inf")

        header = (
            f"Node '{node_id}' ({node_name}) | period: {tod} | roads: {k}\n"
            f"Highest-priority road: '{high.road_id}' → "
            f"{high.green_duration}s green ({high.traffic_flow:.0f} veh/h)\n"
            f"Lowest-priority road:  '{low.road_id}' → "
            f"{low.green_duration}s green ({low.traffic_flow:.0f} veh/h)\n"
            f"Flow ratio: {ratio:.1f}x | "
            f"Min-green starvation guard: {min_green}s per road"
        ) if (high and low) else f"Node '{node_id}' ({node_name}) — no data"

        optimal = (
            "\nOPTIMAL SCENARIO:\n"
            "  When all incoming roads carry comparably high, uniform flows,\n"
            "  the greedy maximum-first rule aligns with the globally optimal\n"
            "  schedule: clearing the heaviest flow first reduces average queue\n"
            "  length fastest. Formally: when all flows are within a constant\n"
            "  factor c of each other, the greedy schedule is a\n"
            "  (1 + 1/c)-approximation of optimal."
        )

        suboptimal = (
            "\nSUBOPTIMAL SCENARIO:\n"
            f"  The lowest-flow road ({low.road_id}: {low.traffic_flow:.0f} veh/h)\n"
            f"  is dwarfed by the highest ({high.road_id}: "
            f"{high.traffic_flow:.0f} veh/h,\n"
            f"  ratio ≈ {ratio:.1f}x). Without the min_green floor, the greedy\n"
            "  algorithm would allocate near-zero time to the low-flow road,\n"
            "  causing indefinite starvation. This is suboptimal because:\n"
            "  1. Pedestrian crossings legally require a minimum phase.\n"
            "  2. Blocking a feeder road backs up adjacent streets.\n"
            f"  MITIGATION: every road is guaranteed {min_green}s minimum."
        ) if (high and low) else ""

        return "\n".join([header, optimal, suboptimal])
