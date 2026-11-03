"""Write the supervisor's records -- run INSIDE GitHub Actions, never in a session.

The cloud supervisor can do almost nothing itself: its sandbox blocks GitHub
GraphQL (which `gh pr create`/`gh pr merge` use) AND github.com web pages (so
it cannot read the calendar), and anything it pushed would be attributed to
Felipe and land on his graph. So the workflow does the whole check, and this
script records it, deterministically, from verify.py's findings:

  - appends one journal line: last night's square, repairs, dark squares,
    any band shift, plus the optional free-text note
  - writes state/last_check.md, which the cloud session reads back over REST
  - refreshes actual.grid and the renders
  - commits all of it AS github-actions[bot] (not linked to Felipe, so it
    counts 0) and lands it through one branch, one PR, one --merge.

It does NOT touch level_commits: that only feeds build_schedule.py, a run-once
freeze, and re-freezing mid-year moves the ASCII reveal. A band shift is
reported for a human to decide on. Nor achievements.md: the built-in token
cannot see private repos, so its merged-PR count would come out too low.

The PR and merge must use the built-in GITHUB_TOKEN, never COMMITZILLA_TOKEN:
the workflow pins that for this step.

  record.py --check check.json [--repaired DATE:N,...] [--note "text"] [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
CFG = json.load(open(os.path.join(ROOT, "config.json")))
REL = CFG["project_dir"]
BOT = ("github-actions[bot]", "41898333+github-actions[bot]@users.noreply.github.com")
REPORT = os.path.join(ROOT, "state", "last_check.md")


def run(cmd, check=True, env=None):
    print("$", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=REPO, env=env)
    if check and r.returncode:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(cmd)}")
    return r.returncode


def today_local():
    off = CFG["tz_offset"]
    sign = 1 if off[0] == "+" else -1
    tz = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[4:6])))
    return datetime.now(tz).date()


def band_shifts(chk):
    """Levels whose lowest observed count sits above the count we paint with.

    An upper bound, not proof: the true threshold may be lower and simply not
    hit by any day yet. verify.py tops up anything that actually lands pale.
    """
    return [f"L{lv} seen only from {chk['bands'][lv]}, we paint {n}"
            for lv, n in sorted(chk["level_commits"].items())
            if lv in chk["bands"] and chk["bands"][lv] > n]


def verdict(v):
    return "ok" if v["got"] == v["want"] else ("PALE" if v["got"] < v["want"] else "dark")


def compose(chk, repaired, note):
    last = (today_local() - timedelta(days=1)).isoformat()
    sq = chk["days"].get(last)
    parts = [f"painter {last}: L{sq['got']}/L{sq['want']} ({sq['count']}) {verdict(sq)}" if sq
             else f"painter {last}: not on the graph yet"]
    parts.append("repaired " + ", ".join(repaired) if repaired else "no repairs")
    if chk["pale"]:
        parts.append(f"pale (14d): {', '.join(chk['pale'])}")
    if chk["dark"]:
        parts.append(f"dark (14d, unfixable): {', '.join(chk['dark'])}")
    shifts = band_shifts(chk)
    parts.append("bands to check: " + "; ".join(shifts) if shifts
                 else "bands " + "/".join(str(chk["bands"].get(k, "?")) for k in "1234"))
    if note:
        parts.append(" ".join(note.split()))
    return " · ".join(parts), shifts


def write_report(chk, repaired, line, shifts):
    rows = "\n".join(f"| {d} | L{v['want']} | L{v['got']} | {v['count']} | {verdict(v)} |"
                     for d, v in sorted(chk["days"].items()))
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(f"""# Last supervisor check

_Written by `scripts/record.py` in Actions at {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC.
Read-back via `{chk['source']}`; graph ends {chk['today']}._

**Summary:** {line}

- Live bands (count at which each level starts): `{chk['bands']}`
- `level_commits` in use: `{chk['level_commits']}`
- Bands to check (lowest count seen per level vs what we paint): {'; '.join(shifts) if shifts else 'none'}
- Repairs: {', '.join(repaired) if repaired else 'none'}

| Day | Want | Got | Contributions | |
|---|---|---|---|---|
{rows}
""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", required=True, help="JSON written by verify.py --json")
    ap.add_argument("--repaired", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if run([sys.executable, os.path.join(HERE, "blackout.py")], check=False):
        return 0  # the eye: write nothing at all

    chk = json.load(open(a.check))
    repaired = [r for r in a.repaired.split(",") if r]
    day = today_local().isoformat()

    run(["git", "fetch", "origin", "main"])
    branch = f"{CFG['branch_prefix']}notes-{day}"
    if not a.dry_run:
        # repairs (if any) have already merged; build on top of them
        run(["git", "checkout", "-B", branch, "origin/main"])

    line, shifts = compose(chk, repaired, a.note)
    with open(os.path.join(ROOT, "state", "journal.md"), "a", encoding="utf-8") as fh:
        fh.write(f"- **{day}** · {line}\n")
    write_report(chk, repaired, line, shifts)
    print(f"journal: {line}")

    run([sys.executable, os.path.join(HERE, "verify.py")], check=False)  # full-year actual.grid
    run([sys.executable, os.path.join(HERE, "render.py"), "--target"])
    run([sys.executable, os.path.join(HERE, "render.py"), "--actual"], check=False)

    if a.dry_run:
        run(["git", "--no-pager", "diff", "--stat"], check=False)
        return 0

    env = dict(os.environ, GIT_AUTHOR_NAME=BOT[0], GIT_AUTHOR_EMAIL=BOT[1],
               GIT_COMMITTER_NAME=BOT[0], GIT_COMMITTER_EMAIL=BOT[1])
    run(["git", "add", f"{REL}/state", f"{REL}/out"])
    run(["git", "commit", "-m", f"\U0001f996 supervisor notes {day}"], env=env)
    run(["git", "push", "-u", "origin", branch, "--force-with-lease"])
    run(["gh", "pr", "create", "--base", "main", "--head", branch,
         "--title", f"\U0001f996 commitzilla supervisor notes {day}",
         "--body", f"{line}\n\nRecorded by the bot; counts 0 toward the graph."])
    run(["gh", "pr", "merge", branch, "--merge", "--delete-branch"])
    run(["git", "checkout", "--detach", "origin/main"], check=False)
    print(f"recorded notes for {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
