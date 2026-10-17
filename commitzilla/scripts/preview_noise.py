"""Render the dragon as it will REALLY look, with background activity mixed in.

Felipe's own work lit 111 of the last 365 days, nearly all of it at level 1.
Those days land wherever they land, including on squares the dragon needs dark,
and nothing can remove them. This samples that same rate onto the rest days so
the picture can be judged honestly before committing a year to it.
"""

import os
import random
import subprocess
import sys

from render import load_grid, render_png, render_svg, ROOT

ACTIVE_RATE = 111 / 365.0


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    rnd = random.Random(seed)
    grid = load_grid(os.path.join(ROOT, "art", "dragon.grid"))

    added = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == 0 and rnd.random() < ACTIVE_RATE:
                # real days skew heavily to the lowest band
                grid[r][c] = 1 if rnd.random() < 0.85 else 2
                added += 1

    png = os.path.join(ROOT, "out", "with_noise.png")
    render_png(grid, png)
    render_svg(grid, os.path.join(ROOT, "out", "with_noise.svg"),
               "commitzilla / target + realistic background activity")
    print(f"{png}  ({added} noise squares added at the historical rate)")


if __name__ == "__main__":
    main()
