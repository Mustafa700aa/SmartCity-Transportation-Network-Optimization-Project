from __future__ import annotations

import dataclasses
import logging
import math
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.infrastructure.csv_loader import load_cairo_graph
from src.core.graph import Graph
from src.utils.formatters import parse_avoid_edges
from src.core.weight_engine import WeightEngine
from src.algorithms.dijkstra_router import DijkstraRouter
from src.algorithms.astar import AStarRouter
from src.algorithms.mst import kruskal_mst
from src.algorithms.dp_maintenance import DPMaintenanceOptimizer
from src.algorithms.dp_transit_scheduler import DPTransitScheduler

class RouteRequest(BaseModel):
    start_node:  str       = Field(..., description="Origin node ID")
    end_node:    str       = Field(..., description="Destination node ID")
    time_of_day: str       = Field("morning", description="Traffic period")
    avoid_edges: List[str] = Field(default_factory=list,
                                   description="Edges to avoid, e.g. ['1-3', '5-8']")
    weight_mode: str       = Field("bpr", description="Weight strategy: 'bpr' or 'ml'")

class HealthResponse(BaseModel):
    status:      str
    nodes_count: int
    edges_count: int
    routes_count: int

class MaintenanceRequest(BaseModel):
    budget: float = Field(50.0, description="Maximum budget in Million EGP", gt=0)

class TransitRequest(BaseModel):
    time_of_day: str  = Field("morning", description="Traffic period")
    fleet:       int  = Field(50, description="Total available fleet units", gt=0)

_log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    data_dir = Path("data")
    if not data_dir.is_dir():
        data_dir = Path(".")
    app.state.graph = load_cairo_graph(data_dir)
    summary = app.state.graph.summary()
    _log.info("Graph loaded: %s", summary)
    yield

app = FastAPI(
    title="Cairo Smart City Transportation API",
    description="RESTful gateway for routing, MST, and optimization algorithms.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_graph() -> Graph:
    return app.state.graph

def _validate_nodes(graph: Graph, start: str, end: str) -> None:
    sid = graph.sid(start)
    eid = graph.sid(end)
    if sid not in graph.nodes:
        raise HTTPException(status_code=404, detail=f"Start node '{start}' not found in graph.")
    if eid not in graph.nodes:
        raise HTTPException(status_code=404, detail=f"End node '{end}' not found in graph.")

def _sanitize_result(obj) -> dict:
    raw = dataclasses.asdict(obj)

    def _clean(v):
        if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
            return None
        if isinstance(v, tuple):
            return [_clean(item) for item in v]
        if isinstance(v, dict):
            return {k: _clean(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_clean(item) for item in v]
        return v

    return _clean(raw)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    graph = _get_graph()
    summary = graph.summary()
    return HealthResponse(
        status="online",
        nodes_count=summary["nodes"],
        edges_count=summary["edges_total"],
        routes_count=summary["routes"],
    )

@app.post("/api/route")
async def dijkstra_route(req: RouteRequest):
    graph = _get_graph()
    _validate_nodes(graph, req.start_node, req.end_node)

    try:
        WeightEngine.normalize_time_of_day(req.time_of_day)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        we = WeightEngine(strategy=req.weight_mode)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    avoid = parse_avoid_edges(req.avoid_edges)
    router = DijkstraRouter(graph, weight_engine=we)

    result = router.find_shortest_path(
        req.start_node, req.end_node, req.time_of_day, avoid_edges=avoid,
    )
    return _sanitize_result(result)

@app.post("/api/astar")
async def astar_route(req: RouteRequest):
    graph = _get_graph()
    _validate_nodes(graph, req.start_node, req.end_node)

    try:
        WeightEngine.normalize_time_of_day(req.time_of_day)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        we = WeightEngine(strategy=req.weight_mode)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    avoid = parse_avoid_edges(req.avoid_edges)
    router = AStarRouter(graph, weight_engine=we)

    result = router.find_shortest_path(
        req.start_node, req.end_node, req.time_of_day, avoid_edges=avoid,
    )
    return _sanitize_result(result)

@app.get("/api/mst")
async def mst_result():
    graph = _get_graph()
    result = kruskal_mst(graph)
    return _sanitize_result(result)

@app.get("/api/graph")
async def get_graph():
    graph = _get_graph()
    nodes = [dataclasses.asdict(n) for n in graph.nodes.values()]
    edges = []
    for e in graph.edges:
        edges.append({
            "from": e.from_id,
            "to": e.to_id,
            "type": e.edge_type,
            "distance": e.distance_km
        })
    return {"nodes": nodes, "edges": edges}

@app.post("/api/maintenance")
async def maintenance_optimize(req: MaintenanceRequest):
    graph = _get_graph()
    optimizer = DPMaintenanceOptimizer(graph)
    result = optimizer.optimize(max_budget_megp=req.budget)
    return _sanitize_result(result)

@app.post("/api/transit")
async def transit_optimize(req: TransitRequest):
    graph = _get_graph()
    try:
        WeightEngine.normalize_time_of_day(req.time_of_day)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    scheduler = DPTransitScheduler(graph)
    result = scheduler.optimize(time_of_day=req.time_of_day, available_fleet=req.fleet)
    return _sanitize_result(result)
