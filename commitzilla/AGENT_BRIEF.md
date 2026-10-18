# commitzilla — brief for the nightly agent

Read this first, every night, before touching anything.

## What this is

A 🦖-sized art project. A Japanese dragon is being painted onto Felipe's GitHub
contribution graph, one day per pixel, over 364 days from **2026-10-18** to
**2027-10-16**. Each day has a target shade (1–4). Hitting that shade means making
the right number of contributions on that date.

**Every day of the year is painted.** The background is level 1, not empty, so the
graph is a field of pale green with the dragon picked out in brighter green on top
of it. There is exactly **one** level-0 square in the whole year — the dragon's
eye, **2027-08-10** — and it is the only black day. That is the easter egg.

The same dragon is simultaneously being uncovered in `DRAGON.md`, one sliver per
commit, so the two finish together.

## Division of labour

- **GitHub Actions** (`.github/workflows/commitzilla.yml`, at the repo root) is the
  painter. It runs nightly, makes the commits, opens one PR and merges it. It is
  deliberately dumb and deliberately reliable — a missing night leaves a visible
  hole in a picture that takes a year to draw.
- **You, the nightly routine,** are the supervisor. You do not need to paint.
  You check that the painter worked, repair what drifted, and keep the records.

## Your checklist

1. `python3 commitzilla/scripts/verify.py --days 14` — compare the real graph to the target.
2. Run `python3 commitzilla/scripts/blackout.py`. If it exits 1, stop here and do
   nothing else at all today.
3. If any square came out **pale**, repair it: `verify.py --repair` makes backdated
   commits on that date through the normal one-PR-one-merge path. Squares that came
   out **too dark** cannot be fixed; contributions cannot be removed. Log and move on.
4. If the bands have shifted, update `level_commits` in `config.json` to sit a notch
   above the thresholds `verify.py` reports, and say so in the journal.
5. `python3 commitzilla/scripts/render.py --target && python3 commitzilla/scripts/render.py --actual`
6. `python3 commitzilla/scripts/achievements.py --status`
7. Append one line to `state/journal.md`: date, what the painter did, what you repaired.
8. Commit the above through the same PR-and-merge path. One branch at a time.

## Invariants — do not break these

- **Never touch a file outside `commitzilla/`**, except the workflow at
  `.github/workflows/commitzilla.yml`. This repo has real projects in it; staying
  inside our own directory is what makes a conflict with Felipe's own work
  essentially impossible.
- **Never force-push, never rewrite `main`.** Append only.
- **Exactly one branch.** Every PR is merged with `--merge` and `--delete-branch`.
  Never `--squash`: squashing collapses the night's commits into one and the
  square comes out a shade too pale.
- **Never paint a future date.** GitHub ignores future-dated commits.
- **2027-08-10 is a total blackout.** It is the dragon's eye, the only black square
  of the year. No commit, no PR, no issue, no journal entry — nothing. A single
  contribution of any kind lights it and it can never be unlit. Run
  `python3 commitzilla/scripts/blackout.py` before anything that writes; it exits 1
  on that day. On a blackout day your entire job is to do nothing.
- **Never commit secrets.** There are live credentials elsewhere in this workspace.
- **`overhead` in `config.json` is coupled to which token the workflow uses.** Measured
  on day 0: with the built-in `GITHUB_TOKEN` the PR and the merge commit are both
  attributed to `github-actions[bot]`, so neither counts toward Felipe's graph and
  `overhead` is **0**. If a `COMMITZILLA_TOKEN` secret (a PAT) is ever added, they
  start counting as his and `overhead` must be raised to **2** in the same change.
  Getting this wrong overshoots every square by two, and an overshoot is permanent.
- If the graph read-back fails, **stop and report**. Do not improvise commits; a
  wrong guess is permanent.

## Shape of the problem, so the numbers make sense

GitHub's five shades are **relative to the busiest day of the trailing year**, not
absolute counts. As Felipe's real work moves that maximum, a fixed commit count
drifts into the wrong band. Two consequences:

- Aim at the **bottom** of a band, never the top. Topping up later is possible;
  taking contributions away is not.
- Felipe's own work adds to whatever day it lands on. Since the background is
  level 1 rather than empty, that noise now only risks nudging a background
  square up to level 2, which is cosmetically minor — it can no longer punch a
  black hole in the picture. The one exception is the eye, which it would ruin.
- A square can always be repaired upward with backdated commits, which is the
  whole reason this survives a missed night.

`verify.py` learns the live thresholds from the colours the GraphQL API returns
rather than hardcoding them. Trust it over any number written in a doc.
