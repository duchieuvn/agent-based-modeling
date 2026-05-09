import numpy as np
import networkx as nx
from typing import List, Tuple, Optional

Coord = Tuple[int, int]

class CityMap:
    """Grid-backed city map with optional graph overlay for routing."""

    def __init__(self, height: int, width: int, street_mask: Optional[np.ndarray] = None, seed: Optional[int] = None):
        self.height = height
        self.width = width
        self.rng = np.random.default_rng(seed)
        if street_mask is None:
            self.street = self._generate_random_streets(prob_street=0.6)
        else:
            assert street_mask.shape == (height, width)
            self.street = street_mask.astype(bool)
        self.waste = np.zeros((height, width), dtype=int)
        self.bins = {}  # maps Coord -> {'capacity': int, 'load': int}
        self._graph = None

    def _generate_random_streets(self, prob_street=0.6) -> np.ndarray:
        return self.rng.random((self.height, self.width)) < prob_street

    def add_bin(self, coord: Coord, capacity: int = 50):
        self.bins[coord] = {'capacity': capacity, 'load': 0}

    def add_waste(self, coord: Coord, amount: int = 1):
        r, c = coord
        if not self._in_bounds(r, c):
            return
        self.waste[r, c] += amount

    def collect_from_bin(self, coord: Coord, amount: int) -> int:
        """Attempt to collect `amount` from bin at coord. Returns actually collected."""
        b = self.bins.get(coord)
        if not b:
            return 0
        collected = min(amount, b['load'])
        b['load'] -= collected
        return collected

    def deposit_to_bin(self, coord: Coord, amount: int) -> int:
        b = self.bins.get(coord)
        if not b:
            return 0
        free = b['capacity'] - b['load']
        accepted = min(free, amount)
        b['load'] += accepted
        overflow = amount - accepted
        if overflow > 0:
            # overflow becomes ground waste
            self.add_waste(coord, overflow)
        return accepted

    def get_neighbors(self, coord: Coord, neighborhood: int = 4) -> List[Coord]:
        r, c = coord
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if neighborhood == 8:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbors = []
        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if self._in_bounds(nr, nc) and self.street[nr, nc]:
                neighbors.append((nr, nc))
        return neighbors

    def _in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.height and 0 <= c < self.width

    def random_passable_cell(self) -> Coord:
        coords = np.argwhere(self.street)
        if coords.size == 0:
            raise RuntimeError("No passable (street) cells in map")
        idx = self.rng.integers(0, len(coords))
        r, c = coords[idx]
        return int(r), int(c)

    def grid_to_graph(self) -> nx.Graph:
        if self._graph is not None:
            return self._graph
        G = nx.Graph()
        for r in range(self.height):
            for c in range(self.width):
                if not self.street[r, c]:
                    continue
                G.add_node((r, c))
                for nr, nc in self.get_neighbors((r, c), neighborhood=4):
                    G.add_edge((r, c), (nr, nc), weight=1)
        self._graph = G
        return G

    def shortest_path(self, start: Coord, goal: Coord) -> List[Coord]:
        G = self.grid_to_graph()
        try:
            path = nx.shortest_path(G, start, goal, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def total_waste(self) -> int:
        return int(self.waste.sum() + sum(b['load'] for b in self.bins.values()))
