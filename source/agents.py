from mesa import Agent
from typing import Optional, Tuple

Coord = Tuple[int, int]

class LocalAgent(Agent):
    """Simple human that moves randomly on streets and occasionally litters."""

    def __init__(self, model, p_litter: float = 0.03, keep_direction_prob: float = 0.65, max_wander_distance: Optional[int] = None):
        super().__init__(model)
        self.init_pos = model.city.random_passable_cell()
        self.pos = self.init_pos
        self.p_litter = p_litter
        self.keep_direction_prob = keep_direction_prob
        # Use Manhattan radius to keep the agent from wandering too far from start.
        if max_wander_distance is None:
            max_wander_distance = 4
        self.max_wander_distance = max_wander_distance
        self.direction: Optional[Coord] = None

    def _manhattan(self, a: Coord, b: Coord) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def step(self):
        # Move with directional persistence while respecting wander radius.
        neighbors = self.model.city.get_neighbors(self.pos)
        valid_neighbors = [n for n in neighbors if self._manhattan(n, self.init_pos) <= self.max_wander_distance]

        if valid_neighbors:
            keep_candidate = None
            if self.direction is not None:
                keep_candidate = (self.pos[0] + self.direction[0], self.pos[1] + self.direction[1])

            if keep_candidate in valid_neighbors and self.random.random() < self.keep_direction_prob:
                next_pos = keep_candidate
            else:
                alternatives = [n for n in valid_neighbors if n != keep_candidate]
                next_pos = self.random.choice(alternatives if alternatives else valid_neighbors)

            self.direction = (next_pos[0] - self.pos[0], next_pos[1] - self.pos[1])
            self.pos = next_pos
            
        # If a bin is close enough, deposit there; otherwise litter on the street.
        nearby_bin = None
        nearby_distance = None
        for bin_coord in self.model.city.bins.keys():
            distance = self._manhattan(self.pos, bin_coord)
            if distance <= 3 and (nearby_distance is None or distance < nearby_distance):
                nearby_bin = bin_coord
                nearby_distance = distance

        if self.random.random() < self.p_litter:
            if nearby_bin is not None:
                self.model.city.deposit_to_bin(nearby_bin, 1)
            else:
                self.model.city.add_waste(self.pos, 1)
