from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from src.models.entities import Edge

@dataclass
class RouteResult:
    path:            List[str]     = field(default_factory=list)
    total_time_h:    float         = math.inf
    total_time_min:  float         = math.inf
    total_dist_km:   float         = 0.0
    iterations:      int           = 0
    time_of_day:     str           = 'morning'
    edge_types_used: List[str]     = field(default_factory=list)
    hops:            int           = 0
    found:           bool          = False
    error:           Optional[str] = None
    segments:        List[dict]    = field(default_factory=list)

@dataclass
class MSTResult:
    mst_edges:         List['Edge'] = field(default_factory=list)
    total_cost:        float        = 0.0
    nodes_covered:     int          = 0
    fully_connected:   bool         = False
    skipped_edges:     List[str]    = field(default_factory=list)
    components_before: int          = 0
    components_after:  int          = 0

@dataclass
class PreemptionEvent:
    step:             int           # Position in path (1-based)
    node_id:          str           # Intersection node ID
    node_name:        str           # Human-readable name
    node_type:        str           # e.g. 'Residential', 'Mixed', 'Medical', etc.
    signal_forced:    str           # Always 'GREEN' (the greedy override)
    congestion_level: str           # FREE / LIGHT / MODERATE / HEAVY / GRIDLOCK
    traffic_volume:   float         # vehicles/hour at time_of_day (0 if no data)
    delay_saved_sec:  int           # Estimated seconds saved for ambulance
    edge_type_in:     Optional[str] # Type of edge used to arrive at this node
    edge_type_out:    Optional[str] # Type of edge used to leave this node
    cumulative_saved_sec: int       # Running total of seconds saved so far
    note:             str = ''      # Extra context (start/end/intermediate)

@dataclass
class PreemptionLog:
    route_path:         List[str]            # Node IDs in ambulance path
    time_of_day:        str
    total_nodes:        int
    overrides_applied:  int
    total_delay_saved_sec: int
    fully_cleared:      bool                 # True if all signals were overridden
    events:             List[PreemptionEvent] = field(default_factory=list)
    warnings:           List[str]            = field(default_factory=list)

@dataclass
class GreenSlot:
    road_id:        str    # e.g. "1-3"
    from_node:      str    # upstream node ID
    from_name:      str    # upstream node name
    traffic_flow:   float  # vehicles/hour at scheduling time
    green_duration: int    # seconds of green time allocated
    priority_rank:  int    # 1 = highest priority (most congested)

@dataclass
class GreenLightSchedule:
    node_id:        str
    node_name:      str
    slots:          List['GreenSlot']
    total_time:     int              # seconds (== cycle_duration)
    time_of_day:    str
    incoming_roads: int
    analysis:       str = field(default="")

@dataclass
class TransitRouteAllocation:
    route_id:           str           # e.g. "BR1" or "ML1"
    line_name:          str           # human-readable name
    edge_type:          str           # 'bus' or 'metro'
    from_id:            str
    to_id:              str
    distance_km:        float
    daily_passengers:   float         # raw demand from data
    original_fleet:     int           # buses_assigned before DP
    allocated_fleet:    int           # fleet units assigned by DP
    throughput_score:   float         # passengers served per fleet unit
    wait_time_min:      float         # estimated average wait time

@dataclass
class TransitScheduleResult:
    time_of_day:        str
    available_fleet:    int
    total_routes:       int
    fleet_assigned:     int
    total_throughput:   float         # total passengers served
    avg_wait_time_min:  float         # fleet-weighted average wait
    allocations:        List['TransitRouteAllocation'] = field(default_factory=list)
    dp_table_size:      int           = 0       # rows × cols for complexity note
    analysis:           str           = ''

@dataclass
class MaintenanceCandidate:
    road_id:            str           # e.g. "1-3"
    from_name:          str
    to_name:            str
    distance_km:        float
    condition:          float         # 1-10 scale
    repair_cost_megp:   float         # Million EGP
    traffic_benefit:    float         # total veh/h across all periods
    selected:           bool          # True if chosen by DP

@dataclass
class MaintenanceResult:
    max_budget_megp:    float
    total_candidates:   int
    selected_count:     int
    total_cost_megp:    float
    total_benefit:      float         # total traffic served by repaired roads
    budget_utilization: float         # percentage of budget used
    candidates:         List['MaintenanceCandidate'] = field(default_factory=list)
    dp_table_size:      int           = 0
    analysis:           str           = ''

