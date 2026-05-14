from mesa import Agent
from typing import Optional, Tuple, List

Coord = Tuple[int, int]

class LocalAgent(Agent):
    """Simple human that moves randomly on streets and occasionally litters."""

    def __init__(self, model, p_litter: float = 0.7, keep_direction_prob: float = 0.65, max_wander_distance: Optional[int] = None):
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




class TruckAgent(Agent):

    def __init__(self, model, depot:Coord, capacity: int = 500,
                 speed: int = 1, full_threshold: float = 0.8 ):
        super().__init__(model)

        self.pos: Coord = depot
        self.depot: Coord = depot

        self.capacity = capacity
        self.load: int = 0
        self.speed: int = speed

        self.target_bin: Optional[Coord] = None
        self.target_stop: Optional[Coord] = None
        self.path: List[Coord] = []

        self.full_threshold: float = full_threshold

    def remaining_capacity(self) -> int:
        return self.capacity -self.load
    
    def is_full(self) -> bool:
        return self.load >= self.capacity
    
    def at_depot(self) -> bool:
        """Return True if the truck is currently at the depot."""
        return self.depot == self.pos
    
    def at_target_bin(self) -> bool:
        if self.target_bin is None:
            return False

        tr, tc = self.pos
        br, bc = self.target_bin

        distance = abs(tr - br) + abs(tc - bc)

        return distance == 1
    def distance_to(self, coord: Coord) -> int:
        r1, c1 = self.pos
        r2, c2 = coord
        
        return abs(r1-r2) + abs (c1-c2)
    
    def get_bin_stop_cells(self, bin_coord: Coord) -> List[Coord]:
        """Return street cells next to a bin where the truck can stop."""
        r, c = bin_coord

        possible_cells = [
            (r - 1, c),
            (r + 1, c),
            (r, c - 1),
            (r, c + 1),
        ]

        stop_cells = []

        for nr, nc in possible_cells:
            if self.model.city._in_bounds(nr, nc) and self.model.city.street[nr, nc]:
                stop_cells.append((nr, nc))

        return stop_cells

    def find_target_bin(self) -> Optional[Coord]:
        """Find the nearest reachable bin that is full enough to collect."""
        best_bin: Optional[Coord] = None
        best_stop: Optional[Coord] = None
        best_path: List[Coord] = []
        best_distance: float = float("inf")

        for bin_coord, info in self.model.city.bins.items():
            capacity = info.get("capacity", 0)
            load = info.get("load", 0)

            if capacity <= 0:
                continue

            fill_ratio = load / capacity

            if fill_ratio < self.full_threshold:
                continue

            stop_cells = self.get_bin_stop_cells(bin_coord)

            for stop_cell in stop_cells:
                path = self.model.city.shortest_path(self.pos, stop_cell)

                if not path:
                    continue

                distance = len(path)

                if distance < best_distance:
                    best_distance = distance
                    best_bin = bin_coord
                    best_stop = stop_cell
                    best_path = path

        self.target_bin = best_bin
        self.target_stop = best_stop
        self.path = best_path

        return best_bin
    
    def plan_path_to(self, destination: Coord) -> None:
        """Calculate and store a path to the destination."""
        self.path = self.model.city.shortest_path(self.pos, destination)

    def move_along_path(self) -> None:
        """Move along the stored path according to truck speed."""
        if not self.path:
            return
        
        if self.path[0] == self.pos:
            self.path.pop(0)

        for _ in range(self.speed):
            if not self.path:
                break

            self.pos = self.path.pop(0)

    def collect_from_target_bin(self) -> None:
        """Collect waste from the target bin into the truck."""
        if self.target_bin == None:
            return
        
        if not self.at_target_bin():
            return
        
        bin_info = self.model.city.bins.get(self.target_bin)

        if bin_info is None:
            self.clear_target()

        available = bin_info.get("load", 0)
        space = self.remaining_capacity()

        if available <= 0 or space <= 0:
            return

        collected = min(available, space)

        bin_info["load"] -= collected

        self.load += collected 

        if bin_info["load"] <= 0:
            self.clear_target()


    def dump_at_depot(self) -> None:
        """Empty the truck at the depot."""
        if not self.at_depot():
            return
        
        if self.load <= 0:
            return
        
        dumped = self.load
        self.load = 0

        self.model.total_dumped += dumped

    def clear_target(self) -> None:
        """Forget the current target bin and path."""
        pass

    def step(self) -> None:
        """Main truck behavior called once per simulation step."""
        pass

    
        
