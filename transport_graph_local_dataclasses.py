from __future__ import annotations
import argparse, csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import matplotlib.pyplot as plt


@dataclass
class Node:
    id: str
    name: str
    source: str
    type: str
    x: float
    y: float
    population: int | None = None


@dataclass
class Edge:
    from_id: str
    to_id: str
    edge_type: str
    source: str
    distance_km: float | None = None
    capacity: float | None = None
    condition: float | None = None
    construction_cost: float | None = None
    traffic_flow: dict[str, float] = field(default_factory=dict)
    demand: float | None = None
    route_id: str | None = None
    line_name: str | None = None
    buses_assigned: int | None = None
    daily_passengers: float | None = None


@dataclass
class Route:
    route_id: str
    route_type: str
    stops: list[str]
    daily_passengers: float
    buses_assigned: int | None = None
    name: str | None = None


class Graph:
    VALID_TIME_OF_DAY = ('morning', 'afternoon', 'evening', 'night')
    TIME_OF_DAY_ALIASES = {
        'morning': 'morning',
        'morning peak': 'morning',
        'am peak': 'morning',
        'afternoon': 'afternoon',
        'evening': 'evening',
        'evening peak': 'evening',
        'pm peak': 'evening',
        'night': 'night',
    }

    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.adj_list: dict[str, list[tuple[str, Edge]]] = defaultdict(list)
        self.adj_matrix: dict[str, dict[str, dict[str, list[Edge]]]] = defaultdict(dict)
        self.routes: dict[str, Route] = {}
        self.traffic: dict[tuple[str, str], dict[str, float]] = {}
        self.demand: dict[tuple[str, str], float] = {}
        self.weight_cache: dict[tuple, float] = {}
        self.warnings: list[str] = []

    @staticmethod
    def sid(v): return str(v).strip()
    @staticmethod
    def ek(a, b): return tuple(sorted((a, b)))
    @staticmethod
    def seq(v): return [x.strip() for x in str(v).split(',') if x.strip()]

    @classmethod
    def normalize_time_of_day(cls, time_of_day):
        key = ' '.join(str(time_of_day).strip().lower().replace('_', ' ').replace('-', ' ').split())
        t = cls.TIME_OF_DAY_ALIASES.get(key)
        if t is None:
            raise ValueError(f"Invalid time_of_day '{time_of_day}'. Expected one of: {', '.join(cls.VALID_TIME_OF_DAY)}")
        return t

    def read(self, folder, name):
        path = Path(folder) / name
        if not path.exists(): raise FileNotFoundError(f'Missing required file: {path}')
        with path.open('r', encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))

    def dist(self, a, b):
        na, nb = self.nodes.get(a), self.nodes.get(b)
        if not na or not nb: return None
        dx, dy = (na.x - nb.x) * 96.0, (na.y - nb.y) * 111.0
        return (dx * dx + dy * dy) ** 0.5

    def add_node(self, **kw):
        node = Node(**kw)
        self.nodes[node.id] = node
        # Keep adjacency structures pre-seeded for all known IDs.
        _ = self.adj_list[node.id]
        _ = self.adj_matrix[node.id]

    def add_edge(self, **kw):
        edge = Edge(**kw)
        self.edges.append(edge)
        self.adj_list[edge.from_id].append((edge.to_id, edge))
        self.adj_list[edge.to_id].append((edge.from_id, edge))
        self.adj_matrix.setdefault(edge.from_id, {}).setdefault(edge.to_id, {}).setdefault(edge.edge_type, []).append(edge)
        self.adj_matrix.setdefault(edge.to_id, {}).setdefault(edge.from_id, {}).setdefault(edge.edge_type, []).append(edge)
        self.weight_cache.clear()

    def get_edges(self, edge_type=None): return [e for e in self.edges if edge_type in (None, e.edge_type)]

    def neighbors(self, node_id, edge_types=None):
        node_id = self.sid(node_id)
        entries = self.adj_list.get(node_id, [])
        if edge_types is None:
            return entries
        if isinstance(edge_types, str):
            allowed = {edge_types}
        else:
            allowed = set(edge_types)
        return [(nbr, edge) for nbr, edge in entries if edge.edge_type in allowed]

    def get_edge_types_between(self, from_id, to_id):
        from_id, to_id = self.sid(from_id), self.sid(to_id)
        return sorted(self.adj_matrix.get(from_id, {}).get(to_id, {}).keys())

    @classmethod
    def load(cls, folder):
        g = cls()
        for r in g.read(folder, 'Neighborhoods.csv'):
            g.add_node(id=g.sid(r['ID']), name=r['Name'].strip(), source='neighborhood', type=r['Type'].strip(), x=float(r['X-coordinate']), y=float(r['Y-coordinate']), population=int(r['Population']) if r.get('Population') else None)
        for r in g.read(folder, 'Facilities.csv'):
            g.add_node(id=g.sid(r['ID']), name=r['Name'].strip(), source='facility', type=r['Type'].strip(), x=float(r['X-coordinate']), y=float(r['Y-coordinate']))
        for r in g.read(folder, 'Traffic_Flow.csv'):
            try:
                a, b = map(g.sid, str(r['RoadID']).split('-', 1))
                g.traffic[g.ek(a, b)] = {'morning': float(r['Morning_Peak(veh/h)']), 'afternoon': float(r['Afternoon(veh/h)']), 'evening': float(r['Evening_Peak(veh/h)']), 'night': float(r['Night(veh/h)'])}
            except Exception:
                g.warnings.append(f"Invalid RoadID: {r.get('RoadID')}")
        for r in g.read(folder, 'Transport_Demand.csv'):
            g.demand[(g.sid(r['FromID']), g.sid(r['ToID']))] = float(r['Daily_Passengers'])
        for r in g.read(folder, 'Existing_Roads.csv'):
            a, b = g.sid(r['FromID']), g.sid(r['ToID'])
            g.add_edge(from_id=a, to_id=b, edge_type='existing_road', source='Existing_Roads.csv', distance_km=float(r['Distance(km)']), capacity=float(r['Current_Capacity(vehicles/hour)']), condition=float(r['Condition(1-10)']), traffic_flow=g.traffic.get(g.ek(a, b), {}), demand=g.demand.get((a, b)) or g.demand.get((b, a)))
        for r in g.read(folder, 'Potential_Roads.csv'):
            a, b = g.sid(r['FromID']), g.sid(r['ToID'])
            g.add_edge(from_id=a, to_id=b, edge_type='potential_road', source='Potential_Roads.csv', distance_km=float(r['Distance(km)']), capacity=float(r['Estimated_Capacity(vehicles/hour)']), construction_cost=float(r['Construction_Cost(Million_EGP)']), demand=g.demand.get((a, b)) or g.demand.get((b, a)))
        for fname, et, rid, seq, name in [('Bus_Routes.csv', 'bus', 'RouteID', 'Stops', None), ('Metro_Lines.csv', 'metro', 'LineID', 'Stations', 'Name')]:
            for r in g.read(folder, fname):
                route = Route(route_id=g.sid(r[rid]), route_type=et, stops=g.seq(r[seq]), daily_passengers=float(r['Daily_Passengers']), buses_assigned=int(r['Buses_Assigned']) if 'Buses_Assigned' in r and r['Buses_Assigned'] else None, name=r.get(name, '').strip() if name else None)
                g.routes[route.route_id] = route
                for s in route.stops:
                    if s not in g.nodes: g.warnings.append(f'{et} stop not found: {s}')
                for a, b in zip(route.stops, route.stops[1:]):
                    g.add_edge(from_id=a, to_id=b, edge_type=et, source=fname, distance_km=g.dist(a, b), route_id=route.route_id, line_name=route.name, buses_assigned=route.buses_assigned, daily_passengers=route.daily_passengers)
        return g

    def summary(self):
        counts = {}
        for e in self.edges: counts[e.edge_type] = counts.get(e.edge_type, 0) + 1
        return {'nodes': len(self.nodes), 'routes': len(self.routes), 'edges_total': len(self.edges), 'edges_by_type': counts, 'warnings': len(self.warnings)}

    def get_edge_weight(self, edge: Edge, time_of_day='morning'):
        t, d = self.normalize_time_of_day(time_of_day), edge.distance_km or 1.0
        cache_key = (
            edge.from_id,
            edge.to_id,
            edge.edge_type,
            t,
            d,
            edge.capacity,
            edge.condition,
            edge.construction_cost,
            edge.daily_passengers,
            edge.buses_assigned,
            edge.traffic_flow.get(t),
        )
        cached = self.weight_cache.get(cache_key)
        if cached is not None:
            return cached

        if edge.edge_type == 'existing_road':
            traffic, cap, cond = edge.traffic_flow.get(t), edge.capacity or 2500.0, edge.condition or 7.0
            ratio = max(0.0, (traffic or 0.0) / cap) if cap else 0.0
            # BPR travel-time model: T = T0 * (1 + alpha * (V/C)^beta).
            alpha, beta = 0.15, 4.0
            bpr_factor = 1.0 + alpha * (ratio ** beta)
            cond_factor = 1.0 + max(0.0, 7.0 - cond) * 0.02
            value = (d / 38.0) * bpr_factor * cond_factor
        elif edge.edge_type == 'potential_road':
            value = d / 42.0
        elif edge.edge_type == 'bus':
            p, buses = edge.daily_passengers or 0.0, edge.buses_assigned
            value = (d / 24.0) * (1.0 + min(1.2, p / 100000.0)) * (max(0.65, 1.15 - min(buses, 40) * 0.012) if buses else 1.0)
        elif edge.edge_type == 'metro':
            value = (d / 45.0) * (1.0 + min(0.6, (edge.daily_passengers or 0.0) / 3000000.0))
        else:
            value = d / 30.0

        self.weight_cache[cache_key] = value
        return value

    def plot(self, show_labels=True, show_potential=True, annotate='all', figsize=(18, 11), node_size=80, time_of_day='morning'):
        t = self.normalize_time_of_day(time_of_day)
        styles = {'existing_road': ('#4c97d8', 2.3, 0.8, 2), 'potential_road': ('#f0a04b', 1.5, 0.35, 1), 'bus': ('#3ba34d', 2.0, 0.72, 2), 'metro': ('#c83a3a', 2.4, 0.85, 3)}
        layers = ['existing_road', 'potential_road', 'bus', 'metro']
        if not show_potential: layers.remove('potential_road')
        summary = self.summary()
        counts = summary['edges_by_type']
        total_buses = sum((r.buses_assigned or 0) for r in self.routes.values() if r.route_type == 'bus')
        route_palette = plt.get_cmap('tab20').colors
        windows = [('Transportation Multi-Layer Graph (Combined)', None)] + [(f'Path Highlight: {et}', et) for et in layers[:4]]
        for title, focus in windows:
            fig, ax = plt.subplots(figsize=figsize)
            seen = set()
            for et in layers:
                c, lw, a, z = styles[et]
                for e in self.get_edges(et):
                    na, nb = self.nodes.get(e.from_id), self.nodes.get(e.to_id)
                    if not na or not nb: continue
                    if focus and et != focus:
                        ax.plot([na.x, nb.x], [na.y, nb.y], color='lightgray', linewidth=0.9, alpha=0.25, zorder=0)
                        continue
                    label_key = et
                    if et in ('bus', 'metro') and e.route_id:
                        c = route_palette[sum(map(ord, e.route_id)) % len(route_palette)]
                        label_key = f"{et}:{e.line_name or e.route_id}"
                    label = label_key if label_key not in seen else None
                    ax.plot([na.x, nb.x], [na.y, nb.y], color=c, linewidth=(lw + 0.7 if focus else lw), alpha=(0.95 if focus else a), zorder=(z + 2 if focus else z), label=label)
                    seen.add(label_key)
            for source, marker, color, scale in [('neighborhood', 'o', 'black', 1.0), ('facility', 's', 'dimgray', 1.2)]:
                pts = [n for n in self.nodes.values() if n.source == source]
                if pts: ax.scatter([n.x for n in pts], [n.y for n in pts], s=node_size * scale, marker=marker, color=color, edgecolors='white', linewidths=0.7, zorder=4, label=source)
            if show_labels:
                for n in self.nodes.values():
                    if annotate == 'facilities' and n.source != 'facility': continue
                    if annotate == 'neighborhoods' and n.source != 'neighborhood': continue
                    dx, dy, fs = (0.006, 0.0025, 9) if n.source == 'facility' else (0.003, 0.0015, 10)
                    ax.text(n.x + dx, n.y + dy, n.id, fontsize=fs, zorder=5, bbox=dict(boxstyle='round,pad=0.12', facecolor='white', edgecolor='none', alpha=0.55))
            if focus:
                stats_text = (
                    f"time_of_day: {t}\nnodes: {summary['nodes']}\nroutes: {summary['routes']}\nfocus_edges: {counts.get(focus, 0)}\n"
                    f"buses_total: {total_buses}\ntotal_edges: {summary['edges_total']}"
                )
            else:
                stats_text = (
                    f"time_of_day: {t}\nnodes: {summary['nodes']}\nroutes: {summary['routes']}\n"
                    f"existing: {counts.get('existing_road', 0)}\npotential: {counts.get('potential_road', 0)}\n"
                    f"bus: {counts.get('bus', 0)}\nmetro: {counts.get('metro', 0)}\n"
                    f"buses_total: {total_buses}\ntotal_edges: {summary['edges_total']}"
                )
            ax.set_title(f'{title} [{t}]', fontsize=14, pad=12)
            ax.set_xlabel('X-coordinate'); ax.set_ylabel('Y-coordinate'); ax.grid(True, linestyle='--', alpha=0.18); ax.legend(loc='upper right', frameon=True)
            ax.text(1.005, 0.5, stats_text, transform=ax.transAxes, va='center', ha='left', fontsize=11, clip_on=False, bbox=dict(boxstyle='round,pad=0.35', facecolor='white', edgecolor='gray', alpha=0.95))
            fig.tight_layout(rect=(0, 0, 0.9, 1))
        plt.show()


def main():
    p = argparse.ArgumentParser(description='Compact local transportation graph with dataclasses')
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--hide-potential', action='store_true')
    p.add_argument('--hide-labels', action='store_true')
    p.add_argument('--annotate', choices=['all', 'facilities', 'neighborhoods'], default='all')
    p.add_argument('--time-of-day', default='morning')
    args = p.parse_args()
    g = Graph.load(args.data_dir)
    print('Graph summary:', g.summary())
    if g.warnings:
        print('Validation warnings:'); [print('-', w) for w in g.warnings]
    g.plot(show_labels=not args.hide_labels, show_potential=not args.hide_potential, annotate=args.annotate, time_of_day=args.time_of_day)

if __name__ == '__main__':
    main()
