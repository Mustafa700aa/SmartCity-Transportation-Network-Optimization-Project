import pytest

from src.core.graph import Graph
from src.algorithms.dp_maintenance import DPMaintenanceOptimizer

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
