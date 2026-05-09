from mesa import Model
from city import CityMap
from agents import HumanAgent
from bins import Bin
import numpy as np
from typing import Dict, List, Any, Tuple


class CityModel(Model):
    def __init__(self, width: int = 20, height: int = 20, n_humans: int = 20, seed: int = None):
        super().__init__(seed=seed)
        self.width = width
        self.height = height
        self.city = CityMap(height, width, seed=seed)
        # place some bins on random passable cells
        for _ in range(max(1, (width * height) // 100)):
            coord = self.city.random_passable_cell()
            self.city.add_bin(coord, capacity=100)
        # create human agents using Mesa 3.5.1 factory method
        HumanAgent.create_agents(model=self, n=n_humans)

    def step(self):
        # Mesa 3.5.1: random activation via shuffle_do
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
            agents.append((int(a.unique_id), atype, (pos if pos is None else (int(pos[0]), int(pos[1]))), payload))

        metrics = {
            'total_waste': int(self.total_waste()),
            'num_agents': len(self.agents),
            'time': float(self.time),
        }

        return {
            'time': float(self.time),
            'waste': waste,
            'street_mask': street_mask,
            'bins': bins,
            'agents': agents,
            'metrics': metrics,
        }

    def visual_snapshots(self, steps: int) -> List[Dict[str, Any]]:
        """Run the model for `steps` steps and return a list of visual snapshots (non-destructive for UI)."""
        snaps = []
        for _ in range(steps):
            self.step()
            snaps.append(self.get_visual_state())
        return snaps
