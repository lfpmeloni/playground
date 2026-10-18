"""Paint one day's square on the contribution graph.

One branch, N commits, one PR, one merge, branch deleted -- so the repo never
holds more than a single branch. Never squash-merges: squashing would collapse
the night's commits into one and destroy the pixel.

  paint.py                      paint today
  paint.py --date 2027-03-14    paint a specific day (backdated; this is how
                                verify.py repairs a square that came out pale)
  paint.py --extra 5            add N commits to a day on top of the schedule
  paint.py --dry-run            print what would happen, touch nothing
  paint.py --simulate-year      replay all 364 days as a dry run
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)

CFG = json.load(open(os.path.join(ROOT, "config.json")))
SCHED = json.load(open(os.path.join(ROOT, "plan", "schedule.json")))
PROGRESS = os.path.join(ROOT, "state", "progress.json")
REL = CFG["project_dir"]


def run(cmd, check=True, capture=False, env=None, cwd=REPO):
    if capture:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
        if check and r.returncode:
            raise SystemExit(f"$ {' '.join(cmd)}\n{r.stdout}{r.stderr}")
        return r.stdout.strip()
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if check and r.returncode:
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return ""


def now_local():
    off = CFG["tz_offset"]
    sign = 1 if off[0] == "+" else -1
    hh, mm = int(off[1:3]), int(off[4:6])
    tz = timezone(sign * timedelta(hours=hh, minutes=mm))
    return datetime.now(tz)


def today_local():
    return now_local().date()


def scheduled_day():
    """The day the nightly run was MEANT for.

    The cron fires late in the evening local time, but Actions routinely delays
    a scheduled job by many minutes under load. A run that slips past midnight
    would otherwise paint tomorrow's square and leave a hole in tonight's, so
    anything landing in the small hours is treated as last night's run.
    """
    now = now_local()
    return (now.date() - timedelta(days=1)) if now.hour < 4 else now.date()


def load_progress():
    if os.path.exists(PROGRESS):
        return json.load(open(PROGRESS))
    return {"commits_total": 0, "days": {}}


def save_progress(p):
    os.makedirs(os.path.dirname(PROGRESS), exist_ok=True)
    json.dump(p, open(PROGRESS, "w"), indent=1, sort_keys=True)


def commit_env(day: str):
    """Pin author AND committer to midday local on the target date.

    Explicit beats implicit here: GitHub buckets a commit onto a square using
    the author date's own offset, so a run that slips past midnight -- or a
    deliberate backdated repair -- still lands on the right day.
    """
    stamp = f"{day}T{CFG['commit_time']}{CFG['tz_offset']}"
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": CFG["author_name"],
        "GIT_AUTHOR_EMAIL": CFG["author_email"],
        "GIT_COMMITTER_NAME": CFG["author_name"],
        "GIT_COMMITTER_EMAIL": CFG["author_email"],
        "GIT_AUTHOR_DATE": stamp,
        "GIT_COMMITTER_DATE": stamp,
    })
    return env


def plan_for(day: str, extra: int):
    entry = SCHED["days"].get(day)
    if entry is None:
        return None, 0
    if extra:
        return entry, extra
    if not entry["commits"]:
        return entry, 0
    # The PR itself and the merge commit are contributions too, so the night
    # needs fewer hand-made commits than the band's headline number.
    return entry, entry.get("made", max(1, entry["commits"] - CFG.get("overhead", 0)))


def paint(day: str, extra: int, dry: bool, prog: dict, use_pr: bool = True, force: bool = False):
    # Idempotence matters more here than it looks: a manual run and the nightly
    # cron landing on the same date would paint it twice, roughly doubling the
    # day's contributions and tipping the square into the wrong band -- which
    # cannot be undone. Repairs pass --extra and are always allowed through.
    done = prog["days"].get(day)
    if done and done.get("status") == "painted" and not extra and not force:
        print(f"{day}: already painted ({done['made']} commits) -- nothing to do. "
              f"Use --extra N to top it up, or --force to repaint.")
        return prog

    entry, n = plan_for(day, extra)
    if entry is None:
        print(f"{day}: outside the schedule -- nothing to do")
        return prog
    if n == 0:
        print(f"{day}: level 0 -- resting")
        return prog

    lvl = entry["level"]
    print(f"{day}: day {entry['day']} (col {entry['col']}, row {entry['row']}) "
          f"level {lvl} -> {n} commits")

    branch = f"{CFG['branch_prefix']}{day}" + (f"-extra" if extra else "")
    env = commit_env(day)

    if not dry:
        run(["git", "fetch", "origin", "main"])
        run(["git", "checkout", "-B", branch, "origin/main"])

    for i in range(1, n + 1):
        prog["commits_total"] += 1
        done = prog["commits_total"]
        msg_args = [sys.executable, os.path.join(HERE, "ascii_reveal.py"),
                    "--commits-done", str(done),
                    "--projected", str(SCHED["projected_commits"])]
        if day == SCHED["end"] and i == n:
            # last commit of the year: land the wipe exactly on the edge
            msg_args = [sys.executable, os.path.join(HERE, "ascii_reveal.py"),
                        "--set", str(SCHED["ascii_cells"])]
        if dry:
            print(f"   commit {i}/{n}: reveal@{done} · day {entry['day']} · L{lvl}")
            continue
        out = run(msg_args, capture=True)
        revealed = out.split("->")[-1].strip()
        msg = f"\U0001f996 reveal {revealed} · day {entry['day']}/364 · L{lvl} {i}/{n}"
        run(["git", "add", f"{REL}/DRAGON.md"])
        run(["git", "commit", "-m", msg], env=env)

    if dry:
        return prog

    prior = prog["days"].get(day, {})
    prog["days"][day] = {
        "level": lvl, "target_commits": entry["commits"],
        "made": prior.get("made", 0) + n,
        "repairs": prior.get("repairs", 0) + (1 if extra else 0),
        "observed": None, "status": "painted",
    }
    save_progress(prog)
    run(["git", "add", f"{REL}/state/progress.json"])
    run(["git", "commit", "--amend", "--no-edit"], env=env)

    if not use_pr:
        run(["git", "push", "origin", f"{branch}:main"])
        run(["git", "checkout", "main"])
        run(["git", "branch", "-D", branch], check=False)
        print(f"{day}: pushed {n} commits straight to main")
        return prog

    run(["git", "push", "-u", "origin", branch, "--force-with-lease"])
    title = f"\U0001f996 commitzilla day {entry['day']}/364 — level {lvl}"
    body = (f"Painting `{day}` at level {lvl} ({n} commits).\n\n"
            f"Square: column {entry['col']}, row {entry['row']} of the 52x7 grid.\n"
            f"ASCII dragon advanced to {prog['commits_total']}/{SCHED['projected_commits']} commits.\n\n"
            f"Automated by [commitzilla](../tree/main/{REL}).")
    run(["gh", "pr", "create", "--base", "main", "--head", branch,
         "--title", title, "--body", body])
    # --merge, never --squash: squashing collapses the night into a single
    # commit and the square comes out a shade too pale.
    run(["gh", "pr", "merge", branch, "--merge", "--delete-branch"])
    run(["git", "checkout", "main"])
    run(["git", "fetch", "origin", "main"])
    run(["git", "reset", "--hard", "origin/main"])
    print(f"{day}: merged {n} commits via PR, branch deleted")
    return prog


def simulate_year():
    prog = {"commits_total": 0, "days": {}}
    origin = date.fromisoformat(SCHED["origin"])
    painted = 0
    for d in range(SCHED["rows"] * SCHED["cols"]):
        day = (origin + timedelta(days=d)).isoformat()
        entry, n = plan_for(day, 0)
        if n:
            painted += 1
            prog["commits_total"] += n
    cells = SCHED["ascii_cells"]
    import math
    final = math.ceil(cells * prog["commits_total"] / SCHED["projected_commits"])
    print(f"painted days      : {painted}/364")
    print(f"commits for real  : {prog['commits_total']} (schedule projects {SCHED['projected_commits']})")
    print(f"ascii reveal ends : {min(final, cells)}/{cells}")
    ok = final >= cells
    print("ascii completes   :", "yes" if ok else "NO -- would stop short")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--extra", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--simulate-year", action="store_true")
    ap.add_argument("--no-pr", action="store_true", help="push straight to main (repair escape hatch)")
    ap.add_argument("--force", action="store_true", help="repaint a day already recorded as painted")
    ap.add_argument("--for-scheduled-day", action="store_true",
                    help="used by the nightly cron: a run delayed past midnight still paints last night")
    a = ap.parse_args()

    if a.simulate_year:
        raise SystemExit(simulate_year())

    day = a.date or (scheduled_day() if a.for_scheduled_day else today_local()).isoformat()
    # A dry run may look at any day -- that is how the art gets previewed.
    # A real run may not: GitHub silently ignores future-dated commits.
    if date.fromisoformat(day) > today_local() and not a.dry_run:
        raise SystemExit(f"refusing to paint the future: {day}")

    prog = load_progress()
    paint(day, a.extra, a.dry_run, prog, use_pr=not a.no_pr, force=a.force)


if __name__ == "__main__":
    main()
