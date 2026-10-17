"""Draft the dragon into a 7x52 grid of levels 0-4.

FIRST DRAFT GENERATOR ONLY. Once the shape is right, art/dragon.grid is the
authority and can be hand-tuned one character at a time; nothing in the nightly
path ever calls this script again.

Rows are Sunday(0)..Saturday(6), columns are weeks -- exactly like the graph.
A procedural sine was tried first and lost: at seven pixels tall it reads as a
chunky zigzag, so the spine is picked by hand, column by column.
"""

import argparse
import os

ROWS, COLS = 7, 52

# Row of the dragon's back, per column, cols 0..38. Two lazy undulations;
# values stay in 1..4 so a three-cell-thick body never clips the grid.
SPINE = [
    4, 4, 3, 3, 2, 2, 1, 1, 1, 1,
    2, 2, 3, 3, 4, 4, 4, 4, 3, 3,
    2, 2, 1, 1, 1, 2, 2, 3, 3, 4,
    4, 4, 3, 3, 2, 2, 1, 1,
]

# Body depth per column: a whip-thin tail that swells through the midsection
# and narrows again into the neck.
def thickness(c):
    if c <= 2:
        return 1
    if c <= 6:
        return 2
    if c <= 33:
        return 3
    return 2


# Shading by depth, top (back) to bottom (belly): bright ridge, mid body, dark belly.
#
# Nothing in the dragon uses level 1, on purpose. Felipe's own real work lights
# roughly a third of all days, almost always at 1-5 contributions, which is
# exactly level 1. Any part of the dragon drawn at level 1 would be
# indistinguishable from that background noise. Keeping the art at levels 2-4
# means the noise stays visibly dimmer than every part of the picture.
# The BODY is a solid level-3 mass with a level-4 ridge, rather than shading
# down to level 2 at the belly: against level-1 background noise a dim belly
# blurs the silhouette, and a crisp outline matters more here than a tubular
# gradient. Level 2 survives only on extremities, where ambiguity costs little.
SHADE = {1: [2], 2: [3, 3], 3: [4, 3, 3]}

HEAD_COL = 38
# Facing right. The open jaw is what makes this read as a head rather than a
# blob -- a level-0 gap between upper snout and lower jaw is the strongest
# silhouette cue available at seven pixels tall. The eye is a hole too.
HEAD = [
    "..4..4....",
    ".44444444.",
    "4444044444",
    "444444....",
    ".44444444.",
    "...2..2...",
]

# The flaming pearl, forever one week out of reach.
# Sits level with the open mouth, forever one week out of reach.
PEARL = [".2.", "242", ".2."]

CLAW_COLS = (9, 19, 27)


def put(g, r, c, v):
    if 0 <= r < ROWS and 0 <= c < COLS:
        g[r][c] = v


def blit(g, sprite, top, left):
    for dr, line in enumerate(sprite):
        for dc, ch in enumerate(line):
            if ch != ".":
                put(g, top + dr, left + dc, int(ch))


def build():
    g = [[0] * COLS for _ in range(ROWS)]

    for c, top in enumerate(SPINE):
        depth = thickness(c)
        for i, level in enumerate(SHADE[depth]):
            put(g, top + i, c, level)
        if c in CLAW_COLS:
            put(g, top + depth, c, 2)

    put(g, SPINE[0], 0, 2)            # tail tip fades out
    blit(g, HEAD, 0, HEAD_COL)        # skull fills rows 0..5
    blit(g, PEARL, 2, COLS - 3)   # row 3: dead ahead of the open jaw
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "art", "dragon.grid"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing hand-tuned grid")
    a = ap.parse_args()

    path = os.path.abspath(a.out)
    if os.path.exists(path) and not a.force:
        raise SystemExit(f"refusing to clobber hand-tuned grid at {path} (use --force)")

    g = build()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write("# commitzilla target image: 7 rows (Sun..Sat) x 52 cols (weeks), levels 0-4\n")
        for row in g:
            fh.write("".join(str(v) for v in row) + "\n")

    hist = {}
    for row in g:
        for v in row:
            hist[v] = hist.get(v, 0) + 1
    print(f"wrote {path}")
    print("lit cells:", COLS * ROWS - hist.get(0, 0), "/", COLS * ROWS, " histogram:", hist)
    for row in g:
        print("".join(" .:*#"[v] for v in row))


if __name__ == "__main__":
    main()
