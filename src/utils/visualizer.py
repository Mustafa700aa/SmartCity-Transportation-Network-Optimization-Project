"""
src/utils/visualizer.py
Visualization layer: renders the multi-layer transportation graph.
Single Responsibility: drawing only. No data loading, no weight calculation.
Replaces the former Graph.plot() method.
"""
from __future__ import annotations
import matplotlib.pyplot as plt

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine


def plot_graph(
    graph: Graph,
    show_labels:    bool  = True,
    show_potential: bool  = True,
    annotate:       str   = 'all',
    figsize:        tuple = (18, 11),
    node_size:      int   = 80,
    time_of_day:    str   = 'morning',
) -> None:
    """
    Render the Cairo transportation graph using Matplotlib.
    Replaces the former Graph.plot() method.
    """
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
        for source, marker, color, scale in [
            ('neighborhood', 'o', 'black',   1.0),
            ('facility',     's', 'dimgray', 1.2),
        ]:
            pts = [n for n in graph.nodes.values() if n.source == source]
            if pts:
                ax.scatter([n.x for n in pts], [n.y for n in pts],
                           s=node_size * scale, marker=marker, color=color,
                           edgecolors='white', linewidths=0.7, zorder=4, label=source)
        if show_labels:
            for n in graph.nodes.values():
                if annotate == 'facilities'    and n.source != 'facility':    continue
                if annotate == 'neighborhoods' and n.source != 'neighborhood': continue
                dx, dy, fs = (0.006, 0.0025, 9) if n.source == 'facility' else (0.003, 0.0015, 10)
                ax.text(n.x + dx, n.y + dy, n.id, fontsize=fs, zorder=5,
                        bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none', alpha=0.55))
        if focus:
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
