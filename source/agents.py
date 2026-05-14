from mesa import Agent
from typing import Optional, Tuple, List

Coord = Tuple[int, int]

class Human(Agent):
    """Simple human that moves randomly on streets and occasionally litters."""

    def __init__(self, model, p_litter: float = 0.2):
        super().__init__(model)
        self.init_pos = model.city.random_passable_cell()
        self.pos = self.init_pos
        self.p_litter = p_litter

    def litter(self):
        # If a bin is close enough, deposit there; otherwise litter on the street.
        nearby_bin = None
        nearby_distance = None
        for bin_coord in self.model.city.bins.keys():
            distance = abs(self.pos[0] - bin_coord[0]) + abs(self.pos[1] - bin_coord[1])
            if distance <= 3 and (nearby_distance is None or distance < nearby_distance):
                nearby_bin = bin_coord
                nearby_distance = distance

        if self.random.random() < self.p_litter:
            if nearby_bin is not None:
                self.model.city.deposit_to_bin(nearby_bin, 1)
            else:
                self.model.city.add_waste(self.pos, 1)

class LocalAgent(Human):
    """Simple human that moves randomly on streets and occasionally litters."""

    def __init__(self, model, p_litter: float = 0.05, keep_direction_prob: float = 0.65, max_wander_distance: Optional[int] = None):
        super().__init__(model, p_litter)
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

class TouristAgent(Human):
    def __init__(self, model, p_litter: float = 0.2, keep_direction_prob: float = 0.7):
        super().__init__(model, p_litter=p_litter)
        # FSM states: 'to_center', 'roam_center', 'to_area', 'roam_area'
        self.state = 'to_center'
        self.direction: Optional[Coord] = None
        self.keep_direction_prob = keep_direction_prob
        self.roam_min = 3
        self.roam_max = 8
        self.roam_steps_remaining = 0
        self.explore_prob = 0.15
        self.area_size = 7
        # Precompute center region
        self.center_region = self.model.city.get_center_region()
        self.area_region: List[Coord] = []

    def _manhattan(self, a: Coord, b: Coord) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _choose_area_region(self) -> List[Coord]:
        # Attempt to pick a region box around a random passable cell that has passable cells.
        attempts = 5
        for _ in range(attempts):
            center = self.model.city.random_passable_cell()
            region = self.model.city.get_region_by_box(center, self.area_size)
            # Prefer regions that are not entirely inside center
            if region and not all(self.model.city.is_in_center(c) for c in region):
                return region
        # Fallback: any non-empty region near a random passable cell
        center = self.model.city.random_passable_cell()
        return self.model.city.get_region_by_box(center, self.area_size)

    def _enter_roam(self, region: List[Coord]):
        self.roam_steps_remaining = self.random.randint(self.roam_min, self.roam_max)
        self.direction = None

    def _heading_step(self, target_region: List[Coord]):
        if not target_region:
            return
        # choose a concrete target cell inside region
        target = self.random.choice(target_region)
        neighbors = self.model.city.get_neighbors(self.pos)
        if not neighbors:
            return
        # pick neighbor that minimizes manhattan distance to target, with small explore_prob
        best = min(neighbors, key=lambda n: self._manhattan(n, target))
        if self.random.random() < self.explore_prob:
            # explore: pick a random neighbor (possible different from best)
            choice = self.random.choice(neighbors)
        else:
            choice = best
        self.direction = (choice[0] - self.pos[0], choice[1] - self.pos[1])
        self.pos = choice

    def _roam_step(self, region: List[Coord]):
        # directional persistence while staying inside region
        neighbors = self.model.city.get_neighbors(self.pos)
        valid_neighbors = [n for n in neighbors if n in region]
        if not valid_neighbors:
            return
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

    def step(self):
        # Finite-state behavior: head -> roam center -> head -> roam area -> repeat
        if self.state == 'to_center':
            # If already in center region, switch to roaming
            if self.pos in self.center_region:
                self.state = 'roam_center'
                self._enter_roam(self.center_region)
            else:
                self._heading_step(self.center_region)
                if self.pos in self.center_region:
                    self.state = 'roam_center'
                    self._enter_roam(self.center_region)

        elif self.state == 'roam_center':
            self._roam_step(self.center_region)
            self.roam_steps_remaining -= 1
            if self.roam_steps_remaining <= 0:
                # pick a specific area to visit next
                self.area_region = self._choose_area_region()
                self.state = 'to_area'

        elif self.state == 'to_area':
            if not self.area_region:
                self.area_region = self._choose_area_region()
            if self.pos in self.area_region:
                self.state = 'roam_area'
                self._enter_roam(self.area_region)
            else:
                self._heading_step(self.area_region)
                if self.pos in self.area_region:
                    self.state = 'roam_area'
                    self._enter_roam(self.area_region)

        elif self.state == 'roam_area':
            self._roam_step(self.area_region)
            self.roam_steps_remaining -= 1
            if self.roam_steps_remaining <= 0:
                # head back to center
                self.state = 'to_center'

        # Litter behavior carried from Human
        self.litter()