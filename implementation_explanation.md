# Implementation Explanation

## Overview

This project implements a Mesa-based agent simulation for the waste-in-the-city problem described in [description.md](description.md). The code models a city as a grid world, places agents and infrastructure on that grid, simulates movement and waste generation, and provides a Matplotlib-based real-time visualization.

## How the code follows `description.md`

### City model as a grid world

`description.md` says the city should be a grid world with streets, walls/buildings, public areas, and fixed waste infrastructure.

In the current code, this is represented by `CityMap` in [source/city.py](source/city.py).

- `street` is a boolean grid that marks passable cells.
- `waste` is a 2D array that stores waste amounts on each cell.
- `bins` stores fixed waste infrastructure with capacity and current load.
- `get_neighbors()` returns only passable neighboring cells, so agents move through streets and avoid blocked cells.

This matches the grid-world structure required in the project description.

### Local humans

`description.md` requires local humans who move regularly, generate small amounts of waste, and may use nearby bins.

The current implementation has `HumanAgent` in [source/agents.py](source/agents.py).

- Each human is placed on a random street cell.
- On each step, the agent moves to a random neighboring street cell.
- With a probability `p_litter`, the agent adds waste to the current cell.

This is a simplified version of the local-human behavior from the description. The current code does not yet model daily routines or bin usage, but it already captures movement plus waste generation.

### Fixed waste infrastructure

`description.md` requires bins and containers with limited capacity that may overflow.

This is implemented partially in [source/city.py](source/city.py) and [source/bins.py](source/bins.py).

- `CityMap.add_bin()` registers bins on the grid.
- Each bin has a capacity and current load.
- `deposit_to_bin()` accepts waste up to the remaining capacity and sends overflow back to the ground waste grid.

So the infrastructure and overflow logic are already aligned with the description, even though transporters are not implemented yet.

### Simulation model and scheduler

`description.md` says the implementation must be in Mesa or AgentPy and should support graph search where useful.

The current implementation uses Mesa in [source/model.py](source/model.py).

- `CityModel` creates the city map and human agents.
- Mesa 3.5.1-style activation is handled by `self.agents.shuffle_do("step")`.
- This gives random activation order, which fits the agent-based simulation style required by the project.

The model also exposes `get_visual_state()` so the UI can read a stable snapshot without changing the simulation state.

### Real-time visualization

The project description focuses on emergent city-level waste distribution, so the visualization helps inspect that behavior over time.

The Matplotlib UI is implemented in [source/visualization/plotter.py](source/visualization/plotter.py) and launched from [source/run.py](source/run.py).

- The grid background shows streets and blocked cells.
- Waste is rendered as a heatmap.
- Bins are shown as blue squares sized by fill level.
- Agents are shown as red points.
- The UI advances the model frame by frame using `FuncAnimation`.

This supports the project goal of observing how waste accumulates spatially and temporally.

## Code flow

### 1. Start the program

Running [source/run.py](source/run.py) creates a `CityModel` instance with the chosen grid size, number of humans, and random seed.

### 2. Build the city

`CityModel` creates a `CityMap`, adds bins to random passable cells, and creates human agents.

### 3. Advance the simulation

Each model step activates all agents in random order.

- Humans move to a neighboring street cell.
- Some humans generate waste at their location.
- Waste accumulates on the grid, and bins keep their own load values.

### 4. Collect a visual snapshot

`get_visual_state()` packages the current model state into arrays and lists that the visualization layer can use.

### 5. Render the UI

The Matplotlib animator reads each snapshot, draws the waste heatmap, bins, and agents, and refreshes the display in real time.

## What is already complete

- Grid-based city representation
- Human agents with movement and waste generation
- Bin infrastructure with capacity and overflow handling
- Mesa model and random activation
- Real-time Matplotlib visualization
- `get_visual_state()` for UI snapshots

## What is still missing from `description.md`

The description also asks for additional entities and features that are not implemented yet:

- Tourists
- Cleaning Service
- Dust Transporters
- More advanced graph search routing
- Scenario experiments and statistics
- An original extension beyond the base model

So the current code is a working foundation that matches the project structure, but it is still a partial implementation of the full description.

## Files to inspect

- [source/model.py](source/model.py)
- [source/city.py](source/city.py)
- [source/agents.py](source/agents.py)
- [source/bins.py](source/bins.py)
- [source/run.py](source/run.py)
- [source/visualization/plotter.py](source/visualization/plotter.py)
- [description.md](description.md)
