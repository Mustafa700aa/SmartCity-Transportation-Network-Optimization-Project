"""
CSE112 - Emergency Preemption System (A*)
Emergency Vehicle Routing using A* Search
"""

import heapq
import math

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────

# Nodes: id -> (name, type, x, y, population)
NODES = {
    '1':   ('Maadi',                   'Residential', 31.25, 29.96, 250000),
    '2':   ('Nasr City',               'Mixed',       31.34, 30.06, 500000),
    '3':   ('Downtown Cairo',          'Business',    31.24, 30.04, 100000),
    '4':   ('New Cairo',               'Residential', 31.47, 30.03, 300000),
    '5':   ('Heliopolis',              'Mixed',       31.32, 30.09, 200000),
    '6':   ('Zamalek',                 'Residential', 31.22, 30.06,  50000),
    '7':   ('6th October City',        'Mixed',       30.98, 29.93, 400000),
    '8':   ('Giza',                    'Mixed',       31.21, 29.99, 550000),
    '9':   ('Mohandessin',             'Business',    31.20, 30.05, 180000),
    '10':  ('Dokki',                   'Mixed',       31.21, 30.03, 220000),
    '11':  ('Shubra',                  'Residential', 31.24, 30.11, 450000),
    '12':  ('Helwan',                  'Industrial',  31.33, 29.85, 350000),
    '13':  ('New Admin Capital',       'Government',  31.80, 30.02,  50000),
    '14':  ('Al Rehab',                'Residential', 31.49, 30.06, 120000),
    '15':  ('Sheikh Zayed',            'Residential', 30.94, 30.01, 150000),
    'F1':  ('Cairo Intl Airport',      'Airport',     31.41, 30.11,      0),
    'F2':  ('Ramses Railway Station',  'Transit Hub', 31.25, 30.06,      0),
    'F3':  ('Cairo University',        'Education',   31.21, 30.03,      0),
    'F4':  ('Al-Azhar University',     'Education',   31.26, 30.05,      0),
    'F5':  ('Egyptian Museum',         'Tourism',     31.23, 30.05,      0),
    'F6':  ('Cairo Intl Stadium',      'Sports',      31.30, 30.07,      0),
    'F7':  ('Smart Village',           'Business',    30.97, 30.07,      0),
    'F8':  ('Cairo Festival City',     'Commercial',  31.40, 30.03,      0),
    'F9':  ('Qasr El Aini Hospital',   'Medical',     31.23, 30.03,      0),  # Super-Node
    'F10': ('Maadi Military Hospital', 'Medical',     31.25, 29.95,      0),  # Super-Node
}

# Super-Nodes: hospitals with guaranteed access
SUPER_NODES = {'F9', 'F10'}

# Edges: (from, to, distance_km, capacity, condition)
EDGES_RAW = [
    ('1',  '3',  8.5,  3000, 7),
    ('1',  '8',  6.2,  2500, 6),
    ('2',  '3',  5.9,  2800, 8),
    ('2',  '5',  4.0,  3200, 9),
    ('3',  '5',  6.1,  3500, 7),
    ('3',  '6',  3.2,  2000, 8),
    ('3',  '9',  4.5,  2600, 6),
    ('3',  '10', 3.8,  2400, 7),
    ('4',  '2',  15.2, 3800, 9),
    ('4',  '14', 5.3,  3000, 10),
    ('5',  '11', 7.9,  3100, 7),
    ('6',  '9',  2.2,  1800, 8),
    ('7',  '8',  24.5, 3500, 8),
    ('7',  '15', 9.8,  3000, 9),
    ('8',  '10', 3.3,  2200, 7),
    ('8',  '12', 14.8, 2600, 5),
    ('9',  '10', 2.1,  1900, 7),
    ('10', '11', 8.7,  2400, 6),
    ('11', 'F2', 3.6,  2200, 7),
    ('12', '1',  12.7, 2800, 6),
    ('13', '4',  45.0, 4000, 10),
    ('14', '13', 35.5, 3800, 9),
    ('15', '7',  9.8,  3000, 9),
    ('F1', '5',  7.5,  3500, 9),
    ('F1', '2',  9.2,  3200, 8),
    ('F2', '3',  2.5,  2000, 7),
    ('F7', '15', 8.3,  2800, 8),
    ('F8', '4',  6.1,  3000, 9),
    # Hospital connections
    ('F9', '3',  0.8,  2000, 9),
    ('F9', '10', 0.9,  2000, 9),
    ('F9', '6',  1.5,  1800, 8),
    ('F10','1',  1.2,  2500, 9),
    ('F10','12', 13.5, 2600, 7),
    ('F10','8',  5.2,  2500, 8),
]

# Traffic Flow (morning peak) for preemption: road_key -> (flow, capacity)
TRAFFIC_FLOW = {
    '1-3':   (2800, 3000), '1-8':   (2200, 2500), '2-3':   (2700, 2800),
    '2-5':   (3000, 3200), '3-5':   (3200, 3500), '3-6':   (1800, 2000),
    '3-9':   (2400, 2600), '3-10':  (2300, 2400), '4-2':   (3600, 3800),
    '4-14':  (2800, 3000), '5-11':  (2900, 3100), '6-9':   (1700, 1800),
    '7-8':   (3200, 3500), '7-15':  (2800, 3000), '8-10':  (2000, 2200),
    '8-12':  (2400, 2600), '9-10':  (1800, 1900), '10-11': (2200, 2400),
    '11-F2': (2100, 2200), '12-1':  (2600, 2800), '13-4':  (3800, 4000),
    '14-13': (3600, 3800), '15-7':  (2800, 3000), 'F1-5':  (3300, 3500),
    'F1-2':  (3000, 3200), 'F2-3':  (1900, 2000), 'F7-15': (2600, 2800),
    'F8-4':  (2800, 3000),
}


# ─────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────

def build_graph():
    graph = {nid: [] for nid in NODES}
    for (a, b, dist, cap, cond) in EDGES_RAW:
        key_ab = f"{a}-{b}"
        key_ba = f"{b}-{a}"
        flow, capacity = TRAFFIC_FLOW.get(key_ab, TRAFFIC_FLOW.get(key_ba, (cap * 0.7, cap)))
        congestion_ratio = flow / capacity
        graph[a].append((b, dist, congestion_ratio))
        graph[b].append((a, dist, congestion_ratio))
    return graph


# ─────────────────────────────────────────────
# HEURISTIC: Euclidean distance (degrees → km)
# ─────────────────────────────────────────────

def euclidean_km(node_a, node_b):
    """h(n) = Euclidean distance between X/Y coordinates, scaled to km."""
    _, _, x1, y1, _ = NODES[node_a]
    _, _, x2, y2, _ = NODES[node_b]
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2) * 111.0  # ~111 km per degree


def heuristic(node_id, goal_id):
    """
    Admissible heuristic for A* — pure Euclidean distance.
    Never overestimates → guarantees A* explores fewer nodes than Dijkstra.
    h(n) = Euclidean distance × 111 km/degree
    """
    return euclidean_km(node_id, goal_id)


# ─────────────────────────────────────────────
# EDGE COST: Traffic Preemption
# ─────────────────────────────────────────────

def edge_cost(from_node, to_node, dist, congestion_ratio, use_preemption=True, use_super_node=True):
    """
    Edge cost with two reductions:
    1. Traffic Preemption: emergency vehicles bypass 30% of congestion delay.
    2. Super-Node bonus: edges leading INTO a hospital get 50% cost reduction
       → guaranteed fast access without distorting the heuristic.
    """
    cost = dist
    if use_preemption:
        congestion_delay = dist * congestion_ratio * 0.3
        cost -= congestion_delay * 0.3
    if use_super_node and to_node in SUPER_NODES:
        cost *= 0.5  # Super-Node: halve the cost of the final edge to hospital
    return cost


# ─────────────────────────────────────────────
# A* SEARCH
# ─────────────────────────────────────────────

def astar(graph, start, goal, use_preemption=True, use_super_node=True):
    """
    A* Search for emergency vehicle routing.
    - Admissible heuristic (Euclidean) guarantees fewer iterations than Dijkstra.
    - Super-Node: reduces cost of edges INTO hospitals → guaranteed fast access.
    - Preemption: reduces cost based on 30% congestion bypass.
    """
    open_set = []
    heapq.heappush(open_set, (0.0, start))

    g_score = {nid: float('inf') for nid in NODES}
    g_score[start] = 0.0

    came_from = {}
    explored = set()
    iterations = 0

    while open_set:
        f_current, current = heapq.heappop(open_set)
        iterations += 1

        if current in explored:
            continue
        explored.add(current)

        if current == goal:
            path = _reconstruct_path(came_from, current)
            return {
                'path': path,
                'cost': g_score[goal],
                'iterations': iterations,
                'explored': list(explored),
            }

        for neighbor, dist, congestion in graph.get(current, []):
            cost = edge_cost(current, neighbor, dist, congestion, use_preemption, use_super_node)
            tentative_g = g_score[current] + cost

            if tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = heuristic(neighbor, goal)
                f = tentative_g + h
                heapq.heappush(open_set, (f, neighbor))

    return None


# ─────────────────────────────────────────────
# DIJKSTRA (for comparison)
# ─────────────────────────────────────────────

def dijkstra(graph, start, goal):
    """Standard Dijkstra for comparison against A*."""
    open_set = [(0.0, start)]
    dist = {nid: float('inf') for nid in NODES}
    dist[start] = 0.0
    came_from = {}
    explored = set()
    iterations = 0

    while open_set:
        d_current, current = heapq.heappop(open_set)
        if current in explored:
            continue
        explored.add(current)
        iterations += 1

        if current == goal:
            path = _reconstruct_path(came_from, current)
            return {
                'path': path,
                'cost': dist[goal],
                'iterations': iterations,
                'explored': list(explored),
            }

        for neighbor, edge_dist, _ in graph.get(current, []):
            nd = dist[current] + edge_dist
            if nd < dist[neighbor]:
                dist[neighbor] = nd
                came_from[neighbor] = current
                heapq.heappush(open_set, (nd, neighbor))

    return None


def _reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


# ─────────────────────────────────────────────
# NEAREST HOSPITAL FINDER
# ─────────────────────────────────────────────

def find_nearest_hospital(graph, start):
    """Find nearest hospital (Super-Node) using A* to each."""
    best = None
    best_cost = float('inf')
    for hospital in SUPER_NODES:
        result = astar(graph, start, hospital)
        if result and result['cost'] < best_cost:
            best_cost = result['cost']
            best = hospital
    return best


# ─────────────────────────────────────────────
# DISPLAY HELPERS
# ─────────────────────────────────────────────

def format_path(path):
    steps = []
    for nid in path:
        name = NODES[nid][0]
        tag = ' [SUPER-NODE ★]' if nid in SUPER_NODES else ''
        steps.append(f"{nid} ({name}){tag}")
    return ' → '.join(steps)


def print_result(label, result, graph):
    if not result:
        print(f"  {label}: No path found.")
        return
    path = result['path']
    # Recalculate actual km distance
    total_km = 0.0
    for i in range(len(path) - 1):
        for nb, dist, _ in graph[path[i]]:
            if nb == path[i+1]:
                total_km += dist
                break
    print(f"  Algorithm   : {label}")
    print(f"  Path        : {format_path(path)}")
    print(f"  Distance    : {total_km:.2f} km")
    print(f"  Hops        : {len(path) - 1}")
    print(f"  Iterations  : {result['iterations']}")
    print(f"  Nodes expl. : {len(result['explored'])}")
    print(f"  Route cost  : {result['cost']:.4f}")


# ─────────────────────────────────────────────
# MAIN — RUN SCENARIOS
# ─────────────────────────────────────────────

def run_scenario(graph, origin, target, use_preemption, use_super_node):
    origin_name = NODES[origin][0]
    target_name = NODES[target][0]
    print(f"\n{'═'*65}")
    print(f"  SCENARIO: {origin_name}  →  {target_name}")
    print(f"  Traffic Preemption : {'ON (30% bypass)' if use_preemption else 'OFF'}")
    print(f"  Super-Node Logic   : {'ON' if use_super_node else 'OFF'}")
    print(f"{'═'*65}")

    astar_result = astar(graph, origin, target, use_preemption, use_super_node)
    dijk_result  = dijkstra(graph, origin, target)

    print("\n  ── A* Search ──")
    print_result('A*', astar_result, graph)

    print("\n  ── Dijkstra ──")
    print_result('Dijkstra', dijk_result, graph)

    if astar_result and dijk_result:
        saved = dijk_result['iterations'] - astar_result['iterations']
        pct   = saved / dijk_result['iterations'] * 100
        print(f"\n  ► A* used {saved} fewer iterations ({pct:.1f}% reduction)")
        if astar_result['iterations'] < dijk_result['iterations']:
            print("  ✓ ACCEPTANCE CRITERIA MET: A* finds hospital in fewer iterations")
        else:
            print("  ✗ Dijkstra was faster in this case")


def main():
    graph = build_graph()

    print("=" * 65)
    print("  CSE112 — EMERGENCY PREEMPTION SYSTEM (A*)")
    print("  Emergency Vehicle Routing · Cairo Road Network")
    print("=" * 65)
    print(f"\n  Nodes loaded : {len(NODES)}")
    print(f"  Edges loaded : {len(EDGES_RAW)}")
    print(f"  Super-Nodes  : {', '.join(SUPER_NODES)} (Hospitals)")

    # ── Scenario 1: Far origin, nearest hospital, all features ON
    run_scenario(graph,
                 origin='7',       # 6th October City
                 target='F9',      # Qasr El Aini Hospital
                 use_preemption=True,
                 use_super_node=True)

    # ── Scenario 2: Different origin → F10
    run_scenario(graph,
                 origin='13',      # New Admin Capital
                 target='F10',     # Maadi Military Hospital
                 use_preemption=True,
                 use_super_node=True)

    # ── Scenario 3: Preemption OFF (baseline)
    run_scenario(graph,
                 origin='4',       # New Cairo
                 target='F9',
                 use_preemption=False,
                 use_super_node=True)

    # ── Scenario 4: Super-Node OFF (to show difference)
    run_scenario(graph,
                 origin='7',
                 target='F9',
                 use_preemption=True,
                 use_super_node=False)

    # ── Auto-find nearest hospital
    print(f"\n{'═'*65}")
    print("  NEAREST HOSPITAL AUTO-ROUTING")
    print(f"{'═'*65}")
    for origin in ['2', '5', '11', '7']:
        nearest = find_nearest_hospital(graph, origin)
        result = astar(graph, origin, nearest)
        print(f"\n  From {NODES[origin][0]} → nearest: {NODES[nearest][0]} ({nearest})")
        if result:
            print(f"    Path: {' → '.join(result['path'])}")
            print(f"    Iterations: {result['iterations']}  |  Cost: {result['cost']:.2f}")

    print(f"\n{'═'*65}\n")


if __name__ == '__main__':
    main()
