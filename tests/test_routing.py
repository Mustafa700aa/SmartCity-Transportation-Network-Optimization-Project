import math
import pytest

from src.core.graph import Graph
from src.core.weight_engine import WeightEngine
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter

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
