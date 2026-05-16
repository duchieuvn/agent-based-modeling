from mesa import Model
from city import CityMap
from agents import LocalAgent, TruckAgent, TouristAgent, ServiceAgent
import numpy as np
from typing import Dict, List, Any, Tuple, Optional


class CityModel(Model):
    def __init__(self, width: int = 50, height: int = 50, n_humans: int = 20, n_trucks: int = 1, n_service: int = 20, depot_pos = None, seed: int = None):
        super().__init__(seed=seed)
        self.width = width
        self.height = height
        self.total_dumped = 0
        self.claimed_bins = set()

        self.city = CityMap(height, width, seed=seed)

        self.depot  = self.city.truck_spawn

        # create human agents using Mesa 3.5.1 factory method
        LocalAgent.create_agents(model=self, n=n_humans)

        # place the first bins at the initial positions of the first LocalAgents
        # so the simulation starts with bins anchored to the local population.
        bin_count = max(1, (width * height) // 100)
        local_agents = sorted(
            (agent for agent in self.agents if isinstance(agent, LocalAgent)),
            key=lambda agent: agent.unique_id,
        )

        for agent in local_agents[:bin_count]:
            self.city.add_bin(agent.init_pos, capacity=100)

        while len(self.city.bins) < bin_count:
            coord = self.city.random_passable_cell()
            if coord in self.city.bins:
                continue
            self.city.add_bin(coord, capacity=100)

        TouristAgent.create_agents(model=self, n=int(n_humans*1.5))
        TruckAgent.create_agents(model=self, n=n_trucks, depot=self.depot, capacity = 500, speed = 1, full_threshold = 0.8)
        ServiceAgent.create_agents(model=self, n=n_service, capacity=100, speed=1, behavior = "nearest")

    def step(self):
        # Mesa 3.5.1: random activation via shuffle_do
        self.agents.shuffle_do("step")

    def local_density(self, coord: Tuple[int, int], radius: int = 2) -> int:
        """Return the number of agents within Manhattan `radius` of `coord`.

        This counts all agents that have a `.pos` attribute and are within
        the given Manhattan distance. Use this as a lightweight crowd signal.
        """
        r, c = coord
        count = 0
        for a in list(self.agents):
            pos = getattr(a, "pos", None)
            if pos is None:
                continue
            if abs(pos[0] - r) + abs(pos[1] - c) <= radius:
                count += 1
        return count

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

            # ServiceAgent info
            if atype == "ServiceAgent":
                payload["load"] = int(getattr(a, "load", 0))
                payload["capacity"] = int(getattr(a, "capacity", 0))
                payload["speed"] = int(getattr(a, "speed", 1)) if hasattr(a, "speed") else 1
                payload["target_waste"] = getattr(a, "target_waste", None)
                payload["target_bin"] = getattr(a, "target_bin", None)
                payload["path_length"] = len(getattr(a, "path", []))
                payload["direction"] = getattr(a, "direction", None)
            
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
            'depot_cells': list(self.city.depot_cells),
            'metrics': metrics,
        }

    def visual_snapshots(self, steps: int) -> List[Dict[str, Any]]:
        """Run the model for `steps` steps and return a list of visual snapshots (non-destructive for UI)."""
        snaps = []
        for _ in range(steps):
            self.step()
            snaps.append(self.get_visual_state())
        return snaps
