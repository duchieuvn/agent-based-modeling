from mesa import Model
from city import CityMap
from agents import LocalAgent, TruckAgent
from bins import Bin
import numpy as np
from typing import Dict, List, Any, Tuple, Optional


class CityModel(Model):
    def __init__(self, width: int = 50, height: int = 50, n_humans: int = 20, n_trucks: int = 1, depot_pos = None, seed: int = None):
        super().__init__(seed=seed)
        self.width = width
        self.height = height
        self.total_dumped = 0
        self.claimed_bins = set()

        self.city = CityMap(height, width, seed=seed)

        if depot_pos is None:
            depot_pos = (0, 0)
        
        self.depot = depot_pos

        # place some bins on random passable cells
        for _ in range(max(1, (width * height) // 100)):
            coord = self.city.random_passable_cell()
            self.city.add_bin(coord, capacity=100)
        # create human agents using Mesa 3.5.1 factory method
        LocalAgent.create_agents(model=self, n=n_humans)
        TruckAgent.create_agents(model=self, n=n_trucks, depot=self.depot, capacity = 500, speed = 1, full_threshold = 0.8)

    def step(self):
        # Mesa 3.5.1: random activation via shuffle_do
        self.claimed_bins.clear()
        self.agents.shuffle_do("step")

    def total_waste(self) -> int:
        return self.city.total_waste()

    def get_visual_state(self) -> Dict[str, Any]:
        """Return a read-only snapshot of the model state suitable for visualization.

        Returns a dict with keys:
          - time: model time
          - waste: 2D numpy array of ground waste
          - street_mask: 2D boolean numpy array where True = street/passable
          - bins: list of (r, c, capacity, load)
          - agents: list of (id, type, (r,c), payload)
          - metrics: dict of simple aggregated metrics
        """
        # grid arrays
        waste = np.array(self.city.waste, copy=True)
        street_mask = np.array(self.city.street, copy=True)

        # bins
        bins = []
        for (r, c), info in self.city.bins.items():
            bins.append((int(r), int(c), int(info.get('capacity', 0)), int(info.get('load', 0))))

        # agents
        agents = []
        for a in list(self.agents):
            pos = getattr(a, 'pos', None)
            atype = a.__class__.__name__
            payload = {}
            # include known agent attributes if present
            if hasattr(a, 'p_litter'):
                payload['p_litter'] = float(a.p_litter)
            # agents.append((int(a.unique_id), atype, (pos if pos is None else (int(pos[0]), int(pos[1]))), payload))

            # TruckAgent info
            if atype == "TruckAgent":
                payload["load"] = int(a.load)
                payload["capacity"] = int(a.capacity)
                payload["speed"] = int(a.speed)
                payload["target_bin"] = a.target_bin
                payload["target_stop"] = a.target_stop
                payload["path_length"] = len(a.path)
                payload["direction"] = a.direction
            
            agents.append(
                (
                    int(a.unique_id),
                    atype,
                    pos if pos is None else (int(pos[0]), int(pos[1])),
                    payload
                )
            )
        metrics = {
            'total_waste': int(self.total_waste()),
            'num_agents': len(self.agents),
            'time': float(self.time),
            "total_dumped": int(self.total_dumped),
        }

        return {
            'time': float(self.time),
            'waste': waste,
            'street_mask': street_mask,
            'bins': bins,
            'agents': agents,
            'depot': (int(self.depot[0]), int(self.depot[1])),
            'metrics': metrics,
        }

    def visual_snapshots(self, steps: int) -> List[Dict[str, Any]]:
        """Run the model for `steps` steps and return a list of visual snapshots (non-destructive for UI)."""
        snaps = []
        for _ in range(steps):
            self.step()
            snaps.append(self.get_visual_state())
        return snaps
