"""Render the dragon as it will REALLY look, with background activity mixed in.

Felipe's own work lit 111 of the last 365 days. Now that the background is
level 1 rather than empty, that activity can only nudge a background square up
to level 2 instead of punching a black hole in the picture -- far less damaging,
but worth seeing before committing a year to it.

The eye is left alone here. In reality a single contribution on 2027-08-10 would
destroy it, which is what blackout.py exists to prevent.
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
            if grid[r][c] == 1 and rnd.random() < ACTIVE_RATE:
                # a day of real work on top of the level-1 baseline
                grid[r][c] = 2
                added += 1

    png = os.path.join(ROOT, "out", "with_noise.png")
    render_png(grid, png)
    render_svg(grid, os.path.join(ROOT, "out", "with_noise.svg"),
               "commitzilla / target + realistic background activity")
    print(f"{png}  ({added} noise squares added at the historical rate)")


if __name__ == "__main__":
    main()
