from mesa import Agent
import numpy as np
from typing import Optional, Tuple, List
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
    """Tourist that moves by maximizing a utility combining crowd density,
    directional persistence and a small exploration term.

    The agent replaces the previous FSM with a scored neighbor selection.
    """

    def __init__(self, model, p_litter: float = 0.2, *, crowd_radius: int = 2, crowd_weight: float = 1.0,
                 persistence_weight: float = 0.6, explore_prob: float = 0.12, beta: float = 2.0,
                 center_weight: float = 0.5):
        super().__init__(model, p_litter=p_litter)
        self.direction: Optional[Coord] = None
        self.crowd_radius = crowd_radius
        self.crowd_weight = crowd_weight
        self.persistence_weight = persistence_weight
        self.explore_prob = explore_prob
        self.beta = beta
        self.center_weight = center_weight

    def _manhattan(self, a: Coord, b: Coord) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _score_candidate(self, candidate: Coord) -> float:
        """Compute utility for moving to `candidate` cell.

        Higher is better. Components:
        - crowd: number of agents near candidate (linear)
        - persistence: bonus if candidate continues current direction
        - small random noise for tie-breaking and exploration
        """
        # crowd signal (nearby agents) with concave transform to reduce marginal pull
        raw_count = float(self.model.local_density(candidate, radius=self.crowd_radius))
        crowd = float(np.log1p(raw_count))

        # directional persistence: favor continuing the current direction
        persistence = 0.0
        if self.direction is not None:
            keep_candidate = (self.pos[0] + self.direction[0], self.pos[1] + self.direction[1])
            if candidate == keep_candidate:
                persistence = 1.0

        # center bias: prefer cells closer to geometric center of the map
        try:
            h = float(self.model.city.height)
            w = float(self.model.city.width)
            center_r = (h - 1.0) / 2.0
            center_c = (w - 1.0) / 2.0
            dist_center = abs(candidate[0] - center_r) + abs(candidate[1] - center_c)
            center_bonus = self.center_weight * (1.0 / (1.0 + dist_center))
        except Exception:
            center_bonus = 0.0

        # small noise; keep it tiny relative to other weights
        noise = self.random.random() * 1e-3

        score = (self.crowd_weight * crowd
                 + self.persistence_weight * persistence
                 + center_bonus
                 + noise)
        return score

    def _choose_best_neighbor(self) -> Optional[Coord]:
        neighbors = self.model.city.get_neighbors(self.pos)
        if not neighbors:
            return None

        # Occasionally explore a random neighbor regardless of score
        if self.random.random() < self.explore_prob:
            return self.random.choice(neighbors)

        # Softmax (Boltzmann) sampling to avoid deterministic traps
        scores = [self._score_candidate(n) for n in neighbors]
        # numeric stability: subtract max
        max_s = max(scores)
        exps = [float(np.exp(self.beta * (s - max_s))) for s in scores]
        total = sum(exps)
        if total <= 0:
            return self.random.choice(neighbors)

        # sample according to weights
        r = self.random.random() * total
        cum = 0.0
        for weight, n in zip(exps, neighbors):
            cum += weight
            if r <= cum:
                return n
        return neighbors[-1]

    def step(self):
        next_pos = self._choose_best_neighbor()
        if next_pos is not None:
            self.direction = (next_pos[0] - self.pos[0], next_pos[1] - self.pos[1])
            self.pos = next_pos

        # Litter behavior carried from Human
        self.litter()

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
        self.direction: Optional[Coord] = None

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
            if bin_coord in self.model.claimed_bins:
                continue

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

        if best_bin is not None:
            self.model.claimed_bins.add(best_bin)

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

            next_pos = self.path.pop(0)
            self.direction = (next_pos[0] - self.pos[0], next_pos[1] - self.pos[1])
            self.pos = next_pos

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
        if self.target_bin in self.model.claimed_bins:
            self.model.claimed_bins.remove(self.target_bin)

        self.target_bin = None
        self.target_stop = None
        self.path = []

    def step(self) -> None:
        """Main truck behavior called once per simulation step."""

        if self.is_full():
            if self.at_depot():
                self.dump_at_depot()
                self.clear_target()
            else:
                if not self.path:
                    self.plan_path_to(self.depot)
                self.move_along_path()
            return
        
        if self.target_bin is not None:
            if self.at_target_bin():
                self.collect_from_target_bin()
            else:
                self.move_along_path()
            return
        
        self.find_target_bin()

        if self.target_bin is not None:
            self.move_along_path()

class PathPlanner(Agent):

    def __init__(self, model):
        super().__init__(model)

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

            next_pos = self.path.pop(0)
            self.direction = (next_pos[0] - self.pos[0], next_pos[1] - self.pos[1])
            self.pos = next_pos
    




class ServiceAgent(PathPlanner):

    def __init__(self, model, capacity, speed:int=1, random_patrol:bool=True):
        super().__init__(model)
        self.init_pos = model.city.random_passable_cell()
        self.pos = self.init_pos

        self.capacity = capacity
        self.load: int = 0

        self.speed: int = speed
        self.path:List = []

        self.direction: Optional[Coord] = None

        self.random_patrol_enabled:bool = random_patrol

        self.target_waste: Optional[Coord] = None
        self.target_bin: Optional[Coord] = None

    def remaining_capacity(self) -> int:
        return self.capacity - self.load
    
    def is_full(self)-> bool:
        return self.load >= self.capacity
    
    def has_space(self) -> bool:
        return self.remaining_capacity()>0
    
    def distance_to(self, coord: Coord) -> int:
        r1, c1 = self.pos
        r2, c2 = coord

        return abs(r1 - r2) + abs(c1 - c2)
    
    def find_nearest_target(self, targets: List[Coord]) -> Optional[Coord]:
        best_target: Optional[Coord] = None
        best_path: List[Coord] = []
        best_distance: float = float("inf")

        for target in targets:
            path = self.model.city.shortest_path(self.pos, target)

            if not path:
                continue

            distance = len(path)

            if distance < best_distance:
                best_distance = distance
                best_target = target
                best_path = path

        self.path = best_path

        return best_target
    
    def find_nearest_waste(self) -> Optional[Coord]:
        waste_cells = np.argwhere(self.model.city.waste > 0)

        targets: List[Coord] = []

        for r, c in waste_cells:
            targets.append((int(r), int(c)))

        self.target_waste = self.find_nearest_target(targets)

        return self.target_waste
    
    def find_nearest_bin(self) -> Optional[Coord]:
        targets: List[Coord] = []

        for bin_coord, info in self.model.city.bins.items():
            capacity = info.get("capacity", 0)
            load = info.get("load", 0)

            if capacity <= 0:
                continue

            if load >= capacity:
                continue

            targets.append(bin_coord)

        self.target_bin = self.find_nearest_target(targets)

        return self.target_bin
    
    def pick_waste(self) -> None:
        if not self.has_space():
            return

        available = self.model.city.waste[self.pos]

        if available <= 0:
            return

        space = self.remaining_capacity()
        picked = min(available, space)

        self.model.city.waste[self.pos] -= picked
        self.load += picked

        if self.model.city.waste[self.pos] <= 0:
            self.target_waste = None
    
    def empty_waste(self) -> None:
        if self.target_bin is None:
            return

        if self.pos != self.target_bin:
            return

        if self.load <= 0:
            return

        bin_info = self.model.city.bins.get(self.target_bin)

        if bin_info is None:
            self.target_bin = None
            return

        bin_capacity = bin_info.get("capacity", 0)
        bin_load = bin_info.get("load", 0)

        if bin_capacity <= 0:
            return

        bin_space = bin_capacity - bin_load

        if bin_space <= 0:
            return

        dumped = min(self.load, bin_space)

        bin_info["load"] += dumped
        self.load -= dumped

        if self.load <= 0:
            self.target_bin = None
            
    def random_patrol(self):
        pass

    def nearest_waste_patrol(self):
        pass
