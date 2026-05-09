from dataclasses import dataclass
from typing import Tuple

Coord = Tuple[int, int]

@dataclass
class Bin:
    id: int
    coord: Coord
    capacity: int = 50
    load: int = 0

    def deposit(self, amount: int) -> int:
        free = self.capacity - self.load
        accepted = min(free, amount)
        self.load += accepted
        return accepted

    def collect(self, amount: int) -> int:
        taken = min(self.load, amount)
        self.load -= taken
        return taken
