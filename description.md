# Project: ABM-Modeling
**Topic: Waste in the City** [cite: 170]

The goal is to study how different types of agents and infrastructure influence the spatial and temporal distribution of waste in the city. [cite: 170]

## City Model (Grid World)
The city is modeled as a grid world consisting of: [cite: 171]
* **Streets / paths**: Areas where agents can move. [cite: 171]
* **Walls / buildings**: Objects that block movement. [cite: 171]
* **Public areas**: Locations where waste may accumulate. [cite: 171]
* **Fixed waste infrastructure**: Items such as bins and containers. [cite: 171]

## Agent Types
The model must include at least the following entities: [cite: 173]

1. **Local Humans** [cite: 173]
    * Move according to regular daily patterns. [cite: 173]
    * Generate small amounts of waste with a given probability. [cite: 173]
    * May use nearby bins if available. [cite: 173]
2. **Tourists** [cite: 173]
    * Move less predictably. [cite: 173]
    * Prefer central or attractive areas. [cite: 173]
    * May generate more waste in crowded areas. [cite: 173]
3. **Cleaning Service** [cite: 173]
    * Move through streets to detect and collect waste from public spaces. [cite: 173]
    * Bring waste to disposal areas for processing/termination. [cite: 173]
    * Follow simple rule-based strategies (e.g., nearest waste, random patrol, or fixed route). [cite: 173, 174]
4. **Dust Bins and Dust Containers** [cite: 175]
    * Fixed infrastructure with limited capacity. [cite: 175]
    * Receive waste from humans and robots. [cite: 175]
    * May overflow if not emptied. [cite: 175]
5. **Dust Transporters** [cite: 175]
    * Collect waste from full bins or containers. [cite: 175]
    * Transport waste to a disposal point outside or at the edge of the city. [cite: 175]
    * Follow street paths and cannot pass through buildings. [cite: 175]

## Main Research Questions
How do city structure, movement patterns, bin placement, cleaning strategies, and transporter frequency affect waste accumulation in a city? [cite: 177] The focus is on the **emergent city-level waste distribution** caused by many interacting agents over time, rather than a single agent's decision process. [cite: 178]

## Experiments and Implementation
* **Implementation**: Simulation must be implemented in **Mesa** or **AgentPy**. [cite: 180]
* **Graph Search**: Use graph search algorithms where they make sense. [cite: 180]
* **Scenarios**: Run multiple scenarios to measure statistics (e.g., total waste on streets, overflowing bins, average waste per region, robot efficiency, and transporter workload). [cite: 180]
* **Creative Extension**: Each group must design and implement an original extension that meaningfully enhances the model. [cite: 182]

## Project Timeline and Requirements
* **Implementation Period**: 11.05.2026 – 01.06.2026 (No lectures). [cite: 184]
* **Teams**: Work in teams of 2 people. [cite: 184]
* **Submission**: Code, documentation, and presentation are due on Moodle by 01.06.2026. [cite: 184]
* **Presentation**: 10 minutes for the presentation plus 5–10 minutes for questions per person. [cite: 184]
* **Defense**: Project presentations and defense will occur on 08.06.2026 (and 15.06.2026 if needed). [cite: 184]