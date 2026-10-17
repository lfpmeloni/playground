"""Upscale art/dragon.grid into the big ASCII canvas that DRAGON.md reveals.

Same dragon, bigger: the markdown file wipes in left-to-right in lockstep with
the squares being painted on the graph. Run once.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

GLYPH = {0: "·", 1: "░", 2: "▒", 3: "▓", 4: "█"}


def main():
    cfg = json.load(open(os.path.join(ROOT, "config.json")))
    ws, hs = cfg["ascii"]["w_scale"], cfg["ascii"]["h_scale"]

    grid = []
    with open(os.path.join(ROOT, "art", "dragon.grid")) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                grid.append([int(ch) for ch in line])

    out = []
    for r in range(len(grid) * hs):
        out.append("".join(GLYPH[grid[r // hs][c // ws]] for c in range(len(grid[0]) * ws)))

    path = os.path.join(ROOT, "art", "dragon_ascii.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {path}  ({len(out[0])}x{len(out)} = {len(out[0]) * len(out)} cells)")
    for line in out:
        print(line)


if __name__ == "__main__":
    main()
