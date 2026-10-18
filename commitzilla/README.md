# commitzilla 🦖

A Japanese dragon, painted one day at a time onto a contribution graph.

![the target](out/target.png)

Every day from **2026-10-18** to **2027-10-16** is one pixel. The shade of each
pixel is how many contributions land on that date, so drawing the dragon means
making exactly the right amount of noise on exactly the right day.

**Every single day gets painted.** The background is the palest green rather than
empty, and the dragon is picked out in brighter green on top of it.

The tail is painted first. The head lands in the final weeks.

## The one black day

There is exactly one level-0 square in the whole 364 — **2027-08-10** — and it is
the dragon's eye. One contribution of any kind on that date lights it and it can
never be unlit, so everything that writes checks `scripts/blackout.py` first and
does nothing at all that day.

If you are reading this on 2027-08-10: don't push anything. Anywhere.

### What it will really look like

![with background activity](out/with_noise.png)

Felipe's own work lit 111 of the last 365 days. Because the background is level 1
rather than empty, that activity can only nudge a background square up to level 2
instead of punching a black hole through the picture — the dragon still reads
clearly underneath it. Regenerate this preview at the historical rate with
`python3 scripts/preview_noise.py [seed]`.

The eye is the exception: it is the one square real activity would genuinely
destroy, which is what `blackout.py` is for.

## The other dragon

The same picture is being uncovered in [`DRAGON.md`](DRAGON.md), one sliver per
commit, wiping left to right in lockstep with the squares. Neither is "junk
commits": every commit in the nightly batch carries a real diff, because it
advances the reveal. Both finish on the same day.

## How it runs

| | |
|---|---|
| **Painter** | `.github/workflows/commitzilla.yml` — nightly cron. Makes the commits, opens one PR, merges it, deletes the branch. Dumb and reliable. |
| **Supervisor** | a nightly Claude routine following [`AGENT_BRIEF.md`](AGENT_BRIEF.md). Reads the real graph back, repairs pale squares, retunes the shading, keeps the journal. |

One PR per night — 363 of them over the year — each merged with `--merge` and
`--delete-branch`, so the repo never holds more than a single branch.

## Why it needs a supervisor at all

GitHub's five shades are **relative to the busiest day of your trailing year**, not
fixed counts. Real work moves that maximum, which silently demotes squares that
were already painted. So the system does not fire and forget: it reads the actual
colour of every square back out of the GraphQL API, learns the live thresholds
from the colours themselves, and tops up anything that came out pale using
backdated commits. Contributions can never be removed, which is why every target
aims at the *bottom* of its band and leaves headroom.

## Files

```
config.json          shading, identity, dates
art/dragon.grid      7x52 of levels 0-4 — the target image, hand-tunable
art/dragon_ascii.txt the big ASCII version DRAGON.md reveals
plan/schedule.json   frozen date -> level -> commit count
state/               progress, journal, achievements, last observed grid
out/                 target.png, actual.png, and SVGs for this page
scripts/             build_*, paint, verify, render, ascii_reveal, achievements
```

## Checking on it

```bash
python3 scripts/render.py --target            # the whole dragon, today
python3 scripts/blackout.py                   # is today the eye? (exit 1 = do nothing)
python3 scripts/verify.py --days 30           # target vs. what GitHub shows
python3 scripts/paint.py --date 2027-03-14 --dry-run
python3 scripts/paint.py --simulate-year      # replay all 364 days
python3 scripts/achievements.py --status
```

## A note on tokens

With the built-in `GITHUB_TOKEN`, the nightly PR is opened and merged by
`github-actions[bot]`, not by Felipe. Measured on day 0: the hand-made commits
count toward the graph, the PR and the merge commit do not. **The art works; the
PR-based achievements do not.**

To earn Pull Shark and YOLO, add a fine-grained PAT as the repo secret
`COMMITZILLA_TOKEN` (scoped to this repo: Contents, Pull requests and Issues, all
read/write). The workflow already prefers it. **If you add it, set `overhead` to
`2` in `config.json` in the same change** — the PR and merge commit then start
counting, and without that correction every square overshoots by two, which
cannot be undone.

## Achievements

Tracked in [`state/achievements.md`](state/achievements.md). Pull Shark, YOLO and
Quickdraw are pursued automatically. Pair Extraordinaire, Starstruck, Galaxy Brain
and Public Sponsor are recorded but not automated, because each one needs either
another real person or a spending decision — the reasons are written down there
rather than quietly skipped.

## Honest note

These commits are decorative. They are not work, and a graph painted this way
stops being a signal of real activity. That was the point of the exercise.
