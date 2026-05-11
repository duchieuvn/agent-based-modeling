import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter


class Animator:
    """Matplotlib animation helper for a CityModel visual snapshot stream."""

    def __init__(self, model, steps=200, interval=200):
        self.model = model
        self.steps = steps
        self.interval = interval
        self.fig = None
        self.ax = None
        self._waste_im = None
        self._bins_scatter = None
        self._agents_scatter = None
        self._title = None

    def _get_bin_color(self, load_ratio):
        """Return color based on bin load percentage."""
        if load_ratio < 0.5:
            return "green"
        elif load_ratio < 0.8:
            return "yellow"
        elif load_ratio < 1.0:
            return "purple"
        else:
            return "red"

    def _ensure_axes(self):
        if self.fig is not None and self.ax is not None:
            return

        state = self.model.get_visual_state()
        waste = np.asarray(state["waste"])
        h, w = waste.shape

        self.fig, self.ax = plt.subplots(figsize=(min(12, max(5, w / 4)), min(12, max(5, h / 4))))
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_aspect("equal")
        self.ax.set_xlim(-0.5, w - 0.5)
        self.ax.set_ylim(h - 0.5, -0.5)

        street_mask = np.asarray(state["street_mask"])
        background = np.where(street_mask, 0.9, 0.3)
        self.ax.imshow(background, cmap="gray", interpolation="nearest", zorder=0)
        self._waste_im = self.ax.imshow(waste, cmap="YlOrRd", interpolation="nearest", alpha=0.75, zorder=1)

        self._bins_scatter = self.ax.scatter([], [], s=[], c="blue", marker="s", edgecolors="black", linewidths=0.5, zorder=2)
        self._agents_scatter = self.ax.scatter([], [], s=24, c="red", marker="o", edgecolors="white", linewidths=0.4, zorder=3)
        self._title = self.ax.text(
            0.02,
            0.98,
            "",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"),
        )

    def _apply_state(self, state):
        waste = np.asarray(state["waste"])
        street_mask = np.asarray(state["street_mask"])
        self._waste_im.set_data(waste)
        self._waste_im.set_alpha(np.where(street_mask, 0.75, 0.0))

        bins = state.get("bins", [])
        if bins:
            xs = [c for (r, c, capacity, load) in bins]
            ys = [r for (r, c, capacity, load) in bins]
            sizes = [max(30, 35 + 170 * (load / max(1, capacity))) for (r, c, capacity, load) in bins]
            colors = [self._get_bin_color(load / max(1, capacity)) for (r, c, capacity, load) in bins]
            self._bins_scatter.set_offsets(np.column_stack([xs, ys]))
            self._bins_scatter.set_sizes(sizes)
            self._bins_scatter.set_color(colors)
        else:
            self._bins_scatter.set_offsets(np.empty((0, 2)))
            self._bins_scatter.set_sizes([])
            self._bins_scatter.set_color([])

        agents = state.get("agents", [])
        agent_positions = []
        for (_id, _atype, pos, _payload) in agents:
            if pos is None:
                continue
            r, c = pos
            agent_positions.append((c, r))
        if agent_positions:
            self._agents_scatter.set_offsets(np.array(agent_positions))
        else:
            self._agents_scatter.set_offsets(np.empty((0, 2)))

        metrics = state.get("metrics", {})
        self._title.set_text(
            f"t={state.get('time', 0):.0f}  waste={metrics.get('total_waste', 0)}  agents={metrics.get('num_agents', 0)}"
        )

    def _update(self, _frame):
        self.model.step()
        state = self.model.get_visual_state()
        self._apply_state(state)
        return self._waste_im, self._bins_scatter, self._agents_scatter, self._title

    def run(self, show=True, export=None, outfile="out.gif"):
        self._ensure_axes()
        anim = FuncAnimation(self.fig, self._update, frames=self.steps, interval=self.interval, blit=False, repeat=False)

        if export == "gif":
            fps = max(1, int(round(1000.0 / max(1.0, float(self.interval)))))
            try:
                anim.save(outfile, writer=PillowWriter(fps=fps))
            except Exception as exc:
                print(f"Animator export failed: {exc}")

        if show:
            plt.show()

        return anim
