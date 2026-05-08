import math

import pytest

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.models.entities import Node, Edge
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter
from src.algorithms.mst import kruskal_mst
from src.algorithms.dp_maintenance import DPMaintenanceOptimizer
from src.algorithms.greedy_signals import GreedySignalOptimizer
from src.algorithms.greedy_preemption import GreedyPreemptionSystem
from src.models.responses import RouteResult


# =====================================================================
# 🗺️ 1. DIJKSTRA & A* LOGICAL CORRECTNESS TESTS
# =====================================================================

def test_logic_1_shortest_vs_fastest_path_traffic_bias():
    g = Graph()
    g.add_node(id='A', name='Origin', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='Destination', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='C', name='Detour', source='test', type='intersection', x=0.0, y=0.0)

    g.add_edge(from_id='A', to_id='B', edge_type='existing_road', source='test',
               distance_km=5.0, capacity=1000.0,
               traffic_flow={'morning': 4000.0})

    g.add_edge(from_id='A', to_id='C', edge_type='existing_road', source='test',
               distance_km=7.5, capacity=1000.0,
               traffic_flow={'morning': 0.0})
    g.add_edge(from_id='C', to_id='B', edge_type='existing_road', source='test',
               distance_km=7.5, capacity=1000.0,
               traffic_flow={'morning': 0.0})

    we = WeightEngine(strategy='bpr')
    router = DijkstraRouter(g, weight_engine=we)
    res = router.find_shortest_path('A', 'B', time_of_day='morning')

    assert res.found is True
    assert res.path == ['A', 'C', 'B']
    assert res.total_dist_km == 15.0


def test_logic_2_strict_edge_avoidance():
    g = Graph()
    for n in ['A', 'B', 'C', 'D']:
        g.add_node(id=n, name=n, source='test', type='intersection', x=0.0, y=0.0)

    g.add_edge(from_id='A', to_id='C', edge_type='existing_road', source='test', distance_km=5.0)
    g.add_edge(from_id='C', to_id='B', edge_type='existing_road', source='test', distance_km=5.0)

    g.add_edge(from_id='A', to_id='D', edge_type='existing_road', source='test', distance_km=10.0)
    g.add_edge(from_id='D', to_id='B', edge_type='existing_road', source='test', distance_km=10.0)

    router = DijkstraRouter(g)
    
    avoid = {tuple(sorted(['C', 'B']))}
    res = router.find_shortest_path('A', 'B', avoid_edges=avoid)

    assert res.found is True
    assert 'C' not in res.path
    assert res.path == ['A', 'D', 'B']
    assert res.total_dist_km == 20.0


def test_logic_3_astar_heuristic_admissibility():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='B', source='test', type='intersection', x=10.0, y=10.0)
    g.add_node(id='C', name='C', source='test', type='intersection', x=20.0, y=20.0)
    g.add_node(id='D', name='D', source='test', type='intersection', x=30.0, y=30.0)
    g.add_node(id='E', name='E', source='test', type='intersection', x=0.0, y=30.0)
    g.add_node(id='F', name='F', source='test', type='intersection', x=30.0, y=0.0)

    g.add_edge(from_id='A', to_id='B', edge_type='existing_road', source='test', distance_km=1500.0)
    g.add_edge(from_id='B', to_id='C', edge_type='existing_road', source='test', distance_km=1500.0)
    g.add_edge(from_id='C', to_id='D', edge_type='existing_road', source='test', distance_km=1500.0)
    
    g.add_edge(from_id='A', to_id='E', edge_type='existing_road', source='test', distance_km=2500.0)
    g.add_edge(from_id='E', to_id='D', edge_type='existing_road', source='test', distance_km=2500.0)
    g.add_edge(from_id='A', to_id='F', edge_type='existing_road', source='test', distance_km=2500.0)
    g.add_edge(from_id='F', to_id='D', edge_type='existing_road', source='test', distance_km=2500.0)

    we = WeightEngine()
    dijkstra = DijkstraRouter(g, weight_engine=we)
    astar = AStarRouter(g, weight_engine=we)

    res_d = dijkstra.find_shortest_path('A', 'D')
    res_a = astar.find_shortest_path('A', 'D')

    assert res_d.found is True
    assert res_a.found is True
    
    assert res_a.total_time_min == pytest.approx(res_d.total_time_min)
    assert res_a.iterations <= res_d.iterations


def test_logic_4_trivial_and_disconnected_graphs():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='B', source='test', type='intersection', x=1.0, y=1.0)

    router = DijkstraRouter(g)

    res_trivial = router.find_shortest_path('A', 'A')
    assert res_trivial.found is True
    assert res_trivial.hops == 0
    assert res_trivial.total_dist_km == 0.0
    assert res_trivial.total_time_h == 0.0

    res_disc = router.find_shortest_path('A', 'B')
    assert res_disc.found is False
    assert "No path" in res_disc.error
    assert res_disc.path == []


# =====================================================================
# 🌲 2. KRUSKAL MST LOGICAL CORRECTNESS TESTS
# =====================================================================

def test_logic_5_pre_union_component_preservation():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='B', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='C', name='C', source='test', type='intersection', x=0.0, y=0.0)

    g.add_edge(from_id='A', to_id='B', edge_type='existing_road', source='test')

    g.add_edge(from_id='B', to_id='C', edge_type='potential_road', source='test', construction_cost=10.0)
    g.add_edge(from_id='A', to_id='C', edge_type='potential_road', source='test', construction_cost=20.0)

    res = kruskal_mst(g)
    
    assert len(res.mst_edges) == 1
    assert (res.mst_edges[0].from_id == 'B' and res.mst_edges[0].to_id == 'C') or \
           (res.mst_edges[0].from_id == 'C' and res.mst_edges[0].to_id == 'B')
    assert res.skipped_edges != [] 


def test_logic_6_high_population_access_priority():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0, population=10000)
    g.add_node(id='B', name='B', source='test', type='intersection', x=0.0, y=0.0, population=100)
    g.add_node(id='C', name='C', source='test', type='intersection', x=0.0, y=0.0, population=50)

    cost_bc = 5.0
    cost_ab = 100.0

    adj_cost_bc = cost_bc / (g.nodes['B'].population + g.nodes['C'].population)
    adj_cost_ab = cost_ab / (g.nodes['A'].population + g.nodes['B'].population)

    g.add_edge(from_id='B', to_id='C', edge_type='potential_road', source='test', construction_cost=adj_cost_bc)
    g.add_edge(from_id='A', to_id='B', edge_type='potential_road', source='test', construction_cost=adj_cost_ab)

    res = kruskal_mst(g)

    assert res.fully_connected is True
    assert len(res.mst_edges) == 2
    assert adj_cost_ab < adj_cost_bc


def test_logic_7_cycle_freedom_tree_property():
    g = Graph()
    nodes = ['A', 'B', 'C', 'D', 'E']
    for n in nodes:
        g.add_node(id=n, name=n, source='test', type='intersection', x=0.0, y=0.0)

    cost = 1.0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            g.add_edge(from_id=nodes[i], to_id=nodes[j], edge_type='potential_road',
                       source='test', construction_cost=cost)
            cost += 1.0

    res = kruskal_mst(g)
    
    assert len(res.mst_edges) == len(nodes) - 1
    assert res.fully_connected is True


# =====================================================================
# 🚌 3. DYNAMIC PROGRAMMING LOGICAL CORRECTNESS TESTS
# =====================================================================

def test_logic_8_maintenance_optimizer_01_knapsack():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='B', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='C', name='C', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='D', name='D', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='E', name='E', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='F', name='F', source='test', type='intersection', x=0.0, y=0.0)
    
    # Candidate 1
    g.add_edge(from_id='A', to_id='B', edge_type='existing_road', source='test',
               condition=8.0, distance_km=5.0, # Cost = 5.0 * 3.0 = 15.0M
               traffic_flow={'morning': 100.0}) # Benefit = 100 * 1 = 100
    # Candidate 2
    g.add_edge(from_id='C', to_id='D', edge_type='existing_road', source='test',
               condition=8.0, distance_km=3.333333333, # Cost ~ 10.0M
               traffic_flow={'morning': 60.0}) # Benefit = 60
    # Candidate 3
    g.add_edge(from_id='E', to_id='F', edge_type='existing_road', source='test',
               condition=8.0, distance_km=3.333333333, # Cost ~ 10.0M
               traffic_flow={'morning': 55.0}) # Benefit = 55

    optimizer = DPMaintenanceOptimizer(g)
    res = optimizer.optimize(max_budget_megp=20.0)

    assert res.selected_count == 2
    assert res.total_benefit == pytest.approx(115.0)
    assert res.total_cost_megp <= 20.0


def test_logic_9_zero_and_infinite_budget_bounds():
    g = Graph()
    g.add_node(id='A', name='A', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='B', name='B', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='C', name='C', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='D', name='D', source='test', type='intersection', x=0.0, y=0.0)

    g.add_edge(from_id='A', to_id='B', edge_type='existing_road', source='test',
               condition=1.0, distance_km=1.0, traffic_flow={'morning': 500.0})
    g.add_edge(from_id='C', to_id='D', edge_type='existing_road', source='test',
               condition=1.0, distance_km=1.0, traffic_flow={'morning': 500.0})

    optimizer = DPMaintenanceOptimizer(g)

    res_zero = optimizer.optimize(max_budget_megp=0.0)
    assert res_zero.selected_count == 0
    assert res_zero.total_cost_megp == 0.0

    res_inf = optimizer.optimize(max_budget_megp=99999.0)
    assert res_inf.selected_count == 2
    assert res_inf.total_cost_megp > 0.0


# =====================================================================
# 🚦 4. GREEDY ALGORITHMS LOGICAL CORRECTNESS TESTS
# =====================================================================

def test_logic_10_traffic_signal_optimizer_cycle_conservation():
    g = Graph()
    g.add_node(id='Intersection', name='Main Square', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='N1', name='N1', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='N2', name='N2', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='N3', name='N3', source='test', type='intersection', x=0.0, y=0.0)

    g.add_edge(from_id='N1', to_id='Intersection', edge_type='existing_road', source='test',
               traffic_flow={'morning': 5000.0})
    g.add_edge(from_id='N2', to_id='Intersection', edge_type='existing_road', source='test',
               traffic_flow={'morning': 500.0})
    g.add_edge(from_id='N3', to_id='Intersection', edge_type='existing_road', source='test',
               traffic_flow={'morning': 10.0})

    optimizer = GreedySignalOptimizer(g)
    
    cycle = 120
    min_green = 15
    sched = optimizer.compute_schedule('Intersection', time_of_day='morning', 
                                       cycle_duration=cycle, min_green=min_green)
    
    assert len(sched.slots) == 3
    
    total_allocated = sum(slot.green_duration for slot in sched.slots)
    
    assert total_allocated == cycle
    for slot in sched.slots:
        assert slot.green_duration >= min_green


def test_logic_11_emergency_preemption_override():
    g = Graph()
    g.add_node(id='Start', name='S', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='Middle', name='M', source='test', type='intersection', x=0.0, y=0.0)
    g.add_node(id='End', name='E', source='test', type='intersection', x=0.0, y=0.0)
    
    g.add_edge(from_id='Start', to_id='Middle', edge_type='existing_road', source='test',
               distance_km=5.0, capacity=1000.0, traffic_flow={'morning': 5000.0}) 
    g.add_edge(from_id='Middle', to_id='End', edge_type='existing_road', source='test',
               distance_km=5.0, capacity=1000.0, traffic_flow={'morning': 5000.0}) 

    from src.algorithms.dijkstra_router import DijkstraRouter
    from src.core.weight_engine import WeightEngine
    
    we = WeightEngine(strategy='bpr')
    router = DijkstraRouter(g, weight_engine=we)
    route = router.find_shortest_path('Start', 'End', time_of_day='morning')
    
    assert route.found is True

    preempt = GreedyPreemptionSystem(g)
    log = preempt.generate_preemption_log(route)

    assert log.fully_cleared is True
    assert log.overrides_applied == 3  
    
    for ev in log.events:
        assert ev.delay_saved_sec >= 90  
        assert ev.signal_forced == 'GREEN'
