"""Track (and where it is honestly possible, earn) GitHub profile achievements.

  achievements.py --status      refresh state/achievements.md from the live API
  achievements.py --quickdraw   open an issue and close it inside five minutes

Deliberately NOT automated, with the reason recorded rather than quietly skipped:
Pair Extraordinaire needs a co-author trailer naming a second real GitHub
account, and GitHub's terms allow one free personal account per person -- so it
needs an actual collaborator's consent, not a sock puppet. Starstruck and Galaxy
Brain both need other people (you cannot accept your own discussion answer).
Public Sponsor is a paid decision, not a script.
"""

import argparse
import json
import os
import subprocess
import time
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(ROOT, "config.json")))
SCHED = json.load(open(os.path.join(ROOT, "plan", "schedule.json")))
DOC = os.path.join(ROOT, "state", "achievements.md")

PULL_SHARK_TIERS = [(2, "bronze"), (16, "silver"), (128, "gold"), (1024, "platinum")]


def gh(args, check=True):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout.strip()


def merged_prs(login):
    out = gh(["api", "-X", "GET", "search/issues",
              "-f", f"q=is:pr author:{login} is:merged", "--jq", ".total_count"])
    return int(out or 0)


def quickdraw():
    """Open an issue and close it well inside the five-minute window."""
    repo = CFG["repo"]
    url = gh(["issue", "create", "-R", repo,
              "--title", "\U0001f996 commitzilla: first light",
              "--body", "Opened and closed immediately -- commitzilla is awake.\n\n"
                        "This issue exists to confirm the automation can open and close "
                        "its own issues. Closing now."])
    num = url.rstrip("/").split("/")[-1]
    print(f"opened issue #{num}, closing in 10s")
    time.sleep(10)
    gh(["issue", "close", num, "-R", repo, "-c", "Closed by commitzilla. Quickdraw."])
    print(f"closed #{num} -- Quickdraw should land within 24h")
    return num


def painted_nights_ahead():
    """Dates of the painted nights still to come -- one PR each.

    Rest days get no PR at all: a PR is itself a contribution, so opening one on
    a level-0 day would light a square that is supposed to stay dark and punch a
    hole in the dragon. That caps us at one PR per PAINTED night, not per day.
    """
    today = date.today()
    return [d for d, e in sorted(SCHED["days"].items())
            if e["commits"] and date.fromisoformat(d) > today]


def eta_for(n, target):
    ahead = painted_nights_ahead()
    need = target - n
    if need <= 0:
        return "already there"
    if need > len(ahead):
        return f"out of reach this year (needs {need}, only {len(ahead)} painted nights left)"
    return f"~{ahead[need - 1]} ({need} more painted nights)"


def status(login):
    n = merged_prs(login)
    tier = None
    nxt = None
    for count, name in PULL_SHARK_TIERS:
        if n >= count:
            tier = name
        elif nxt is None:
            nxt = (count, name)

    lines = [
        "# Achievements",
        "",
        f"_Refreshed {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by `scripts/achievements.py`._",
        "",
        "## Being pursued automatically",
        "",
        "| Achievement | How | Status |",
        "|---|---|---|",
        f"| **Pull Shark** | one merged PR every night | **{n}** merged PRs"
        + (f" — {tier} tier" if tier else " — not yet")
        + (f", next: {nxt[1]} at {nxt[0]}" if nxt else ", all tiers earned") + " |",
        "| **YOLO** | merging a PR with no review; the first night does it | earned on first merge |",
        "| **Quickdraw** | open an issue, close it inside 5 minutes | `--quickdraw`, one-off |",
        "",
        f"Next Pull Shark tier: **{eta_for(n, nxt[0]) if nxt else 'all tiers earned'}**.",
        f"Painted nights left this year: {len(painted_nights_ahead())}. Every day is painted "
        "except 2027-08-10, the dragon's eye, which gets no commit, no PR and no issue.",
        "",
        "## Recorded, not automated — and why",
        "",
        "| Achievement | Why not |",
        "|---|---|",
        "| **Pair Extraordinaire** | Needs a co-author trailer naming a second real GitHub "
        "account. GitHub allows one free personal account per person, so this needs an actual "
        "collaborator who agrees to it — not a fabricated account. |",
        "| **Starstruck** | Needs 16 stars from other people. |",
        "| **Galaxy Brain** | Needs accepted answers in Discussions; you cannot accept your own. |",
        "| **Public Sponsor** | One manual sponsorship. A spending decision, not a script. |",
        "",
        "> Note: tier thresholds come from community documentation, not an official GitHub "
        "page, and have shifted before. The profile's Achievements tab is the authority.",
        "",
    ]
    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    open(DOC, "w", encoding="utf-8").write("\n".join(lines))
    print(f"merged PRs: {n}" + (f" ({tier})" if tier else ""))
    print(f"wrote {DOC}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--quickdraw", action="store_true")
    a = ap.parse_args()
    login = CFG["repo"].split("/")[0]
    if a.quickdraw:
        quickdraw()
    status(login)


if __name__ == "__main__":
    main()
