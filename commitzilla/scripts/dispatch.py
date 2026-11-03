"""Hand the supervisor's work to the Actions painter. For cloud sessions.

A Claude Code cloud session can call GitHub's REST API but not GraphQL, and
anything it committed or merged itself would count on Felipe's graph. So it
never writes to the repo. It triggers the workflow with workflow_dispatch
(REST), and the workflow makes the repairs with paint.py and records the
notes with record.py, as github-actions[bot], exactly as on a painted night.

  dispatch.py --journal "..." [--repairs 2026-11-01:3,2026-11-02:2]
              [--dry-run]

Exit 0 only if the dispatched run finished successfully.

Why it waits for the workflow to be idle first: the workflow has a
concurrency group, and GitHub keeps at most ONE pending run per group --
a second one queued behind a running job cancels the first pending one. If
that pending one were the nightly paint, tonight's square would be lost.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(ROOT, "config.json")))
REPO = CFG["repo"]
WF = "commitzilla.yml"
BUSY = ("queued", "in_progress", "waiting", "pending", "requested")


def gh(*args):
    r = subprocess.run(["gh", "api", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"gh api {' '.join(args)} failed:\n{r.stderr.strip()}")
    return json.loads(r.stdout) if r.stdout.strip() else None


def runs(**q):
    qs = "&".join(f"{k}={v}" for k, v in {"per_page": 20, **q}.items())
    return gh("-X", "GET", f"repos/{REPO}/actions/workflows/{WF}/runs?{qs}")["workflow_runs"]


def wait_idle(limit_s):
    end = time.time() + limit_s
    while True:
        busy = [r for r in runs() if r["status"] in BUSY]
        if not busy:
            return
        if time.time() > end:
            raise SystemExit(f"workflow still busy after {limit_s}s ({busy[0]['html_url']}); "
                             "not dispatching, so the nightly paint cannot be cancelled. Try later.")
        print(f"workflow busy ({busy[0]['event']}, {busy[0]['status']}); waiting...", flush=True)
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--repairs", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="dispatch with dry_run=true: the workflow prints and touches nothing")
    ap.add_argument("--idle-timeout", type=int, default=1200)
    ap.add_argument("--run-timeout", type=int, default=1500)
    a = ap.parse_args()

    if subprocess.run([sys.executable, os.path.join(HERE, "blackout.py")]).returncode:
        return 0  # the eye: no dispatch, nothing

    for item in filter(None, a.repairs.split(",")):
        d, _, n = item.partition(":")
        datetime.strptime(d, "%Y-%m-%d")
        if not n.isdigit() or not 1 <= int(n) <= 40:
            raise SystemExit(f"bad repair {item!r}: want DATE:N with 1 <= N <= 40")

    wait_idle(a.idle_timeout)
    started = datetime.now(timezone.utc) - timedelta(seconds=5)
    gh("-X", "POST", f"repos/{REPO}/actions/workflows/{WF}/dispatches",
       "-f", "ref=main",
       "-f", f"inputs[journal]={a.journal}",
       "-f", f"inputs[repairs]={a.repairs}",
       "-F", f"inputs[dry_run]={'true' if a.dry_run else 'false'}")
    print(f"dispatched {WF}: repairs=[{a.repairs}]", flush=True)

    run = None
    end = time.time() + a.run_timeout
    while time.time() < end:
        time.sleep(15)
        mine = [r for r in runs(event="workflow_dispatch")
                if datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= started]
        if mine:
            run = mine[-1] if run is None else next((r for r in mine if r["id"] == run["id"]), run)
            if run["status"] == "completed":
                print(f"run {run['html_url']} finished: {run['conclusion']}")
                return 0 if run["conclusion"] == "success" else 1
    raise SystemExit(f"run did not finish within {a.run_timeout}s: "
                     f"{run['html_url'] if run else 'never appeared'}")


if __name__ == "__main__":
    raise SystemExit(main())
