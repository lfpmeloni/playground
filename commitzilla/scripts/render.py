"""Render a grid to PNG (dependency-free) and SVG.

--target  the dragon we are aiming at
--actual  what GitHub really shows, as recorded by verify.py
"""

import argparse
import json
import os

from pngwrite import Canvas

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# GitHub's dark-mode contribution palette.
PALETTE = [
    (0x16, 0x1B, 0x22),   # 0 empty
    (0x0E, 0x44, 0x29),   # 1
    (0x00, 0x6D, 0x32),   # 2
    (0x26, 0xA6, 0x41),   # 3
    (0x39, 0xD3, 0x53),   # 4
]
BG = (0x0D, 0x11, 0x17)
HEX = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

CELL, GAP, MARGIN = 22, 5, 26


def load_grid(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append([int(ch) for ch in line])
    return rows


def render_png(grid, path, scale=1):
    h = len(grid)
    w = len(grid[0])
    cell, gap, margin = CELL * scale, GAP * scale, MARGIN * scale
    width = margin * 2 + w * (cell + gap) - gap
    height = margin * 2 + h * (cell + gap) - gap
    cv = Canvas(width, height, BG)
    for r in range(h):
        for c in range(w):
            cv.rrect(
                margin + c * (cell + gap),
                margin + r * (cell + gap),
                cell, cell,
                PALETTE[grid[r][c]],
                r=max(2, cell // 5),
            )
    cv.save(path)
    return path, width, height


def render_svg(grid, path, title=""):
    h, w = len(grid), len(grid[0])
    width = MARGIN * 2 + w * (CELL + GAP) - GAP
    height = MARGIN * 2 + h * (CELL + GAP) - GAP + (24 if title else 0)
    top = MARGIN + (24 if title else 0)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{title or "commitzilla"}">',
        f'<rect width="{width}" height="{height}" fill="#0d1117"/>',
    ]
    if title:
        out.append(
            f'<text x="{MARGIN}" y="26" fill="#7d8590" '
            f'font-family="ui-monospace,SFMono-Regular,Menlo,monospace" font-size="13">{title}</text>'
        )
    for r in range(h):
        for c in range(w):
            out.append(
                f'<rect x="{MARGIN + c * (CELL + GAP)}" y="{top + r * (CELL + GAP)}" '
                f'width="{CELL}" height="{CELL}" rx="4" fill="{HEX[grid[r][c]]}"/>'
            )
    out.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(out))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", action="store_true")
    ap.add_argument("--actual", action="store_true")
    ap.add_argument("--grid", default=os.path.join(ROOT, "art", "dragon.grid"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--title", default=None)
    a = ap.parse_args()

    if a.actual:
        src = os.path.join(ROOT, "state", "actual.grid")
        if not os.path.exists(src):
            raise SystemExit("no state/actual.grid yet -- run verify.py first")
        grid = load_grid(src)
        name, title = "actual", a.title or "commitzilla / observed on github"
    else:
        grid = load_grid(a.grid)
        name, title = "target", a.title or "commitzilla / target"

    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    png = a.out or os.path.join(ROOT, "out", f"{name}.png")
    svg = os.path.join(ROOT, "out", f"{name}.svg")
    p, w, h = render_png(grid, png, a.scale)
    render_svg(grid, svg, title)
    print(f"{p}  ({w}x{h})")
    print(render_svg(grid, svg, title))


if __name__ == "__main__":
    main()
