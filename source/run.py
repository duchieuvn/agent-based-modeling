import argparse
from visualization.pygame_visualizer import Animator

from model import CityModel


def run_headless(steps: int = 100, width: int = 40, height: int = 40, humans: int = 50, seed: int = None):
    model = CityModel(width=width, height=height, n_humans=humans, seed=seed)
    for t in range(steps):
        model.step()
        if t % 10 == 0:
            print(f"Step {t}: time={model.time}, total_waste={model.total_waste()}, agents={len(model.agents)}")


def run_ui(steps: int = 100, width: int = 40, height: int = 40, humans: int = 50, seed: int = None, interval: int = 200, export: str = None, outfile: str = "out.gif"):
    model = CityModel(width=width, height=height, n_humans=humans, seed=seed)
    animator = Animator(model=model, steps=steps, interval=interval)
    return animator.run(show=(export is None), export=export, outfile=outfile)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--steps', type=int, default=200)
    p.add_argument('--width', type=int, default=60)
    p.add_argument('--height', type=int, default=60)
    p.add_argument('--humans', type=int, default=30)
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--no-ui', action='store_true', help='Run the original headless console loop.')
    p.add_argument('--interval', type=int, default=200, help='Animation interval in milliseconds.')
    p.add_argument('--export', choices=['gif'], default=None, help='Export animation instead of showing a live window.')
    p.add_argument('--outfile', type=str, default='out.gif', help='Output path for exported animation.')
    args = p.parse_args()

    if args.no_ui:
        run_headless(steps=args.steps, width=args.width, height=args.height, humans=args.humans, seed=args.seed)
    else:
        run_ui(steps=args.steps, width=args.width, height=args.height, humans=args.humans, seed=args.seed, interval=args.interval, export=args.export, outfile=args.outfile)
