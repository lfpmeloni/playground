"""Write the supervisor's records -- run INSIDE GitHub Actions, never in a session.

The cloud supervisor cannot commit for itself: GraphQL (which `gh pr create`
and `gh pr merge` use) is blocked in Claude Code sessions, and anything it did
push through the session's GitHub proxy would be attributed to Felipe and land
on his graph -- the `overhead` trap. So it hands its notes to the workflow
(see dispatch.py), and this script records them:

  - appends one journal line
  - refreshes actual.grid, the renders and achievements.md
  - commits all of it AS github-actions[bot] (not linked to Felipe, so it
    counts 0) and lands it through one branch, one PR, one --merge.

The PR and merge must use the built-in GITHUB_TOKEN, never COMMITZILLA_TOKEN:
the workflow pins that for this step.

  record.py --journal "text" [--dry-run]

It deliberately does NOT touch level_commits: that only feeds build_schedule.py,
a run-once freeze, and re-freezing mid-year moves the ASCII reveal. A band
shift is reported in the journal for a human to decide on.
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
    return datetime.now(tz).date().isoformat()



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if run([sys.executable, os.path.join(HERE, "blackout.py")], check=False):
        return 0  # the eye: write nothing at all

    day = today_local()
    run(["git", "fetch", "origin", "main"])
    branch = f"{CFG['branch_prefix']}notes-{day}"
    if not a.dry_run:
        run(["git", "checkout", "-B", branch, "origin/main"])

    note = " ".join(a.journal.split())
    with open(os.path.join(ROOT, "state", "journal.md"), "a", encoding="utf-8") as fh:
        fh.write(f"- **{day}** · {note}\n")

    # Refresh the observed picture and the records. A failed read-back here
    # only costs a stale render; the journal line still lands.
    run([sys.executable, os.path.join(HERE, "verify.py")], check=False)
    run([sys.executable, os.path.join(HERE, "render.py"), "--target"])
    run([sys.executable, os.path.join(HERE, "render.py"), "--actual"], check=False)
    run([sys.executable, os.path.join(HERE, "achievements.py"), "--status"], check=False)

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
         "--body", f"Journal: {note}\n\nRecorded by the bot; counts 0 toward the graph."])
    run(["gh", "pr", "merge", branch, "--merge", "--delete-branch"])
    run(["git", "checkout", "--detach", "origin/main"], check=False)
    print(f"recorded notes for {day}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
