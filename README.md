# agent-based-modeling

The goal is to study how different types of agents and infrastructure influence the spatial and temporal distribution of waste in the city.

# Mesa-based city grid scaffold

Files:

- `city.py`: CityMap (grid + graph conversion)
- `agents.py`: example HumanAgent
- `bins.py`: Bin dataclass
- `model.py`: CityModel wiring city and agents using Mesa
- `run.py`: simple runner

# Quick start:

```bash
python -m pip install -r requirements.txt
python run.py
```

# UI Recommendation

Short answer: start with Matplotlib for quick iteration, and use Dash + dash-cytoscape (or PyVis for a lighter web graph) for an interactive, NetworkX-friendly UI.

- Matplotlib

  Pros: very quick to implement, supports NetworkX drawing and heatmaps, low deps.

  Use when: prototyping animation or exporting MP4/GIF.

- Dash + dash-cytoscape (recommended for full interactive UI)

  Pros: first-class browser UI, easy controls (start/stop/steps), live charts (Plotly), dash-cytoscape accepts NetworkX→Cytoscape JSON easily, good for dashboards and panels.

  Use when: you want interactive exploration, controls, and charts in one app.

- PyVis (lightweight alternative)  
  Pros: simple NetworkX → interactive HTML (vis.js) with physics/layouts, minimal code.

  Use when: you want an embeddable interactive graph view without building a full dashboard.

- Holoviews + Datashader / Bokeh

  Pros: best for very large graphs/heatmaps (fast rendering, zoom), integrates with NetworkX via conversion.

  Use when: scale/performance for large maps matters.
