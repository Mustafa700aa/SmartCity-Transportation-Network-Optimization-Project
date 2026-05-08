from __future__ import annotations
import matplotlib.pyplot as plt

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.models.responses import RouteResult, MSTResult

def plot_graph(
    graph: Graph,
    show_labels:    bool  = True,
    show_potential: bool  = True,
    annotate:       str   = 'all',
    figsize:        tuple = (18, 11),
    node_size:      int   = 80,
    time_of_day:    str   = 'morning',
    route_result:   RouteResult | None = None,
    mst_result:     MSTResult   | None = None,
) -> None:
    t = WeightEngine.normalize_time_of_day(time_of_day)
    styles = {
        'existing_road': ('#4c97d8', 2.3, 0.8, 2),
        'potential_road': ('#f0a04b', 1.5, 0.35, 1),
        'bus':   ('#3ba34d', 2.0, 0.72, 2),
        'metro': ('#c83a3a', 2.4, 0.85, 3),
    }
    layers = ['existing_road', 'potential_road', 'bus', 'metro']
    if not show_potential:
        layers.remove('potential_road')
    summary      = graph.summary()
    counts       = summary['edges_by_type']
    total_buses  = sum((r.buses_assigned or 0) for r in graph.routes.values() if r.route_type == 'bus')
    route_palette = plt.get_cmap('tab20').colors

    # Determine which windows to render
    has_overlay = (route_result and route_result.found) or mst_result
    if has_overlay:
        # Only render a single combined window with the overlay
        windows = [('Transportation Graph — Algorithm Result Overlay', None)]
    else:
        windows = [('Transportation Multi-Layer Graph (Combined)', None)] + [
            (f'Path Highlight: {et}', et) for et in layers[:4]
        ]

    for title, focus in windows:
        fig, ax = plt.subplots(figsize=figsize)

        seen = set()
        for et in layers:
            c, lw, a, z = styles[et]
            for e in graph.get_edges(et):
                na, nb = graph.nodes.get(e.from_id), graph.nodes.get(e.to_id)
                if not na or not nb:
                    continue
                if focus and et != focus:
                    ax.plot([na.x, nb.x], [na.y, nb.y], color='lightgray', linewidth=0.9, alpha=0.25, zorder=0)
                    continue
                # Dim base map edges when an overlay is active
                if has_overlay:
                    ax.plot([na.x, nb.x], [na.y, nb.y], color='#b0b0b0',
                            linewidth=1.0, alpha=0.3, zorder=1)
                    continue
                label_key = et
                if et in ('bus', 'metro') and e.route_id:
                    c = route_palette[sum(map(ord, e.route_id)) % len(route_palette)]
                    label_key = f"{et}:{e.line_name or e.route_id}"
                label = label_key if label_key not in seen else None
                ax.plot([na.x, nb.x], [na.y, nb.y], color=c,
                        linewidth=(lw + 0.7 if focus else lw),
                        alpha=(0.95 if focus else a),
                        zorder=(z + 2 if focus else z), label=label)
                seen.add(label_key)

        if route_result and route_result.found and route_result.path:
            _draw_route_overlay(ax, graph, route_result, seen)

        if mst_result and mst_result.mst_edges:
            _draw_mst_overlay(ax, graph, mst_result, seen)

        for source, marker, color, scale in [
            ('neighborhood', 'o', 'black',   1.0),
            ('facility',     's', 'dimgray', 1.2),
        ]:
            pts = [n for n in graph.nodes.values() if n.source == source]
            if pts:
                ax.scatter([n.x for n in pts], [n.y for n in pts],
                           s=node_size * scale, marker=marker, color=color,
                           edgecolors='white', linewidths=0.7, zorder=4, label=source)

        if route_result and route_result.found and route_result.path:
            _draw_route_nodes(ax, graph, route_result, node_size)

        if mst_result and mst_result.mst_edges:
            _draw_mst_nodes(ax, graph, mst_result, node_size)

        if show_labels:
            for n in graph.nodes.values():
                if annotate == 'facilities'    and n.source != 'facility':    continue
                if annotate == 'neighborhoods' and n.source != 'neighborhood': continue
                dx, dy, fs = (0.006, 0.0025, 9) if n.source == 'facility' else (0.003, 0.0015, 10)
                ax.text(n.x + dx, n.y + dy, n.id, fontsize=fs, zorder=5,
                        bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none', alpha=0.55))

        if has_overlay:
            stats_text = _overlay_stats(route_result, mst_result, summary, t)
        elif focus:
            stats_text = (
                f"time_of_day: {t}\nnodes: {summary['nodes']}\nroutes: {summary['routes']}\n"
                f"focus_edges: {counts.get(focus, 0)}\nbuses_total: {total_buses}\n"
                f"total_edges: {summary['edges_total']}"
            )
        else:
            stats_text = (
                f"time_of_day: {t}\nnodes: {summary['nodes']}\nroutes: {summary['routes']}\n"
                f"existing: {counts.get('existing_road', 0)}\npotential: {counts.get('potential_road', 0)}\n"
                f"bus: {counts.get('bus', 0)}\nmetro: {counts.get('metro', 0)}\n"
                f"buses_total: {total_buses}\ntotal_edges: {summary['edges_total']}"
            )
        ax.set_title(f'{title} [{t}]', fontsize=14, pad=12)
        ax.set_xlabel('X-coordinate')
        ax.set_ylabel('Y-coordinate')
        ax.grid(True, linestyle='--', alpha=0.18)
        ax.legend(loc='upper right', frameon=True)
        ax.text(1.005, 0.5, stats_text, transform=ax.transAxes, va='center', ha='left',
                fontsize=11, clip_on=False,
                bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor='gray', alpha=0.95))
        fig.tight_layout(rect=(0, 0, 0.9, 1))
    plt.show()

# These are private helpers — they only draw what is passed to them (SRP).

def _draw_route_overlay(ax, graph: Graph, route: RouteResult, seen: set) -> None:
    path = route.path
    label_added = False
    for i in range(len(path) - 1):
        na = graph.nodes.get(path[i])
        nb = graph.nodes.get(path[i + 1])
        if not na or not nb:
            continue
        label = 'Optimal Route' if not label_added else None
        ax.plot(
            [na.x, nb.x], [na.y, nb.y],
            color='#FF2D2D', linewidth=5, alpha=0.92,
            zorder=10, solid_capstyle='round',
            label=label,
        )
        # Inner glow line for visibility
        ax.plot(
            [na.x, nb.x], [na.y, nb.y],
            color='#FFD700', linewidth=2, alpha=0.7,
            zorder=11, solid_capstyle='round',
        )
        label_added = True
    seen.add('Optimal Route')

def _draw_route_nodes(ax, graph: Graph, route: RouteResult, node_size: int) -> None:
    path = route.path
    if not path:
        return
    # Intermediate waypoints
    for nid in path[1:-1]:
        n = graph.nodes.get(nid)
        if n:
            ax.scatter(n.x, n.y, s=node_size * 2.0, marker='o',
                       color='#FFD700', edgecolors='#FF2D2D',
                       linewidths=2, zorder=12)
    # Start node (green diamond)
    start_n = graph.nodes.get(path[0])
    if start_n:
        ax.scatter(start_n.x, start_n.y, s=node_size * 3.0, marker='D',
                   color='#00E676', edgecolors='black', linewidths=1.5,
                   zorder=13, label=f'Start: {path[0]}')
    # End node (red star)
    end_n = graph.nodes.get(path[-1])
    if end_n:
        ax.scatter(end_n.x, end_n.y, s=node_size * 3.5, marker='*',
                   color='#FF1744', edgecolors='black', linewidths=1.0,
                   zorder=13, label=f'End: {path[-1]}')

def _draw_mst_overlay(ax, graph: Graph, mst: MSTResult, seen: set) -> None:
    label_added = False
    for edge in mst.mst_edges:
        na = graph.nodes.get(edge.from_id)
        nb = graph.nodes.get(edge.to_id)
        if not na or not nb:
            continue
        label = 'MST Infrastructure' if not label_added else None
        ax.plot(
            [na.x, nb.x], [na.y, nb.y],
            color='#00E676', linewidth=4.5, alpha=0.88,
            zorder=10, solid_capstyle='round',
            label=label,
        )
        # Inner line for contrast
        ax.plot(
            [na.x, nb.x], [na.y, nb.y],
            color='#FFFFFF', linewidth=1.5, alpha=0.6,
            zorder=11, solid_capstyle='round',
        )
        label_added = True
    seen.add('MST Infrastructure')

def _draw_mst_nodes(ax, graph: Graph, mst: MSTResult, node_size: int) -> None:
    mst_nids = set()
    for edge in mst.mst_edges:
        mst_nids.add(edge.from_id)
        mst_nids.add(edge.to_id)
    for nid in mst_nids:
        n = graph.nodes.get(nid)
        if n:
            ax.scatter(n.x, n.y, s=node_size * 2.0, marker='h',
                       color='#00E676', edgecolors='#1B5E20',
                       linewidths=1.5, zorder=12)

def _overlay_stats(
    route: RouteResult | None,
    mst: MSTResult | None,
    summary: dict,
    tod: str,
) -> str:
    lines = [f"time_of_day: {tod}", f"nodes: {summary['nodes']}"]
    if route and route.found:
        lines += [
            "",
            "── Route ──",
            f"path: {' → '.join(route.path)}",
            f"hops: {route.hops}",
            f"time: {route.total_time_min:.1f} min",
            f"dist: {route.total_dist_km:.2f} km",
        ]
    if mst and mst.mst_edges:
        lines += [
            "",
            "── MST ──",
            f"edges: {len(mst.mst_edges)}",
            f"cost: {mst.total_cost:.2f} M EGP",
            f"connected: {mst.fully_connected}",
        ]
    return "\n".join(lines)
