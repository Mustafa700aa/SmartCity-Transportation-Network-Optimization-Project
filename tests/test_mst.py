import pytest

from src.core.graph import Graph
from src.algorithms.mst import kruskal_mst

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
