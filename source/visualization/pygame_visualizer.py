
from __future__ import annotations
import math
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple
import pygame
# ---------------------------------------------------------------------------
# Import setup
# ---------------------------------------------------------------------------
# When this file is run as:
#
#     python source/visualization/pygame_visualizer.py
#
# Python puts the source/visualization/ folder on sys.path, not necessarily the
# source/ folder where model.py lives. Add both common paths so
# `from model import CityModel` works from different working directories.
THIS_FILE = Path(__file__).resolve()
VISUALIZATION_DIR = THIS_FILE.parent
SOURCE_DIR = VISUALIZATION_DIR.parent
PROJECT_ROOT = SOURCE_DIR.parent

for path in (PROJECT_ROOT, SOURCE_DIR):
    path_text = str(path)
    if path.exists() and path_text not in sys.path:
        sys.path.insert(0, path_text)

from model import CityModel  # noqa: E402  (import after sys.path setup)


# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
TILE_SIZE = 32
MIN_TILE_SIZE = 8
MAX_TILE_SIZE = 64
ZOOM_STEP = 2
SIDE_PANEL_WIDTH = 240
FPS = 60


Color = Tuple[int, int, int]

BACKGROUND_COLOR: Color = (26, 31, 34)
ROAD_COLOR: Color = (100, 120, 80)
BUILDING_COLOR: Color = (90, 176, 90)
DEPOT_COLOR: Color = (255, 140, 0)
GRID_LINE_COLOR: Color = (37, 43, 46)
PANEL_COLOR: Color = (31, 36, 40)
PANEL_TEXT_COLOR: Color = (235, 238, 240)
PANEL_MUTED_TEXT_COLOR: Color = (170, 178, 184)
WASTE_COLOR: Color = (72, 176, 88)
BIN_EMPTY_COLOR: Color = (65, 150, 210)
BIN_HALF_COLOR: Color = (230, 176, 61)
BIN_FULL_COLOR: Color = (218, 82, 73)
HUMAN_COLOR: Color = (243, 226, 120)


class AssetManager:
    """Small helper that loads images safely and caches them.

    The visualizer asks for images by filename, such as "human.png". If the
    image is missing or cannot be loaded, this class returns None. The drawing
    code can then use a simple colored fallback shape instead of crashing.
    """

    def __init__(self, asset_dirs: Iterable[Path], tile_size: int = TILE_SIZE):
        self.asset_dirs = [Path(path) for path in asset_dirs]
        self.tile_size = tile_size
        self._cache: Dict[Tuple[str, Tuple[int, int]], Optional[pygame.Surface]] = {}

    def get_image(
        self,
        filename: str,
        size: Optional[Tuple[int, int]] = None,
    ) -> Optional[pygame.Surface]:
        """Return a scaled pygame image, or None if the file is unavailable."""

        target_size = size or (self.tile_size, self.tile_size)
        cache_key = (filename, target_size)

        if cache_key in self._cache:
            return self._cache[cache_key]

        image_path = self._find_asset(filename)
        if image_path is None:
            self._cache[cache_key] = None
            return None

        try:
            image = pygame.image.load(str(image_path)).convert_alpha()
            image = pygame.transform.smoothscale(image, target_size)
        except pygame.error:
            image = None

        self._cache[cache_key] = image
        return image

    def _find_asset(self, filename: str) -> Optional[Path]:
        """Look for an asset in each configured asset folder.

        The first check supports direct names like assets/human.png. The second
        check searches nested folders so existing layouts like
        assets/person/down.png can also be used.
        """

        for asset_dir in self.asset_dirs:
            direct_path = asset_dir / filename
            if direct_path.is_file():
                return direct_path

            matches = list(asset_dir.rglob(filename)) if asset_dir.exists() else []
            if matches:
                return matches[0]

        return None


class PygameCityVisualizer:
    """Runs CityModel and draws its visual state with Pygame."""

    def __init__(
        self,
        model: Optional[CityModel] = None,
        steps: Optional[int] = None,
        interval: int = 200,
        width: int = 20,
        height: int = 20,
        n_humans: int = 20,
        n_trucks: int = 1,
        seed: Optional[int] = None,
        tile_size: int = TILE_SIZE,
    ):
        pygame.init()

        self.model_config = {
            "width": width,
            "height": height,
            "n_humans": n_humans,
            "n_trucks": n_trucks,
            "seed": seed,
        }
        self.tile_size = tile_size
        self.side_panel_width = SIDE_PANEL_WIDTH
        self.max_steps = steps
        self.completed_steps = 0

        if model is None:
            self.model = self._create_model()
        else:
            self.model = model
            self.model_config = self._model_config_from_existing_model(model)

        self.state = self.model.get_visual_state()
        self.grid_height, self.grid_width = self._get_grid_shape(self.state)
        self.tile_size = self._fit_tile_size_to_screen(tile_size)

        self.screen = self._create_window()
        pygame.display.set_caption("Mesa City Visualizer")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 16)
        self.small_font = pygame.font.SysFont("arial", 13)

        # Prefer the existing source/visualization/assets folder. The second
        # path is a friendly fallback if this file is later moved to a root
        # visualization/ folder.
        asset_dirs = [
            VISUALIZATION_DIR / "assets",
            PROJECT_ROOT / "visualization" / "assets",
        ]
        self.assets = AssetManager(asset_dirs, tile_size=self.tile_size)

        self.running = True
        self.paused = False
        self.steps_per_second = self._interval_to_steps_per_second(interval)
        self._step_timer = 0.0

    def _create_model(self) -> CityModel:
        """Create a fresh simulation model from the saved configuration."""

        return CityModel(**self.model_config)

    def _model_config_from_existing_model(self, model: CityModel) -> dict:
        agents = list(getattr(model, "agents", []))

        n_humans = sum(1 for a in agents if a.__class__.__name__ == "LocalAgent")
        n_trucks = sum(1 for a in agents if a.__class__.__name__ == "TruckAgent")

        return {
            "width": int(getattr(model, "width", 20)),
            "height": int(getattr(model, "height", 20)),
            "n_humans": n_humans,
            "n_trucks": n_trucks,
            "seed": None,
        }

    def _interval_to_steps_per_second(self, interval: int) -> int:
        """Convert run.py's milliseconds-per-frame interval into Pygame speed."""

        if interval <= 0:
            return 4
        return max(1, min(60, int(round(1000 / interval))))

    def _fit_tile_size_to_screen(self, requested_tile_size: int) -> int:
        """Start zoomed out enough that large maps fit on screen."""

        display_info = pygame.display.Info()
        max_window_width = max(640, display_info.current_w - 120)
        max_window_height = max(480, display_info.current_h - 160)

        max_map_width = max(1, max_window_width - self.side_panel_width)
        max_tile_width = max_map_width // max(1, self.grid_width)
        max_tile_height = max_window_height // max(1, self.grid_height)
        fitted_tile_size = min(requested_tile_size, max_tile_width, max_tile_height)

        return max(MIN_TILE_SIZE, min(MAX_TILE_SIZE, int(fitted_tile_size)))

    def _create_window(self) -> pygame.Surface:
        """Create or resize the Pygame window for the current zoom level."""

        window_width = self.grid_width * self.tile_size + self.side_panel_width
        window_height = self.grid_height * self.tile_size
        return pygame.display.set_mode((window_width, window_height))

    def _get_grid_shape(self, state: dict) -> Tuple[int, int]:
        """Read grid height and width from the waste array."""

        waste = state["waste"]
        return int(waste.shape[0]), int(waste.shape[1])

    def run(self, show: bool = True, export: Optional[str] = None, outfile: str = "out.gif") -> None:
        """Main Pygame loop: handle input, advance model, and redraw."""

        if export is not None:
            print("Pygame visualizer does not export animations yet; opening the live window instead.")

        while self.running:
            dt_seconds = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update_simulation(dt_seconds)
            self._draw()

        pygame.quit()

    def _handle_events(self) -> None:
        """Handle keyboard and window events."""

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_RIGHT and self.paused:
                    self._step_once()
                elif event.key == pygame.K_UP:
                    self.steps_per_second = min(60, self.steps_per_second + 1)
                elif event.key == pygame.K_DOWN:
                    self.steps_per_second = max(1, self.steps_per_second - 1)
                elif event.key == pygame.K_r:
                    self._reset()
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    self._change_zoom(ZOOM_STEP)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    self._change_zoom(-ZOOM_STEP)

    def _update_simulation(self, dt_seconds: float) -> None:
        """Advance the model according to the current speed setting."""

        if self.paused:
            return

        self._step_timer += dt_seconds
        seconds_per_step = 1.0 / self.steps_per_second

        while self._step_timer >= seconds_per_step:
            self._step_once()
            self._step_timer -= seconds_per_step

    def _step_once(self) -> None:
        """Run one simulation step and refresh the cached visual state."""

        self.model.step()
        self.state = self.model.get_visual_state()
        self.completed_steps += 1

        if self.max_steps is not None and self.completed_steps >= self.max_steps:
            self.running = False

    def _reset(self) -> None:
        """Replace the model with a fresh instance."""

        self.model = self._create_model()
        self.state = self.model.get_visual_state()
        self.completed_steps = 0
        self._step_timer = 0.0

    def _change_zoom(self, amount: int) -> None:
        """Change visual zoom by adjusting tile size only."""

        new_tile_size = max(MIN_TILE_SIZE, min(MAX_TILE_SIZE, self.tile_size + amount))
        if new_tile_size == self.tile_size:
            return

        self.tile_size = new_tile_size
        self.assets.tile_size = new_tile_size
        self.screen = self._create_window()

    def _draw(self) -> None:
        """Draw the whole frame."""

        self.screen.fill(BACKGROUND_COLOR)
        self._draw_city_tiles()
        self._draw_depot()
        self._draw_waste()
        self._draw_bins()
        self._draw_agents()
        self._draw_info_panel()
        pygame.display.flip()

    def _draw_depot(self) -> None:
        """Draw the common dumping depot."""
        depot = self.state.get("depot")
        if depot is None:
            return

        row, col = depot
        size = int(self.tile_size * 0.9)
        x, y = self._centered_cell_rect(row, col, size)

        depot_image = self.assets.get_image("depot.png", size=(size, size))

        if depot_image is not None:
            self.screen.blit(depot_image, (x, y))
        else:
            rect = pygame.Rect(x, y, size, size)
            pygame.draw.rect(self.screen, (160, 100, 220), rect, border_radius=4)
            pygame.draw.rect(self.screen, (30, 30, 35), rect, 2, border_radius=4)
            self._draw_centered_text("D", row, col, self.small_font)
        
    def _draw_city_tiles(self) -> None:
        """Draw roads and buildings using tile images when possible."""

        street_mask = self.state["street_mask"]
        depot_cells = set(map(tuple, self.state.get("depot_cells", [])))
        road_image = self.assets.get_image("road.png")
        building_image = self.assets.get_image("building.png")

        for row in range(self.grid_height):
            for col in range(self.grid_width):
                x, y = self._cell_to_screen(row, col)
                is_street = bool(street_mask[row, col])
                is_depot = (row, col) in depot_cells

                if is_depot:
                    image = None
                    fallback_color = DEPOT_COLOR
                elif is_street:
                    image = road_image
                    fallback_color = ROAD_COLOR
                else:
                    image = building_image
                    fallback_color = BUILDING_COLOR

                if image is not None:
                    self.screen.blit(image, (x, y))
                else:
                    rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                    pygame.draw.rect(self.screen, fallback_color, rect)

                grid_rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
                # pygame.draw.rect(self.screen, GRID_LINE_COLOR, grid_rect, 1)

    def _draw_waste(self) -> None:
        """Draw waste in every cell whose waste count is above zero."""

        waste_grid = self.state["waste"]
        base_size = int(self.tile_size * 0.58)
        waste_image = self.assets.get_image("waste.png", size=(base_size, base_size))

        for row in range(self.grid_height):
            for col in range(self.grid_width):
                amount = int(waste_grid[row, col])
                if amount <= 0:
                    continue

                # Slightly enlarge bigger waste piles, while keeping them inside
                # the tile. Text is also drawn for counts above one.
                extra_size = min(10, amount * 2)
                size = min(self.tile_size - 4, base_size + extra_size)
                x, y = self._centered_cell_rect(row, col, size)

                if waste_image is not None:
                    image = pygame.transform.smoothscale(waste_image, (size, size))
                    self.screen.blit(image, (x, y))
                else:
                    pygame.draw.circle(
                        self.screen,
                        WASTE_COLOR,
                        (x + size // 2, y + size // 2),
                        size // 2,
                    )

                if amount > 1:
                    if self.tile_size >= 18:
                        self._draw_centered_text(str(amount), row, col, self.small_font)

    def _draw_bins(self) -> None:
        """Draw bins, choosing the image by load/capacity."""

        for row, col, capacity, load in self.state["bins"]:
            fill_ratio = 0.0 if capacity <= 0 else load / capacity

            if fill_ratio >= 0.95:
                filename = "bin_full.png"
                fallback_color = BIN_FULL_COLOR
            elif fill_ratio >= 0.5:
                filename = "bin_half.png"
                fallback_color = BIN_HALF_COLOR
            else:
                filename = "bin_empty.png"
                fallback_color = BIN_EMPTY_COLOR

            # This repository currently has dustbin.png; use it as a backup
            # without requiring any simulation changes.
            image = self.assets.get_image(filename) or self.assets.get_image("dustbin.png")
            x, y = self._cell_to_screen(row, col)

            # vibrating the bin at 95%
            if fill_ratio >= 0.95:
                shake = self._shake_offset()
                x += shake

            if image is not None:
                self.screen.blit(image, (x, y))
            else:
                inset = max(1, self.tile_size // 6)
                rect = pygame.Rect(
                    x + inset,
                    y + inset,
                    self.tile_size - inset * 2,
                    self.tile_size - inset * 2,
                )
                pygame.draw.rect(self.screen, fallback_color, rect)
                pygame.draw.rect(self.screen, (20, 24, 26), rect)

    def _draw_agents(self) -> None:
        """Draw humans and trucks at their grid positions."""

        human_size = int(self.tile_size * 0.78)
        truck_size = int(self.tile_size * 0.95)

        human_image = (
            self.assets.get_image("human.png", size=(human_size, human_size))
            or self.assets.get_image("down.png", size=(human_size, human_size))
        )

        truck_image = (
            self.assets.get_image("truck.png", size=(truck_size, truck_size))
            or self.assets.get_image("garbage_truck.png", size=(truck_size, truck_size))
            or self.assets.get_image("van.png", size=(truck_size, truck_size))
        )

        truck_direction_images = {
            (-1, 0): self.assets.get_image("truck_up.png", size=(truck_size, truck_size)),
            (1, 0): self.assets.get_image("truck_down.png", size=(truck_size, truck_size)),
            (0, -1): self.assets.get_image("truck_left.png", size=(truck_size, truck_size)),
            (0, 1): self.assets.get_image("truck_right.png", size=(truck_size, truck_size)),
        }

        for agent_id, agent_type, position, payload in self.state["agents"]:
            if position is None:
                continue

            row, col = position

            if agent_type == "TruckAgent":
                x, y = self._centered_cell_rect(row, col, truck_size)
                direction = payload.get("direction")
                image = truck_direction_images.get(direction, truck_image)

                if image is not None:
                    self.screen.blit(image, (x, y))
                else:
                    rect = pygame.Rect(x, y, truck_size, truck_size)
                    pygame.draw.rect(self.screen, (80, 170, 230), rect, border_radius=4)
                    pygame.draw.rect(self.screen, (20, 24, 26), rect, 2, border_radius=4)

                    if self.tile_size >= 18:
                        load = payload.get("load", 0)
                        capacity = payload.get("capacity", 1)
                        text = f"T {load}/{capacity}"
                        self._draw_centered_text("T", row, col, self.small_font)

                # Optional: draw a small load bar above truck
                capacity = max(1, int(payload.get("capacity", 1)))
                load = int(payload.get("load", 0))
                fill_ratio = max(0.0, min(1.0, load / capacity))
                self._draw_load_bar(row, col, fill_ratio)

            else:
                x, y = self._centered_cell_rect(row, col, human_size)

            if agent_type == "TouristAgent":
                human_image = self.assets.get_image("tourist/down.png", size=(human_size, human_size))
            else:
                human_image = self.assets.get_image("person/down.png", size=(human_size, human_size))

            if human_image is not None:
                self.screen.blit(human_image, (x, y))
            else:
                center = (x + human_size // 2, y + human_size // 2)
                pygame.draw.circle(self.screen, HUMAN_COLOR, center, human_size // 2)
                pygame.draw.circle(self.screen, (33, 35, 36), center, human_size // 2, 2)
    
    def _draw_load_bar(self, row: int, col: int, fill_ratio: float) -> None:
        """Draw a small load bar above a truck."""

        if self.tile_size < 16:
            return

        tile_x, tile_y = self._cell_to_screen(row, col)

        bar_width = int(self.tile_size * 0.8)
        bar_height = max(3, int(self.tile_size * 0.12))

        x = tile_x + (self.tile_size - bar_width) // 2
        y = tile_y + 2

        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        fill_rect = pygame.Rect(x, y, int(bar_width * fill_ratio), bar_height)

        pygame.draw.rect(self.screen, (35, 38, 40), bg_rect)
        pygame.draw.rect(self.screen, (120, 220, 120), fill_rect)
        pygame.draw.rect(self.screen, (10, 12, 14), bg_rect, 1)

    def _draw_info_panel(self) -> None:
        """Draw a simple side panel with current controls and metrics."""

        panel_x = self.grid_width * self.tile_size
        panel_rect = pygame.Rect(panel_x, 0, self.side_panel_width, self.screen.get_height())
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect)

        metrics = self.state.get("metrics", {})
        status = "Paused" if self.paused else "Playing"

        lines = [
            ("City Simulation", PANEL_TEXT_COLOR, self.font),
            ("", PANEL_MUTED_TEXT_COLOR, self.small_font),
            (f"Time: {metrics.get('time', self.state.get('time', 0)):.1f}", PANEL_TEXT_COLOR, self.font),
            (f"Total waste: {metrics.get('total_waste', 0)}", PANEL_TEXT_COLOR, self.font),
            (f"Dumped: {metrics.get('total_dumped', 0)}", PANEL_TEXT_COLOR, self.font),
            (f"Agents: {metrics.get('num_agents', 0)}", PANEL_TEXT_COLOR, self.font),
            (f"Speed: {self.steps_per_second} step/s", PANEL_TEXT_COLOR, self.font),
            (f"Zoom: {self.tile_size}px/cell", PANEL_TEXT_COLOR, self.font),
            (f"Status: {status}", PANEL_TEXT_COLOR, self.font),
            ("", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("SPACE pause/play", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("RIGHT step while paused", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("UP/DOWN speed", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("+/- zoom", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("R reset", PANEL_MUTED_TEXT_COLOR, self.small_font),
            ("ESC quit", PANEL_MUTED_TEXT_COLOR, self.small_font),
        ]

        y = 18
        for text, color, font in lines:
            if text:
                surface = font.render(text, True, color)
                self.screen.blit(surface, (panel_x + 16, y))
            y += 26 if font == self.font else 20

    def _cell_to_screen(self, row: int, col: int) -> Tuple[int, int]:
        """Convert simulation coordinates (row, column) to Pygame (x, y)."""

        x = int(col) * self.tile_size
        y = int(row) * self.tile_size
        return x, y

    def _centered_cell_rect(self, row: int, col: int, size: int) -> Tuple[int, int]:
        """Return the top-left point for a square centered inside one tile."""

        tile_x, tile_y = self._cell_to_screen(row, col)
        offset = (self.tile_size - size) // 2
        return tile_x + offset, tile_y + offset

    def _draw_centered_text(
        self,
        text: str,
        row: int,
        col: int,
        font: pygame.font.Font,
    ) -> None:
        """Draw small text centered in a grid cell."""

        tile_x, tile_y = self._cell_to_screen(row, col)
        surface = font.render(text, True, (255, 255, 255))
        shadow = font.render(text, True, (0, 0, 0))
        rect = surface.get_rect(center=(tile_x + self.tile_size // 2, tile_y + self.tile_size // 2))
        shadow_rect = shadow.get_rect(center=(rect.centerx + 1, rect.centery + 1))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(surface, rect)

    def _shake_offset(self) -> int:
        """Return a tiny left/right offset for full bins."""

        ticks = pygame.time.get_ticks()
        return int(math.sin(ticks * 0.04) * 2)


class Animator(PygameCityVisualizer):
    """run.py-compatible name for the Pygame visualizer.

    The existing run_ui() function creates an Animator with:

        Animator(model=model, steps=steps, interval=interval)

    Keeping this adapter means run.py can call the Pygame visualizer in the
    same style as the previous Matplotlib Animator.
    """

    pass

