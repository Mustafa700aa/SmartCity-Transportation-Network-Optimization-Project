from __future__ import annotations
from collections import defaultdict
from src.models.entities import Node, Edge, Route

class Graph:

    def __init__(self):
        self.nodes:    dict[str, Node]                              = {}
        self.edges:    list[Edge]                                   = []
        self.adj_list: dict[str, list[tuple[str, Edge]]]            = defaultdict(list)
        self.adj_matrix: dict[str, dict[str, dict[str, list[Edge]]]]  = defaultdict(dict)
        self.routes:   dict[str, Route]                             = {}
        self.traffic:  dict[tuple[str, str], dict[str, float]]      = {}
        self.demand:   dict[tuple[str, str], float]                 = {}
        self.warnings: list[str]                                    = []

    @staticmethod
    def sid(v): return str(v).strip()

    @staticmethod
    def ek(a, b): return tuple(sorted((a, b)))

    @staticmethod
    def seq(v): return [x.strip() for x in str(v).split(',') if x.strip()]

    def dist(self, a, b):
        na, nb = self.nodes.get(a), self.nodes.get(b)
        if not na or not nb:
            return None
        dx, dy = (na.x - nb.x) * 96.0, (na.y - nb.y) * 111.0
        return (dx * dx + dy * dy) ** 0.5

    def add_node(self, **kw):
        node = Node(**kw)
        self.nodes[node.id] = node
        # Pre-seed adjacency structures so nodes with no edges are still present.
        if node.id not in self.adj_list:
            self.adj_list[node.id] = []
        if node.id not in self.adj_matrix:
            self.adj_matrix[node.id] = {}

    def add_edge(self, **kw):
        edge = Edge(**kw)
        self.edges.append(edge)
        self.adj_list[edge.from_id].append((edge.to_id, edge))
        self.adj_list[edge.to_id].append((edge.from_id, edge))
        self.adj_matrix.setdefault(edge.from_id, {}).setdefault(edge.to_id, {}).setdefault(edge.edge_type, []).append(edge)
        self.adj_matrix.setdefault(edge.to_id, {}).setdefault(edge.from_id, {}).setdefault(edge.edge_type, []).append(edge)

    def get_edges(self, edge_type=None):
        return [e for e in self.edges if edge_type in (None, e.edge_type)]

    def neighbors(self, node_id, edge_types=None):
        node_id = self.sid(node_id)
        entries = self.adj_list.get(node_id, [])
        if edge_types is None:
            return entries
        allowed = {edge_types} if isinstance(edge_types, str) else set(edge_types)
        return [(nbr, edge) for nbr, edge in entries if edge.edge_type in allowed]

    def get_edge_types_between(self, from_id, to_id):
        from_id, to_id = self.sid(from_id), self.sid(to_id)
        return sorted(self.adj_matrix.get(from_id, {}).get(to_id, {}).keys())

    # ------------------------------------------------------------------
    # Loader-internal setters — called ONLY by infrastructure loaders
    # during graph construction, before the graph is handed to callers.
    # ------------------------------------------------------------------

    def _set_traffic(self, key: tuple, flow: dict[str, float]) -> None:
        """Set traffic flow data for an edge key (loader use only)."""
        self.traffic[key] = flow

    def _set_demand(self, key: tuple, passengers: float) -> None:
        """Set origin-destination demand for a node pair (loader use only)."""
        self.demand[key] = passengers

    def summary(self):
        counts = {}
        for e in self.edges:
            counts[e.edge_type] = counts.get(e.edge_type, 0) + 1
        return {
            'nodes': len(self.nodes),
            'routes': len(self.routes),
            'edges_total': len(self.edges),
            'edges_by_type': counts,
            'warnings': len(self.warnings),
        }
