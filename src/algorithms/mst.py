from __future__ import annotations

from src.core.graph import Graph
from src.models.entities import Edge
from src.models.responses import MSTResult

class _UnionFind:

    def __init__(self, nodes):
        self._parent: dict[str, str] = {n: n for n in nodes}
        self._rank:   dict[str, int] = {n: 0  for n in nodes}

    def find(self, x: str) -> str:
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])
        return self._parent[x]

    def union(self, x: str, y: str) -> bool:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1
        return True

    def component_count(self) -> int:
        return len({self.find(n) for n in self._parent})

def kruskal_mst(graph: Graph) -> MSTResult:
    uf = _UnionFind(graph.nodes.keys())

    for edge_type in ('existing_road', 'bus', 'metro'):
        for e in graph.get_edges(edge_type):
            if e.from_id in graph.nodes and e.to_id in graph.nodes:
                uf.union(e.from_id, e.to_id)

    components_before = uf.component_count()

    potential_edges: list[Edge] = graph.get_edges('potential_road')
    potential_edges.sort(key=lambda e: e.construction_cost or 0.0)

    mst_edges:   list[Edge] = []
    total_cost:  float      = 0.0
    skipped:     list[str]  = []

    for edge in potential_edges:
        if uf.union(edge.from_id, edge.to_id):
            mst_edges.append(edge)
            total_cost += edge.construction_cost or 0.0
        else:
            skipped.append(f"{edge.from_id}→{edge.to_id}")

    components_after = uf.component_count()

    return MSTResult(
        mst_edges          = mst_edges,
        total_cost         = total_cost,
        nodes_covered      = len(graph.nodes),
        fully_connected    = (components_after == 1),
        skipped_edges      = skipped,
        components_before  = components_before,
        components_after   = components_after,
    )
