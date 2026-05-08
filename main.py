from __future__ import annotations

import argparse
from pathlib import Path

from src.infrastructure.csv_loader import load_cairo_graph
from src.utils.visualizer import plot_graph
from src.utils.formatters import (
    format_route_result, format_mst_result, format_astar_comparison,
    format_preemption_log, format_signal_schedule,
    format_transit_schedule, format_maintenance_report,
    parse_avoid_edges,
)
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter
from src.algorithms.mst import kruskal_mst
from src.algorithms.greedy_preemption import GreedyPreemptionSystem
from src.algorithms.greedy_signals import GreedySignalOptimizer
from src.algorithms.dp_transit_scheduler import DPTransitScheduler
from src.algorithms.dp_maintenance import DPMaintenanceOptimizer
from src.core.weight_engine import WeightEngine


def _resolve_data_dir(arg: Path) -> Path:
    if arg.is_dir():
        return arg
    default = Path('data')
    return default if default.is_dir() else Path('.')


def main():
    p = argparse.ArgumentParser(
        description='Cairo Smart City Transportation Network CLI'
    )
    sub = p.add_subparsers(dest='cmd')

    plot_p = sub.add_parser('plot', help='Visualize the transportation graph')
    plot_p.add_argument('--data-dir',       type=Path, default=Path('data'))
    plot_p.add_argument('--hide-potential', action='store_true')
    plot_p.add_argument('--hide-labels',    action='store_true')
    plot_p.add_argument('--annotate',       choices=['all', 'facilities', 'neighborhoods'], default='all')
    plot_p.add_argument('--time-of-day',    default='morning')

    route_p = sub.add_parser('route', help='Find shortest path between two nodes')
    route_p.add_argument('--data-dir', type=Path, default=Path('data'))
    route_p.add_argument('--from',  dest='start', required=True)
    route_p.add_argument('--to',    dest='end',   required=True)
    route_p.add_argument('--time',  dest='tod',   default='morning')
    route_p.add_argument('--compare', action='store_true',
                         help='Run all 4 time periods and compare')
    route_p.add_argument('--modes', nargs='+', default=None)
    route_p.add_argument('--avoid', nargs='+', default=None,
                         help='Edge IDs to avoid, e.g. --avoid 1-3 5-8')
    route_p.add_argument('--plot', action='store_true',
                         help='Visualize the result on the map')
    route_p.add_argument('--weight-mode', dest='weight_mode',
                         choices=['bpr', 'ml'], default='bpr',
                         help='Weight calculation strategy (default: bpr)')

    mst_p = sub.add_parser('mst', help='Run Kruskal MST on potential roads')
    mst_p.add_argument('--data-dir', type=Path, default=Path('data'))
    mst_p.add_argument('--plot', action='store_true',
                       help='Visualize the MST on the map')

    astar_p = sub.add_parser('astar', help='A* emergency routing vs Dijkstra comparison')
    astar_p.add_argument('--data-dir', type=Path, default=Path('data'))
    astar_p.add_argument('--from',  dest='start', required=True)
    astar_p.add_argument('--to',    dest='end',   required=True)
    astar_p.add_argument('--time',  dest='tod',   default='morning')
    astar_p.add_argument('--modes', nargs='+', default=None)
    astar_p.add_argument('--avoid', nargs='+', default=None,
                         help='Edge IDs to avoid, e.g. --avoid 1-3 5-8')
    astar_p.add_argument('--plot', action='store_true',
                         help='Visualize the A* result on the map')
    astar_p.add_argument('--weight-mode', dest='weight_mode',
                         choices=['bpr', 'ml'], default='bpr',
                         help='Weight calculation strategy (default: bpr)')

    preempt_p = sub.add_parser('preempt', help='Greedy emergency signal preemption simulation')
    preempt_p.add_argument('--data-dir', type=Path, default=Path('data'))
    preempt_p.add_argument('--from',  dest='start', required=True)
    preempt_p.add_argument('--to',    dest='end',   required=True)
    preempt_p.add_argument('--time',  dest='tod',   default='morning')
    preempt_p.add_argument('--modes', nargs='+', default=None)

    sig_p = sub.add_parser('signals', help='Greedy traffic signal optimization')
    sig_p.add_argument('--data-dir', type=Path, default=Path('data'))
    sig_p.add_argument('--node',  dest='node', required=True,
                       help='Intersection node ID to schedule')
    sig_p.add_argument('--time',  dest='tod', default='morning')
    sig_p.add_argument('--cycle', dest='cycle', type=int, default=120,
                       help='Signal cycle duration in seconds')
    sig_p.add_argument('--min-green', dest='min_green', type=int, default=10,
                       help='Minimum green time per road in seconds')
    sig_p.add_argument('--batch', nargs='+', default=None,
                       help='Schedule multiple nodes at once')

    transit_p = sub.add_parser('transit', help='DP transit fleet optimization')
    transit_p.add_argument('--data-dir', type=Path, default=Path('data'))
    transit_p.add_argument('--time',  dest='tod', default='morning')
    transit_p.add_argument('--fleet', dest='fleet', type=int, default=50,
                           help='Total available fleet units')

    maint_p = sub.add_parser('maintain', help='DP road maintenance knapsack')
    maint_p.add_argument('--data-dir', type=Path, default=Path('data'))
    maint_p.add_argument('--budget', dest='budget', type=float, default=50.0,
                         help='Max budget in Million EGP')

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
        # WeightEngine is constructed lazily — only when routing is requested.
        we     = WeightEngine(strategy=args.weight_mode)
        avoid  = parse_avoid_edges(args.avoid)
        router = DijkstraRouter(graph, edge_types=args.modes, weight_engine=we)
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
            result = router.find_shortest_path(args.start, args.end, args.tod,
                                               avoid_edges=avoid)
            print(format_route_result(result, graph))
            if args.plot:
                plot_graph(graph, time_of_day=args.tod, route_result=result)

    elif args.cmd == 'mst':
        result = kruskal_mst(graph)
        print(format_mst_result(result, graph))
        if args.plot:
            plot_graph(graph, mst_result=result)

    elif args.cmd == 'astar':
        # WeightEngine is constructed lazily — only when routing is requested.
        we    = WeightEngine(strategy=args.weight_mode)
        avoid = parse_avoid_edges(args.avoid)
        astar = AStarRouter(graph, edge_types=args.modes, weight_engine=we)
        dijk  = DijkstraRouter(graph, edge_types=args.modes, weight_engine=we)
        ra    = astar.find_shortest_path(args.start, args.end, args.tod,
                                         avoid_edges=avoid)
        rd    = dijk.find_shortest_path(args.start, args.end, args.tod,
                                        avoid_edges=avoid)
        print(format_astar_comparison(ra, rd, graph))
        if args.plot:
            plot_graph(graph, time_of_day=args.tod, route_result=ra)

    elif args.cmd == 'preempt':
        astar     = AStarRouter(graph, edge_types=args.modes)
        route     = astar.find_shortest_path(args.start, args.end, args.tod)
        print(format_route_result(route, graph))
        preemptor = GreedyPreemptionSystem(graph)
        log       = preemptor.generate_preemption_log(route)
        print(format_preemption_log(log, graph))

    elif args.cmd == 'signals':
        optimizer = GreedySignalOptimizer(graph)
        if args.batch:
            schedules = optimizer.compute_batch(
                args.batch, args.tod, args.cycle, args.min_green)
            for sched in schedules:
                print(format_signal_schedule(sched, graph))
        else:
            sched = optimizer.compute_schedule(
                args.node, args.tod, args.cycle, args.min_green)
            print(format_signal_schedule(sched, graph))

    elif args.cmd == 'transit':
        scheduler = DPTransitScheduler(graph)
        result    = scheduler.optimize(args.tod, args.fleet)
        print(format_transit_schedule(result, graph))

    elif args.cmd == 'maintain':
        optimizer = DPMaintenanceOptimizer(graph)
        result    = optimizer.optimize(args.budget)
        print(format_maintenance_report(result, graph))


if __name__ == '__main__':
    main()
