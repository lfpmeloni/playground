"""Freeze art/dragon.grid into plan/schedule.json: one entry per calendar day.

Run once. The nightly job only ever reads the result.
"""

import json
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load_grid(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                rows.append([int(ch) for ch in line])
    return rows


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    grid = load_grid(os.path.join(ROOT, "art", "dragon.grid"))
    rows, cols = len(grid), len(grid[0])

    origin = date.fromisoformat(cfg["origin_date"])
    if origin.weekday() != 6:  # Python: Monday=0, Sunday=6
        raise SystemExit(f"origin {origin} is not a Sunday; the grid rows would not line up")

    lv = {int(k): v for k, v in cfg["level_commits"].items()}
    overhead = cfg.get("overhead", 0)
    # Two totals, and they are NOT the same number: the band total is how many
    # contributions a square needs, while the commit total is what we actually
    # hand-make after the free PR + merge-commit contributions are deducted.
    # The ASCII reveal must track the latter or the wipe stops short of the edge.
    days, total_contrib, total_commits = {}, 0, 0
    for d in range(rows * cols):
        col, row = d // rows, d % rows
        level = grid[row][col]
        commits = lv.get(level, 0)
        made = max(1, commits - overhead) if commits else 0
        total_contrib += commits
        total_commits += made
        days[(origin + timedelta(days=d)).isoformat()] = {
            "day": d, "col": col, "row": row, "level": level,
            "commits": commits, "made": made,
        }

    total_cells = (cols * cfg["ascii"]["w_scale"]) * (rows * cfg["ascii"]["h_scale"])
    out = {
        "origin": cfg["origin_date"],
        "end": (origin + timedelta(days=rows * cols - 1)).isoformat(),
        "rows": rows, "cols": cols,
        "projected_contributions": total_contrib,
        "projected_commits": total_commits,
        "ascii_cells": total_cells,
        "reveal_step": max(1, round(total_cells / max(1, total_commits))),
        "days": days,
    }
    path = os.path.join(ROOT, "plan", "schedule.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Every commit must have a sliver of ASCII left to reveal, or it would have
    # nothing to commit and the night would fail at 3am in CI. Fail loudly here
    # instead, at build time, where someone is watching.
    if total_cells <= total_commits:
        raise SystemExit(
            f"ascii canvas is too small: {total_cells} cells for {total_commits} commits. "
            f"Raise ascii.w_scale / ascii.h_scale in config.json."
        )
    json.dump(out, open(path, "w"), indent=1)

    painted = sum(1 for v in days.values() if v["commits"])
    print(f"wrote {path}")
    print(f"  {out['origin']} -> {out['end']}  ({rows * cols} days, {painted} painted)")
    print(f"  projected contributions: {total_contrib}")
    print(f"  projected commits:       {total_commits}  (~{total_commits / painted:.1f} per painted day)")
    print(f"  ascii canvas: {cols * cfg['ascii']['w_scale']}x{rows * cfg['ascii']['h_scale']}"
          f" = {total_cells} cells, {out['reveal_step']} per commit")


if __name__ == "__main__":
    main()
