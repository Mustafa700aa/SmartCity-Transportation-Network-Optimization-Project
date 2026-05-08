from __future__ import annotations
import csv
from pathlib import Path

from src.core.graph import Graph
from src.models.entities import Route

def _read(folder: Path, name: str) -> list[dict]:
    path = folder / name
    if not path.exists():
        raise FileNotFoundError(f'Missing required file: {path}')
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def load_cairo_graph(data_dir) -> Graph:
    g = Graph()
    folder = Path(data_dir)

    for r in _read(folder, 'Neighborhoods.csv'):
        g.add_node(
            id=g.sid(r['ID']), name=r['Name'].strip(),
            source='neighborhood', type=r['Type'].strip(),
            x=float(r['X-coordinate']), y=float(r['Y-coordinate']),
            population=int(r['Population']) if r.get('Population') else None,
        )
    for r in _read(folder, 'Facilities.csv'):
        g.add_node(
            id=g.sid(r['ID']), name=r['Name'].strip(),
            source='facility', type=r['Type'].strip(),
            x=float(r['X-coordinate']), y=float(r['Y-coordinate']),
        )
    for r in _read(folder, 'Traffic_Flow.csv'):
        try:
            a, b = map(g.sid, str(r['RoadID']).split('-', 1))
            g._set_traffic(g.ek(a, b), {
                'morning':   float(r['Morning_Peak(veh/h)']),
                'afternoon': float(r['Afternoon(veh/h)']),
                'evening':   float(r['Evening_Peak(veh/h)']),
                'night':     float(r['Night(veh/h)']),
            })
        except Exception:
            g.warnings.append(f"Invalid RoadID: {r.get('RoadID')}")

    for r in _read(folder, 'Transport_Demand.csv'):
        g._set_demand((g.sid(r['FromID']), g.sid(r['ToID'])), float(r['Daily_Passengers']))

    for r in _read(folder, 'Existing_Roads.csv'):
        a, b = g.sid(r['FromID']), g.sid(r['ToID'])
        g.add_edge(
            from_id=a, to_id=b, edge_type='existing_road',
            source='Existing_Roads.csv',
            distance_km=float(r['Distance(km)']),
            capacity=float(r['Current_Capacity(vehicles/hour)']),
            condition=float(r['Condition(1-10)']),
            traffic_flow=g.traffic.get(g.ek(a, b), {}),
            demand=g.demand.get((a, b)) or g.demand.get((b, a)),
        )
    for r in _read(folder, 'Potential_Roads.csv'):
        a, b = g.sid(r['FromID']), g.sid(r['ToID'])
        g.add_edge(
            from_id=a, to_id=b, edge_type='potential_road',
            source='Potential_Roads.csv',
            distance_km=float(r['Distance(km)']),
            capacity=float(r['Estimated_Capacity(vehicles/hour)']),
            construction_cost=float(r['Construction_Cost(Million_EGP)']),
            demand=g.demand.get((a, b)) or g.demand.get((b, a)),
        )
    for fname, et, rid, seq_col, name_col in [
        ('Bus_Routes.csv',  'bus',   'RouteID', 'Stops',    None),
        ('Metro_Lines.csv', 'metro', 'LineID',  'Stations', 'Name'),
    ]:
        for r in _read(folder, fname):
            route = Route(
                route_id=g.sid(r[rid]), route_type=et, stops=g.seq(r[seq_col]),
                daily_passengers=float(r['Daily_Passengers']),
                buses_assigned=int(r['Buses_Assigned']) if 'Buses_Assigned' in r and r['Buses_Assigned'] else None,
                name=r.get(name_col, '').strip() if name_col else None,
            )
            g.routes[route.route_id] = route
            for s in route.stops:
                if s not in g.nodes:
                    g.warnings.append(f'{et} stop not found: {s}')
            for a, b in zip(route.stops, route.stops[1:]):
                g.add_edge(
                    from_id=a, to_id=b, edge_type=et, source=fname,
                    distance_km=g.dist(a, b), route_id=route.route_id,
                    line_name=route.name, buses_assigned=route.buses_assigned,
                    daily_passengers=route.daily_passengers,
                )
    return g
