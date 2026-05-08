from __future__ import annotations
import math
import hashlib
from typing import List

from src.core.graph import Graph
from src.models.responses import MaintenanceCandidate, MaintenanceResult

# Budget discretization: 1 unit = 0.1 Million EGP (100K EGP granularity)
_BUDGET_SCALE = 10   # multiply MEGP by this to get integer units

# All time periods for total traffic benefit
_ALL_PERIODS = ('morning', 'afternoon', 'evening', 'night')

class DPMaintenanceOptimizer:

    def __init__(self, graph: Graph):
        if not isinstance(graph, Graph):
            raise TypeError(
                f"DPMaintenanceOptimizer requires a Graph instance, got {type(graph)}"
            )
        self._graph = graph

    def optimize(
        self,
        max_budget_megp: float = 50.0,
    ) -> MaintenanceResult:

        items = self._extract_candidates()

        if not items:
            return MaintenanceResult(
                max_budget_megp=max_budget_megp, total_candidates=0,
                selected_count=0, total_cost_megp=0.0, total_benefit=0.0,
                budget_utilization=0.0,
                analysis="No roads requiring maintenance found.",
            )

        n = len(items)
        W = int(max_budget_megp * _BUDGET_SCALE)  # discretize budget

        costs    = [max(1, math.ceil(it['cost_megp'] * _BUDGET_SCALE)) for it in items]
        benefits = [it['benefit'] for it in items]

        #   dp[i][w] = max benefit using items 0..i-1 with capacity w
        dp = [[0.0] * (W + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            ci, bi = costs[i - 1], benefits[i - 1]
            for w in range(W + 1):
                dp[i][w] = dp[i - 1][w]          # skip item i
                if w >= ci:
                    take = dp[i - 1][w - ci] + bi
                    if take > dp[i][w]:
                        dp[i][w] = take           # take item i

        dp_table_size = n * W

        selected = set()
        w = W
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i - 1][w]:
                selected.add(i - 1)
                w -= costs[i - 1]

        candidates: List[MaintenanceCandidate] = []
        total_cost = 0.0
        total_benefit = 0.0

        for idx, it in enumerate(items):
            is_selected = idx in selected
            if is_selected:
                total_cost += it['cost_megp']
                total_benefit += it['benefit']

            candidates.append(MaintenanceCandidate(
                road_id=it['road_id'],
                from_name=it['from_name'],
                to_name=it['to_name'],
                distance_km=it['distance_km'],
                condition=it['condition'],
                repair_cost_megp=it['cost_megp'],
                traffic_benefit=it['benefit'],
                selected=is_selected,
            ))

        # Sort: selected first (by benefit descending), then unselected
        candidates.sort(key=lambda c: (-c.selected, -c.traffic_benefit))

        utilization = (total_cost / max_budget_megp * 100) if max_budget_megp > 0 else 0
        selected_count = len(selected)

        analysis = self._build_analysis(
            candidates, max_budget_megp, total_cost, total_benefit,
            selected_count, n,
        )

        return MaintenanceResult(
            max_budget_megp=max_budget_megp,
            total_candidates=n,
            selected_count=selected_count,
            total_cost_megp=total_cost,
            total_benefit=total_benefit,
            budget_utilization=utilization,
            candidates=candidates,
            dp_table_size=dp_table_size,
            analysis=analysis,
        )

    def _extract_candidates(self) -> List[dict]:
        items = []
        seen = set()

        for edge in self._graph.get_edges('existing_road'):
            # Deduplicate undirected edges
            key = self._graph.ek(edge.from_id, edge.to_id)
            if key in seen:
                continue
            seen.add(key)

            dist = edge.distance_km or 1.0
            condition = edge.condition
            if condition is None:
                # Deterministic pseudo-random condition from edge IDs
                h = hashlib.md5(f"{edge.from_id}-{edge.to_id}".encode()).hexdigest()
                condition = (int(h[:8], 16) % 10) + 1  # 1-10

            # Skip perfect-condition roads
            if condition >= 10:
                continue

            # Cost: distance × deterioration factor
            cost_megp = dist * (11 - condition)

            # Benefit: total traffic flow across all 4 periods
            benefit = 0.0
            for period in _ALL_PERIODS:
                benefit += edge.traffic_flow.get(period, 0.0)

            if benefit <= 0:
                continue

            from_node = self._graph.nodes.get(edge.from_id)
            to_node   = self._graph.nodes.get(edge.to_id)

            items.append({
                'road_id':     f"{edge.from_id}-{edge.to_id}",
                'from_name':   from_node.name if from_node else edge.from_id,
                'to_name':     to_node.name if to_node else edge.to_id,
                'distance_km': dist,
                'condition':   condition,
                'cost_megp':   cost_megp,
                'benefit':     benefit,
            })

        return items

    @staticmethod
    def _build_analysis(
        candidates: List[MaintenanceCandidate],
        budget: float,
        total_cost: float,
        total_benefit: float,
        selected: int,
        total: int,
    ) -> str:
        if not candidates:
            return "No candidates to analyze."

        selected_items = [c for c in candidates if c.selected]
        skipped_items  = [c for c in candidates if not c.selected]

        best = selected_items[0] if selected_items else None
        worst_skipped = skipped_items[-1] if skipped_items else None

        lines = [
            f"0/1 Knapsack DP | {total} candidate roads | "
            f"Budget: {budget:.1f} M EGP",
            f"Selected: {selected} roads | Cost: {total_cost:.2f} M EGP | "
            f"Benefit: {total_benefit:.0f} veh/h total",
            "",
            "OPTIMAL SCENARIO:",
            "  The 0/1 Knapsack DP guarantees the globally optimal subset",
            "  of roads to repair within the budget constraint. Unlike greedy",
            "  approaches that sort by benefit/cost ratio, DP considers all",
            "  2^N subsets implicitly via dynamic programming.",
        ]
        if best:
            lines.append(
                f"  Best repair: {best.road_id} (condition {best.condition:.0f}/10) "
                f"→ cost {best.repair_cost_megp:.2f}M, benefit {best.traffic_benefit:.0f} veh/h"
            )

        lines += [
            "",
            "SUBOPTIMAL SCENARIO:",
            "  A greedy benefit/cost ratio heuristic might select roads with",
            "  high ratios that leave too little budget for high-benefit roads.",
            "  The DP solution avoids this by exploring all feasible combinations.",
        ]
        if worst_skipped:
            lines.append(
                f"  Skipped: {worst_skipped.road_id} "
                f"(cost {worst_skipped.repair_cost_megp:.2f}M, "
                f"benefit {worst_skipped.traffic_benefit:.0f}) — "
                f"exceeds remaining budget or displaced by better combination."
            )

        return "\n".join(lines)
