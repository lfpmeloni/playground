"""The cloud supervisor's one command: have Actions check the graph, then read the result.

A Claude Code cloud session reaches GitHub only through the REST API: GraphQL
is blocked, github.com pages (the contribution calendar) return 403, and
anything it committed itself would count on Felipe's graph. So it does no
checking and no writing of its own. It triggers the workflow in supervise mode
(REST workflow_dispatch); Actions reads the calendar, repairs pale squares with
paint.py and records the night with record.py, all as github-actions[bot]. Then
this reads state/last_check.md back through the REST contents API and prints it.

  dispatch.py [--note "free text for the journal"] [--dry-run]

Exit 0 only if the run succeeded. On failure it prints the run URL and the
failing step, read from the REST jobs API.

Why it waits for the workflow to be idle first: the workflow has a
concurrency group, and GitHub keeps at most ONE pending run per group. A
second one queued behind a running job cancels the first pending one, and if
that were the nightly paint, tonight's square would be lost.
"""

import argparse
import base64
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


def failed_steps(run_id):
    jobs = gh("-X", "GET", f"repos/{REPO}/actions/runs/{run_id}/jobs")["jobs"]
    return [f"{j['name']} / {s['name']}: {s['conclusion']}"
            for j in jobs for s in j.get("steps", []) if s["conclusion"] == "failure"]


def report():
    f = gh("-X", "GET", f"repos/{REPO}/contents/{CFG['project_dir']}/state/last_check.md?ref=main")
    return base64.b64decode(f["content"]).decode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--note", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="dispatch with dry_run=true: the workflow checks and prints, writes nothing")
    ap.add_argument("--idle-timeout", type=int, default=1200)
    ap.add_argument("--run-timeout", type=int, default=1500)
    a = ap.parse_args()

    if subprocess.run([sys.executable, os.path.join(HERE, "blackout.py")]).returncode:
        return 0  # the eye: no dispatch, nothing

    wait_idle(a.idle_timeout)
    started = datetime.now(timezone.utc) - timedelta(seconds=5)
    gh("-X", "POST", f"repos/{REPO}/actions/workflows/{WF}/dispatches",
       "-f", "ref=main",
       "-F", "inputs[supervise]=true",
       "-f", f"inputs[note]={' '.join(a.note.split())}",
       "-F", f"inputs[dry_run]={'true' if a.dry_run else 'false'}")
    print("dispatched supervise run" + (" (dry run)" if a.dry_run else ""), flush=True)

    run_id, end = None, time.time() + a.run_timeout
    while time.time() < end:
        time.sleep(15)
        mine = [r for r in runs(event="workflow_dispatch")
                if datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) >= started]
        if not mine:
            continue
        run = next((r for r in mine if r["id"] == run_id), mine[-1])
        run_id = run["id"]
        if run["status"] != "completed":
            continue
        print(f"run {run['html_url']} finished: {run['conclusion']}")
        if run["conclusion"] != "success":
            for s in failed_steps(run_id):
                print(f"  failed: {s}")
            return 1
        if a.dry_run:
            print("dry run: nothing recorded; see the run log for the check output")
        else:
            print("\n" + report())
        return 0
    raise SystemExit(f"run did not finish within {a.run_timeout}s"
                     + (f": https://github.com/{REPO}/actions/runs/{run_id}" if run_id else
                        " (never appeared)"))


if __name__ == "__main__":
    raise SystemExit(main())
