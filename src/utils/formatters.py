from __future__ import annotations

from src.core.graph import Graph
from src.models.responses import (
    RouteResult, MSTResult, PreemptionLog,
    GreenLightSchedule, TransitScheduleResult, MaintenanceResult,
)


def parse_avoid_edges(avoid: list[str] | None) -> set | None:
    """Parse CLI avoid-edge strings like ['1-3', '5-8'] into a frozenset of tuples."""
    if not avoid:
        return None
    return {tuple(sorted(e.split('-'))) for e in avoid}


def format_route_result(result: RouteResult, graph: Graph) -> str:
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


def format_mst_result(result: MSTResult, graph: Graph) -> str:
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


def format_astar_comparison(astar_result: RouteResult, dijk_result: RouteResult,
                             graph: Graph) -> str:
    lines = []
    sep  = "═" * 68
    sep2 = "─" * 68

    lines.append(f"\n{sep}")
    lines.append("  🚑  EMERGENCY ROUTING — A* vs Dijkstra Comparison")
    lines.append(sep)

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


def format_preemption_log(log: PreemptionLog, graph: Graph) -> str:
    lines = []
    sep  = "═" * 70
    sep2 = "─" * 70

    lines.append(f"\n{sep}")
    lines.append("  🚑  EMERGENCY VEHICLE PREEMPTION — Greedy Signal Override Report")
    lines.append(sep)

    if not log.events:
        lines.append("  ❌  No preemption events — route was not found or path is empty.")
        if log.warnings:
            for w in log.warnings:
                lines.append(f"      ⚠️  {w}")
        lines.append(sep)
        return "\n".join(lines)

    lines.append(f"  Time of Day        : {log.time_of_day.upper()}")
    lines.append(f"  Path               : {' → '.join(log.route_path)}")
    lines.append(f"  Total Intersections : {log.total_nodes}")
    lines.append(f"  Overrides Applied   : {log.overrides_applied}")
    lines.append(f"  Total Delay Saved   : {log.total_delay_saved_sec} sec "
                 f"({log.total_delay_saved_sec / 60:.1f} min)")
    lines.append(f"  Fully Cleared       : {'✅ YES' if log.fully_cleared else '❌ NO'}")
    lines.append(sep)

    lines.append("  SIGNAL OVERRIDE SEQUENCE:")
    lines.append(f"  {'#':>3}  {'Node':>5}  {'Name':<25}  {'Signal':<9}  "
                 f"{'Congestion':<10}  {'Traffic':>8}  {'Saved':>6}  {'Total':>6}")
    lines.append("  " + sep2)

    for ev in log.events:
        lines.append(
            f"  {ev.step:>3}  {ev.node_id:>5}  {ev.node_name:<25}  "
            f"{'🟢 GREEN':<9}  {ev.congestion_level:<10}  "
            f"{ev.traffic_volume:>8.0f}  {ev.delay_saved_sec:>5}s  "
            f"{ev.cumulative_saved_sec:>5}s"
        )
        if ev.note:
            lines.append(f"        └─ {ev.note}")

    if log.warnings:
        lines.append(f"\n  ⚠️  WARNINGS:")
        for w in log.warnings:
            lines.append(f"      {w}")

    lines.append(sep)
    return "\n".join(lines)


def format_signal_schedule(sched: GreenLightSchedule, graph: Graph) -> str:
    lines = []
    sep  = "═" * 70
    sep2 = "─" * 70

    lines.append(f"\n{sep}")
    lines.append("  🚦  TRAFFIC SIGNAL OPTIMIZATION — Greedy Schedule Report")
    lines.append(sep)

    if not sched.slots:
        lines.append(f"  ❌  No incoming roads for node {sched.node_id} ({sched.node_name})")
        lines.append(sep)
        return "\n".join(lines)

    lines.append(f"  Intersection      : {sched.node_id} ({sched.node_name})")
    lines.append(f"  Time of Day       : {sched.time_of_day.upper()}")
    lines.append(f"  Incoming Roads    : {sched.incoming_roads}")
    lines.append(f"  Cycle Duration    : {sched.total_time}s")
    lines.append(sep)

    lines.append("  GREEN-LIGHT ALLOCATION (priority order):")
    lines.append(f"  {'Rank':>4}  {'Road':<12}  {'From':<25}  "
                 f"{'Flow(veh/h)':>11}  {'Green(s)':>8}  {'Share':>6}")
    lines.append("  " + sep2)

    for s in sched.slots:
        pct = s.green_duration / sched.total_time * 100
        lines.append(
            f"  {s.priority_rank:>4}  {s.road_id:<12}  {s.from_name:<25}  "
            f"{s.traffic_flow:>11.0f}  {s.green_duration:>8}  {pct:>5.1f}%"
        )

    lines.append("  " + sep2)
    lines.append(f"  Total: {sched.total_time}s")

    if sched.analysis:
        lines.append(f"\n  ANALYSIS:")
        for aline in sched.analysis.split('\n'):
            lines.append(f"    {aline}")

    lines.append(sep)
    return "\n".join(lines)


def format_transit_schedule(res: TransitScheduleResult, graph: Graph) -> str:
    lines = []
    sep  = "═" * 78
    sep2 = "─" * 78

    lines.append(f"\n{sep}")
    lines.append("  🚌  DP-1: PUBLIC TRANSIT OPTIMIZATION — Fleet Allocation Report")
    lines.append(sep)

    if not res.allocations:
        lines.append("  ❌  No transit routes found.")
        lines.append(sep)
        return "\n".join(lines)

    lines.append(f"  Time of Day       : {res.time_of_day.upper()}")
    lines.append(f"  Available Fleet   : {res.available_fleet} units")
    lines.append(f"  Routes Optimized  : {res.total_routes}")
    lines.append(f"  Fleet Assigned    : {res.fleet_assigned} units")
    lines.append(f"  Total Throughput  : {res.total_throughput:,.0f} passengers")
    lines.append(f"  Avg Wait Time     : {res.avg_wait_time_min:.1f} min")
    lines.append(f"  DP Table Size     : {res.dp_table_size:,} comparisons")
    lines.append(sep)

    lines.append("  FLEET ALLOCATION (by priority):")
    lines.append(
        f"  {'Route':<8} {'Name':<22} {'Type':<6} {'Demand':>10} "
        f"{'Orig':>5} {'Alloc':>5} {'Throughput':>10} {'Wait':>6}")
    lines.append("  " + sep2)

    for a in res.allocations:
        lines.append(
            f"  {a.route_id:<8} {a.line_name:<22} {a.edge_type:<6} "
            f"{a.daily_passengers:>10,.0f} {a.original_fleet:>5} "
            f"{a.allocated_fleet:>5} {a.throughput_score:>10,.0f} "
            f"{a.wait_time_min:>5.1f}m")

    if res.analysis:
        lines.append(f"\n  ANALYSIS:")
        for aline in res.analysis.split('\n'):
            lines.append(f"    {aline}")

    lines.append(sep)
    return "\n".join(lines)


def format_maintenance_report(res: MaintenanceResult, graph: Graph) -> str:
    lines = []
    sep  = "═" * 78
    sep2 = "─" * 78

    lines.append(f"\n{sep}")
    lines.append("  🛠️  DP-2: ROAD MAINTENANCE OPTIMIZATION — 0/1 Knapsack Report")
    lines.append(sep)

    if not res.candidates:
        lines.append("  ❌  No candidate roads found.")
        lines.append(sep)
        return "\n".join(lines)

    lines.append(f"  Budget            : {res.max_budget_megp:.1f} Million EGP")
    lines.append(f"  Candidate Roads   : {res.total_candidates}")
    lines.append(f"  Selected for Repair: {res.selected_count}")
    lines.append(f"  Total Cost        : {res.total_cost_megp:.2f} Million EGP")
    lines.append(f"  Total Benefit     : {res.total_benefit:,.0f} veh/h")
    lines.append(f"  Budget Utilization: {res.budget_utilization:.1f}%")
    lines.append(f"  DP Table Size     : {res.dp_table_size:,} cells")
    lines.append(sep)

    selected = [c for c in res.candidates if c.selected]
    skipped  = [c for c in res.candidates if not c.selected]

    if selected:
        lines.append("  ✅ SELECTED FOR REPAIR:")
        lines.append(
            f"  {'Road':<10} {'From':<20} {'To':<20} "
            f"{'Dist':>6} {'Cond':>5} {'Cost(M)':>8} {'Benefit':>8}")
        lines.append("  " + sep2)
        for c in selected:
            lines.append(
                f"  {c.road_id:<10} {c.from_name:<20} {c.to_name:<20} "
                f"{c.distance_km:>5.1f}  {c.condition:>4.0f}  "
                f"{c.repair_cost_megp:>7.2f}  {c.traffic_benefit:>7.0f}")

    if skipped:
        lines.append(f"\n  ❌ SKIPPED ({len(skipped)} roads):")
        for c in skipped[:5]:
            lines.append(
                f"    {c.road_id:<10} cond={c.condition:.0f} "
                f"cost={c.repair_cost_megp:.2f}M "
                f"benefit={c.traffic_benefit:.0f}")
        if len(skipped) > 5:
            lines.append(f"    ... and {len(skipped)-5} more")

    if res.analysis:
        lines.append(f"\n  ANALYSIS:")
        for aline in res.analysis.split('\n'):
            lines.append(f"    {aline}")

    lines.append(sep)
    return "\n".join(lines)
