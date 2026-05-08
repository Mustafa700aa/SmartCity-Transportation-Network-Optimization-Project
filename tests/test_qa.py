from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.infrastructure.csv_loader import load_cairo_graph
from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter
from src.algorithms.greedy_preemption import GreedyPreemptionSystem
from src.algorithms.greedy_signals import GreedySignalOptimizer
from src.algorithms.dp_transit_scheduler import DPTransitScheduler
from src.algorithms.dp_maintenance import DPMaintenanceOptimizer
from src.models.responses import RouteResult

PASS = " PASS"
FAIL = " FAIL"

class QARunner:

    def __init__(self):
        self.results: list[tuple[str, str]] = []

    def check(self, label: str, passed: bool, detail: str = "") -> None:
        status = PASS if passed else FAIL
        self.results.append((status, label))
        print(f"  {status}  {label}")
        if detail:
            print(f"         → {detail}")

    @property
    def passed(self) -> int:
        return sum(1 for s, _ in self.results if s == PASS)

    @property
    def failed(self) -> int:
        return sum(1 for s, _ in self.results if s == FAIL)

    def summary(self) -> None:
        print(f"\n{'═' * 62}")
        print(f"  QA: {self.passed}/{len(self.results)} passed  "
              f"({'✅ ALL CLEAR' if not self.failed else f'❌ {self.failed} FAILED'})")
        print("═" * 62)

def qa_01_time_awareness(qa: QARunner, graph: Graph, router: DijkstraRouter) -> tuple:
    print("\n  [QA-1] Time-Awareness: Node 7 → Node 3")
    r_morn = router.find_shortest_path('7', '3', 'morning')
    r_night = router.find_shortest_path('7', '3', 'night')
    print(f"    Morning: {r_morn.total_time_min:.2f} min | Night: {r_night.total_time_min:.2f} min")
    qa.check("Morning travel time > Night (BPR peak penalty)",
             r_morn.total_time_h > r_night.total_time_h,
             f"Morning={r_morn.total_time_min:.2f} min, Night={r_night.total_time_min:.2f} min")
    return r_morn, r_night

def qa_02_bpr_consistency(qa: QARunner, graph: Graph, we: WeightEngine) -> None:
    print("\n  [QA-2] BPR Trace edge 1→3 (morning)")
    e13 = next((e for e in graph.get_edges('existing_road')
                if (e.from_id == '1' and e.to_id == '3')
                or (e.from_id == '3' and e.to_id == '1')), None)
    if e13:
        computed = we.get_edge_weight(e13, 'morning')
        expected = (8.5 / 38.0) * (1.0 + 0.15 * (2800 / 3000) ** 4)
        qa.check("BPR weight matches manual trace (Δ < 1e-9)",
                 abs(computed - expected) < 1e-9,
                 f"computed={computed:.6f}, expected={expected:.6f}, diff={abs(computed - expected):.2e}")

def qa_03_error_handling(qa: QARunner, router: DijkstraRouter) -> None:
    print("\n  [QA-3] Error Handling")
    qa.check("Bad start node → found=False",
             not router.find_shortest_path('INVALID', '3').found)
    qa.check("Bad end node → found=False",
             not router.find_shortest_path('1', 'Z99').found)
    qa.check("Bad time_of_day → found=False",
             not router.find_shortest_path('1', '3', 'rush hour').found)

def qa_04_alias_resolution(qa: QARunner, router: DijkstraRouter) -> None:
    print("\n  [QA-4] Alias Resolution")
    r_alias = router.find_shortest_path('1', '3', 'am peak')
    r_normal = router.find_shortest_path('1', '3', 'morning')
    qa.check("'am peak' == 'morning' result",
             r_alias.path == r_normal.path
             and abs(r_alias.total_time_h - r_normal.total_time_h) < 1e-12)

def qa_05_trivial_path(qa: QARunner, router: DijkstraRouter) -> None:
    print("\n  [QA-5] Same-Node Trivial Path")
    r_trivial = router.find_shortest_path('3', '3')
    qa.check("Same-node → time=0, dist=0, found=True",
             r_trivial.found and r_trivial.total_time_h == 0.0 and r_trivial.total_dist_km == 0.0)

def qa_06_hospital_reachability(qa: QARunner, router: DijkstraRouter) -> None:
    print("\n  [QA-6] Hospital Reachability")
    for h in ['F9', 'F10']:
        res = router.find_shortest_path('2', h, 'morning')
        qa.check(f"Nasr City → {h} reachable", res.found,
                 f"Path: {' → '.join(res.path)} | {res.total_time_min:.1f} min")

def qa_07_greedy_preemption(qa: QARunner, graph: Graph) -> None:
    print("\n  [QA-7] Greedy Preemption System")
    astar = AStarRouter(graph)
    r_astar = astar.find_shortest_path('2', 'F9', 'morning')
    preemptor = GreedyPreemptionSystem(graph)
    plog = preemptor.generate_preemption_log(r_astar)
    qa.check("Preemption log generated for Nasr City → F9",
             plog.overrides_applied > 0,
             f"Overrides: {plog.overrides_applied}, Saved: {plog.total_delay_saved_sec}s")
    qa.check("All intersections cleared (fully_cleared=True)",
             plog.fully_cleared,
             f"Events: {len(plog.events)}, Path nodes: {plog.total_nodes}")
    qa.check("Preemption handles invalid route gracefully",
             not GreedyPreemptionSystem(graph).generate_preemption_log(
                 RouteResult(found=False)).events,
             "Empty events for failed route")

def qa_08_greedy_signals(qa: QARunner, graph: Graph) -> None:
    print("\n  [QA-8] Greedy Signal Optimizer")
    sig_opt = GreedySignalOptimizer(graph)
    sig_sched = sig_opt.compute_schedule('3', 'morning')
    qa.check("Signal schedule generated for Downtown Cairo (node 3)",
             sig_sched.incoming_roads > 0,
             f"Incoming roads: {sig_sched.incoming_roads}, Slots: {len(sig_sched.slots)}")
    qa.check("Total green time == cycle duration (120s)",
             sum(s.green_duration for s in sig_sched.slots) == sig_sched.total_time,
             f"Sum={sum(s.green_duration for s in sig_sched.slots)}s, "
             f"Cycle={sig_sched.total_time}s")
    qa.check("Slots sorted by traffic flow (descending)",
             all(sig_sched.slots[i].traffic_flow >= sig_sched.slots[i + 1].traffic_flow
                 for i in range(len(sig_sched.slots) - 1)),
             "Greedy priority ordering confirmed")
    empty_sched = sig_opt.compute_schedule('INVALID_NODE', 'morning')
    qa.check("Empty schedule for unknown node",
             empty_sched.incoming_roads == 0 and len(empty_sched.slots) == 0,
             "Graceful handling of invalid node")

def qa_09_dp_transit(qa: QARunner, graph: Graph) -> None:
    print("\n  [QA-9] DP Transit Scheduler")
    dp_transit = DPTransitScheduler(graph)
    t_res = dp_transit.optimize('morning', 50)
    qa.check("Transit optimization produces allocations",
             t_res.total_routes > 0 and len(t_res.allocations) > 0,
             f"Routes: {t_res.total_routes}, Fleet: {t_res.fleet_assigned}/{t_res.available_fleet}")
    qa.check("Fleet assigned <= available fleet",
             t_res.fleet_assigned <= t_res.available_fleet,
             f"{t_res.fleet_assigned} <= {t_res.available_fleet}")
    qa.check("All throughput scores are non-negative",
             all(a.throughput_score >= 0 for a in t_res.allocations),
             "No negative throughput")

def qa_10_dp_maintenance(qa: QARunner, graph: Graph) -> None:
    print("\n  [QA-10] DP Maintenance Optimizer")
    dp_maint = DPMaintenanceOptimizer(graph)
    m_res = dp_maint.optimize(50.0)
    qa.check("Maintenance optimization produces candidates",
             m_res.total_candidates > 0,
             f"Candidates: {m_res.total_candidates}, Selected: {m_res.selected_count}")
    qa.check("Total cost within budget",
             m_res.total_cost_megp <= m_res.max_budget_megp + 0.01,
             f"Cost: {m_res.total_cost_megp:.2f}M <= Budget: {m_res.max_budget_megp:.1f}M")
    qa.check("Selected roads have selected=True flag",
             sum(1 for c in m_res.candidates if c.selected) == m_res.selected_count,
             f"Flags match count: {m_res.selected_count}")

def run_all_tests(graph: Graph) -> int:
    qa = QARunner()
    router = DijkstraRouter(graph)
    we = WeightEngine()

    print("\n" + "═" * 62)
    print("  PHASE 2 QA — Full Algorithm Audit")
    print("═" * 62)

    r_morn, r_night = qa_01_time_awareness(qa, graph, router)
    qa_02_bpr_consistency(qa, graph, we)
    qa_03_error_handling(qa, router)
    qa_04_alias_resolution(qa, router)
    qa_05_trivial_path(qa, router)
    qa_06_hospital_reachability(qa, router)
    qa_07_greedy_preemption(qa, graph)
    qa_08_greedy_signals(qa, graph)
    qa_09_dp_transit(qa, graph)
    qa_10_dp_maintenance(qa, graph)

    qa.summary()
    return qa.failed

def main():
    parser = argparse.ArgumentParser(
        description='Run Phase 2 QA checklist for Cairo Transportation Network'
    )
    parser.add_argument('--data-dir', type=Path, default=Path('data'),
                        help='Path to the CSV data directory')
    args = parser.parse_args()

    data_dir = args.data_dir if args.data_dir.is_dir() else Path('data')
    if not data_dir.is_dir():
        data_dir = Path('.')

    graph = load_cairo_graph(data_dir)
    print(f"Graph loaded: {graph.summary()}")

    failed = run_all_tests(graph)
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
