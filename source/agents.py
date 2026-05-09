from mesa import Agent
from typing import Tuple

Coord = Tuple[int, int]

class HumanAgent(Agent):
    """Simple human that moves randomly on streets and occasionally litters."""

    def __init__(self, model, p_litter: float = 0.03):
        super().__init__(model)
        self.pos = model.city.random_passable_cell()
        self.p_litter = p_litter

    def step(self):
        # move to a random neighbor if possible
        neighbors = self.model.city.get_neighbors(self.pos)
        if neighbors:
            self.pos = self.random.choice(neighbors)
        # possibly generate waste
        if self.random.random() < self.p_litter:
            self.model.city.add_waste(self.pos, 1)
