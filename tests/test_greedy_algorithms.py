import pytest

from src.core.graph import Graph
from src.algorithms.greedy_signals import GreedySignalOptimizer
from src.algorithms.greedy_preemption import GreedyPreemptionSystem
from src.models.responses import RouteResult

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
