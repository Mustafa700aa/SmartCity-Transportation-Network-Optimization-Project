"""
src/models/entities.py
Pure data structures — no calculations, no graph logic, no I/O.
Single Responsibility: hold domain data fields only.
"""
from __future__ import annotations
from dataclasses import dataclass, field


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
