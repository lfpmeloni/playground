"""Uncover the next sliver of the ASCII dragon into DRAGON.md.

Called once per commit, so every commit in the nightly batch carries a real
diff instead of being pure filler. Cells are revealed in column-major order --
the same left-to-right wipe the contribution graph is getting.

The reveal count lives in an HTML comment inside DRAGON.md, so the file is its
own state and nothing can drift out of sync with it.
"""

import argparse
import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "art", "dragon_ascii.txt")
DOC = os.path.join(ROOT, "DRAGON.md")

MARKER = re.compile(r"<!-- commitzilla-reveal: (\d+)/(\d+) -->")
BAR_W = 52


def load_art():
    with open(ART, encoding="utf-8") as fh:
        lines = [ln.rstrip("\n") for ln in fh if ln.strip("\n")]
    return lines, len(lines[0]), len(lines)


def current_reveal():
    if not os.path.exists(DOC):
        return 0
    m = MARKER.search(open(DOC, encoding="utf-8").read())
    return int(m.group(1)) if m else 0


def render(lines, w, h, revealed):
    """Column-major wipe: cell i is column i//h, row i%h."""
    full_cols, part_rows = divmod(revealed, h)
    out = []
    for r in range(h):
        row = list(lines[r][:full_cols])
        if full_cols < w:
            row.append(lines[r][full_cols] if r < part_rows else " ")
            row.extend(" " * (w - full_cols - 1))
        out.append("".join(row).rstrip())
    return out


def write_doc(revealed, total, lines, w, h, day_note=""):
    art = render(lines, w, h, revealed)
    pct = revealed / total
    filled = int(round(BAR_W * pct))
    bar = "█" * filled + "·" * (BAR_W - filled)
    body = [
        "# DRAGON.md",
        "",
        "> A dragon is being uncovered here one commit at a time, in step with the one",
        "> being painted onto the contribution graph. Both finish on 2027-10-16.",
        "",
        f"<!-- commitzilla-reveal: {revealed}/{total} -->",
        "",
        "```",
        f"{bar}  {pct * 100:5.1f}%",
        "```",
        "",
        "```",
        *art,
        "```",
        "",
    ]
    if day_note:
        body += [day_note, ""]
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))
    return revealed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commits-done", type=int, help="cumulative commits made so far")
    ap.add_argument("--projected", type=int, help="projected commits for the whole year")
    ap.add_argument("--set", type=int, help="reveal exactly this many cells")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    lines, w, h = load_art()
    total = w * h
    cur = current_reveal()

    if a.set is not None:
        nxt = a.set
    elif a.commits_done and a.projected:
        # Proportional, so the wipe lands exactly on the final commit of the year
        # rather than a fixed step that would stop short or overrun.
        nxt = max(cur + 1, math.ceil(total * a.commits_done / a.projected))
    else:
        nxt = cur + 1

    nxt = max(0, min(total, nxt))
    write_doc(nxt, total, lines, w, h, a.note)
    print(f"{cur} -> {nxt} / {total}")


if __name__ == "__main__":
    main()
