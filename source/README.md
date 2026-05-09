Mesa-based city grid scaffold

Files:

- `city.py`: CityMap (grid + graph conversion)
- `agents.py`: example HumanAgent
- `bins.py`: Bin dataclass
- `model.py`: CityModel wiring city and agents using Mesa
- `run.py`: simple runner

Quick start:

```bash
python -m pip install -r requirements.txt
python -m agent_based_modeling.run --steps 200 --width 40 --height 40 --humans 50
```
