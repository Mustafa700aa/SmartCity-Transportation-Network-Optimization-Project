"""
main.py — Unified CLI entry point for the Cairo Smart City Transportation Network.

Responsibilities:
  - CLI argument parsing (argparse)
  - Graph loading via load_cairo_graph()
  - Route result formatting (format_route_result)
  - QA runner (_run_qa)
  - Visualization via plot_graph()

This file is the ONLY place that owns presentation logic and execution flow.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.infrastructure.csv_loader import load_cairo_graph
from src.utils.visualizer import plot_graph
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter
from src.algorithms.mst import kruskal_mst
from src.models.responses import RouteResult, MSTResult
from src.core.graph import Graph
from src.core.weight_engine import WeightEngine


# ─────────────────────────────────────────────────────────────────────────────
# UI Formatting (moved out of RouteResult per SRP)
# ─────────────────────────────────────────────────────────────────────────────
def format_route_result(result: RouteResult, graph: Graph) -> str:
    """
    Render a RouteResult as a human-readable string.
    Separated from the data class to respect SRP.
    """
    lines = []
    sep = "═" * 62
    lines.append(f"\n{sep}")

    if not result.found:
        lines.append("  ❌  ROUTE NOT FOUND")
        lines.append(f"      Reason: {result.error}")
        lines.append(sep)
        return "\n".join(lines)

    start_name = graph.nodes[result.path[0]].name  if result.path else "?"
    end_name   = graph.nodes[result.path[-1]].name if result.path else "?"
    lines.append(f"  🗺️   OPTIMAL ROUTE  [{result.time_of_day.upper()}]")
    lines.append(f"  {result.path[0]} ({start_name})  →  {result.path[-1]} ({end_name})")
    lines.append(sep)

    path_str = " → ".join(
        f"{nid}({graph.nodes[nid].name})" if nid in graph.nodes else nid
        for nid in result.path
    )
    lines.append(f"  Path     : {path_str}")
    lines.append(f"  Hops     : {result.hops}")
    lines.append(f"  Distance : {result.total_dist_km:.2f} km")
    lines.append(f"  Time     : {result.total_time_h:.4f} h  ({result.total_time_min:.1f} min)")
    lines.append(f"  Modes    : {', '.join(sorted(set(result.edge_types_used)))}")
    lines.append(f"  Nodes explored: {result.iterations}")
    lines.append(sep)
    lines.append("  SEGMENT BREAKDOWN:")
    lines.append(f"  {'#':>3}  {'From':>5}  {'To':>5}  {'Type':<16}  {'Dist(km)':>9}  {'Time(min)':>10}")
    lines.append("  " + "─" * 58)
    for i, seg in enumerate(result.segments, 1):
        lines.append(
            f"  {i:>3}  {seg['from']:>5}  {seg['to']:>5}  "
            f"{seg['type']:<16}  {seg['dist_km']:>9.2f}  {seg['time_h'] * 60:>10.2f}"
        )
    lines.append(sep)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MST Formatter
# ─────────────────────────────────────────────────────────────────────────────
def format_mst_result(result: MSTResult, graph: Graph) -> str:
    """
    Render a MSTResult as a human-readable infrastructure report.
    Presentation logic lives here in main.py per SRP.
    """
    lines = []
    sep  = "═" * 66
    sep2 = "─" * 66

    lines.append(f"\n{sep}")
    lines.append("  🏗️   MINIMUM SPANNING TREE — Cairo Potential Road Infrastructure")
    lines.append(sep)
    lines.append(f"  Components before MST : {result.components_before}")
    lines.append(f"  Components after  MST : {result.components_after}")
    lines.append(f"  Fully connected       : {' YES' if result.fully_connected else ' NO — isolated clusters remain'}")
    lines.append(f"  Roads selected        : {len(result.mst_edges)} of {len(result.mst_edges) + len(result.skipped_edges)}")
    lines.append(f"  Total build cost      : {result.total_cost:,.1f} Million EGP")
    lines.append(f"  Roads skipped (cycle) : {len(result.skipped_edges)}")
    lines.append(sep)

    lines.append("  SELECTED ROADS (sorted by build cost):")
    lines.append(f"  {'#':>3}  {'From':>5}  {'To':>5}  {'Dist(km)':>9}  {'Cost(M EGP)':>12}  {'From Node':<25}  To Node")
    lines.append("  " + sep2)
    for i, e in enumerate(result.mst_edges, 1):
        fn = graph.nodes.get(e.from_id)
        tn = graph.nodes.get(e.to_id)
        lines.append(
            f"  {i:>3}  {e.from_id:>5}  {e.to_id:>5}  "
            f"{e.distance_km or 0:>9.1f}  {e.construction_cost or 0:>12,.1f}  "
            f"{fn.name if fn else '?':<25}  {tn.name if tn else '?'}"
        )

    if result.skipped_edges:
        lines.append(f"\n  SKIPPED (would create redundant loop):")
        lines.append(f"  {', '.join(result.skipped_edges)}")

    lines.append(sep)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# A* Comparison Formatter
# ─────────────────────────────────────────────────────────────────────────────
def format_astar_comparison(astar_result: RouteResult, dijk_result: RouteResult,
                             graph: Graph) -> str:
    """
    Side-by-side A* vs Dijkstra performance report.
    Validates path consistency and efficiency gain.
    """
    lines = []
    sep  = "═" * 68
    sep2 = "─" * 68

    lines.append(f"\n{sep}")
    lines.append("  🚑  EMERGENCY ROUTING — A* vs Dijkstra Comparison")
    lines.append(sep)

    # Path consistency
    paths_match = (astar_result.path == dijk_result.path)
    times_match = (abs(astar_result.total_time_h - dijk_result.total_time_h) < 1e-9)
    lines.append(f"  Path identical   : {' YES' if paths_match else '  DIFFER'}")
    lines.append(f"  Travel time equal: {' YES' if times_match else '  DIFFER'}")

    if astar_result.found and dijk_result.found:
        saved  = dijk_result.iterations - astar_result.iterations
        pct    = saved / max(dijk_result.iterations, 1) * 100
        lines.append(f"  Nodes explored   : A*={astar_result.iterations}  Dijkstra={dijk_result.iterations}")
        lines.append(f"  Efficiency gain  : {saved} fewer expansions ({pct:.1f}% faster)")
    lines.append(sep)

    # A* detail
    if astar_result.found:
        lines.append(f"  A* Path  [{astar_result.time_of_day.upper()}]:  "
                     f"{' → '.join(astar_result.path)}")
        lines.append(f"  Time: {astar_result.total_time_min:.2f} min  |  "
                     f"Dist: {astar_result.total_dist_km:.2f} km  |  "
                     f"Hops: {astar_result.hops}  |  "
                     f"Iterations: {astar_result.iterations}")
    else:
        lines.append(f"  A* : {astar_result.error}")

    lines.append(sep2)

    # Dijkstra detail
    if dijk_result.found:
        lines.append(f"  Dijkstra Path    :  "
                     f"{' → '.join(dijk_result.path)}")
        lines.append(f"  Time: {dijk_result.total_time_min:.2f} min  |  "
                     f"Dist: {dijk_result.total_dist_km:.2f} km  |  "
                     f"Hops: {dijk_result.hops}  |  "
                     f"Iterations: {dijk_result.iterations}")
    else:
        lines.append(f"  Dijkstra:  {dijk_result.error}")

    lines.append(sep)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# QA Runner
# ─────────────────────────────────────────────────────────────────────────────
def _run_qa(graph: Graph) -> None:
    """Phase 2 QA Checklist for DijkstraRouter."""
    PASS = " PASS"
    FAIL = " FAIL"
    results = []

    def check(label, passed, detail=""):
        status = PASS if passed else FAIL
        results.append((status, label))
        print(f"  {status}  {label}")
        if detail:
            print(f"         → {detail}")

    print("\n" + "═" * 62)
    print("  PHASE 2 QA — DijkstraRouter Audit")
    print("═" * 62)

    router = DijkstraRouter(graph)
    we     = WeightEngine(graph.weight_cache)

    # QA-1: Time-Awareness
    print("\n  [QA-1] Time-Awareness: Node 7 → Node 3")
    r_morn  = router.find_shortest_path('7', '3', 'morning')
    r_night = router.find_shortest_path('7', '3', 'night')
    print(f"    Morning: {r_morn.total_time_min:.2f} min | Night: {r_night.total_time_min:.2f} min")
    check("Morning travel time > Night (BPR peak penalty)",
          r_morn.total_time_h > r_night.total_time_h,
          f"Morning={r_morn.total_time_min:.2f} min, Night={r_night.total_time_min:.2f} min")

    # QA-2: BPR Consistency
    print("\n  [QA-2] BPR Trace edge 1→3 (morning)")
    e13 = next((e for e in graph.get_edges('existing_road')
                if (e.from_id == '1' and e.to_id == '3')
                or (e.from_id == '3' and e.to_id == '1')), None)
    if e13:
        computed = we.get_edge_weight(e13, 'morning')
        expected = (8.5 / 38.0) * (1.0 + 0.15 * (2800 / 3000) ** 4)
        check("BPR weight matches manual trace (Δ < 1e-9)",
              abs(computed - expected) < 1e-9,
              f"computed={computed:.6f}, expected={expected:.6f}, diff={abs(computed-expected):.2e}")

    # QA-3: Error Handling
    print("\n  [QA-3] Error Handling")
    check("Bad start node → found=False",
          not router.find_shortest_path('INVALID', '3').found)
    check("Bad end node → found=False",
          not router.find_shortest_path('1', 'Z99').found)
    check("Bad time_of_day → found=False",
          not router.find_shortest_path('1', '3', 'rush hour').found)

    # QA-4: Alias resolution
    print("\n  [QA-4] Alias Resolution")
    r_alias  = router.find_shortest_path('1', '3', 'am peak')
    r_normal = router.find_shortest_path('1', '3', 'morning')
    check("'am peak' == 'morning' result",
          r_alias.path == r_normal.path
          and abs(r_alias.total_time_h - r_normal.total_time_h) < 1e-12)

    # QA-5: Trivial same-node
    print("\n  [QA-5] Same-Node Trivial Path")
    r_trivial = router.find_shortest_path('3', '3')
    check("Same-node → time=0, dist=0, found=True",
          r_trivial.found and r_trivial.total_time_h == 0.0 and r_trivial.total_dist_km == 0.0)

    # QA-6: Hospital reachability
    print("\n  [QA-6] Hospital Reachability")
    for h in ['F9', 'F10']:
        res = router.find_shortest_path('2', h, 'morning')
        check(f"Nasr City → {h} reachable", res.found,
              f"Path: {' → '.join(res.path)} | {res.total_time_min:.1f} min")

    # Summary
    passed = sum(1 for s, _ in results if s == PASS)
    failed = sum(1 for s, _ in results if s == FAIL)
    print(f"\n{'═'*62}")
    print(f"  QA: {passed}/{len(results)} passed  "
          f"({' ALL CLEAR' if not failed else f' {failed} FAILED'})")
    print("═" * 62)

    # Full route reports
    print(format_route_result(r_morn,  graph))
    print(format_route_result(r_night, graph))


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_data_dir(arg: Path) -> Path:
    """Auto-detect data directory: prefer ./data/, fall back to ./ ."""
    if arg.is_dir():
        return arg
    default = Path('data')
    return default if default.is_dir() else Path('.')


def main():
    p = argparse.ArgumentParser(
        description='Cairo Smart City Transportation Network CLI'
    )
    sub = p.add_subparsers(dest='cmd')

    # ── plot ──────────────────────────────────────────────────────────────────
    plot_p = sub.add_parser('plot', help='Visualize the transportation graph')
    plot_p.add_argument('--data-dir',       type=Path, default=Path('data'))
    plot_p.add_argument('--hide-potential', action='store_true')
    plot_p.add_argument('--hide-labels',    action='store_true')
    plot_p.add_argument('--annotate',       choices=['all', 'facilities', 'neighborhoods'], default='all')
    plot_p.add_argument('--time-of-day',    default='morning')

    # ── route ─────────────────────────────────────────────────────────────────
    route_p = sub.add_parser('route', help='Find shortest path between two nodes')
    route_p.add_argument('--data-dir', type=Path, default=Path('data'))
    route_p.add_argument('--from',  dest='start', required=True)
    route_p.add_argument('--to',    dest='end',   required=True)
    route_p.add_argument('--time',  dest='tod',   default='morning')
    route_p.add_argument('--compare', action='store_true',
                         help='Run all 4 time periods and compare')
    route_p.add_argument('--modes', nargs='+', default=None)

    # ── mst ───────────────────────────────────────────────────────────────────
    mst_p = sub.add_parser('mst', help='Run Kruskal MST on potential roads')
    mst_p.add_argument('--data-dir', type=Path, default=Path('data'))

    # ── astar ─────────────────────────────────────────────────────────────────
    astar_p = sub.add_parser('astar', help='A* emergency routing vs Dijkstra comparison')
    astar_p.add_argument('--data-dir', type=Path, default=Path('data'))
    astar_p.add_argument('--from',  dest='start', required=True)
    astar_p.add_argument('--to',    dest='end',   required=True)
    astar_p.add_argument('--time',  dest='tod',   default='morning')
    astar_p.add_argument('--modes', nargs='+', default=None)

    # ── qa ────────────────────────────────────────────────────────────────────
    qa_p = sub.add_parser('qa', help='Run Phase 2 QA checklist')
    qa_p.add_argument('--data-dir', type=Path, default=Path('data'))

    args = p.parse_args()

    if args.cmd is None:
        p.print_help()
        return

    data_dir = _resolve_data_dir(args.data_dir)
    graph    = load_cairo_graph(data_dir)
    print(f"Graph loaded: {graph.summary()}")

    if args.cmd == 'plot':
        plot_graph(graph,
                   show_labels=not args.hide_labels,
                   show_potential=not args.hide_potential,
                   annotate=args.annotate,
                   time_of_day=args.time_of_day)

    elif args.cmd == 'route':
        router = DijkstraRouter(graph, edge_types=args.modes)
        if args.compare:
            comparison = router.compare_times(args.start, args.end)
            print(f"\n  {'Period':<12}  {'Time (min)':>10}  {'Dist (km)':>10}  {'Hops':>5}  Path")
            print("  " + "─" * 65)
            for period, res in comparison.items():
                if res.found:
                    print(f"  {period:<12}  {res.total_time_min:>10.2f}  "
                          f"{res.total_dist_km:>10.2f}  {res.hops:>5}  "
                          f"{' → '.join(res.path)}")
                else:
                    print(f"  {period:<12}  UNREACHABLE")
        else:
            result = router.find_shortest_path(args.start, args.end, args.tod)
            print(format_route_result(result, graph))

    elif args.cmd == 'mst':
        result = kruskal_mst(graph)
        print(format_mst_result(result, graph))

    elif args.cmd == 'astar':
        astar  = AStarRouter(graph, edge_types=args.modes)
        dijk   = DijkstraRouter(graph, edge_types=args.modes)
        ra     = astar.find_shortest_path(args.start, args.end, args.tod)
        rd     = dijk.find_shortest_path(args.start, args.end, args.tod)
        print(format_astar_comparison(ra, rd, graph))

    elif args.cmd == 'qa':
        _run_qa(graph)


if __name__ == '__main__':
    main()
