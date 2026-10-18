"""Is today the one day of the year that must stay black?

Exactly one square in the 364 is level 0 -- the dragon's eye, 2027-08-10. It is
the only black day of the year and the whole joke depends on it staying that
way. A single contribution of any kind lights it, permanently.

Everything that might commit, open a PR or open an issue must check this first.

  exit 0  -> normal day, go ahead
  exit 1  -> blackout. Do nothing at all. No commit, no PR, no issue.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config.json")))
SCHED = json.load(open(os.path.join(ROOT, "plan", "schedule.json")))

BLACKOUT = sorted(d for d, v in SCHED["days"].items() if v["level"] == 0)


def today_local():
    off = CFG["tz_offset"]
    sign = 1 if off[0] == "+" else -1
    tz = timezone(sign * timedelta(hours=int(off[1:3]), minutes=int(off[4:6])))
    return datetime.now(tz).date()


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else today_local().isoformat()
    # The window is deliberately generous: a run that straddles local midnight
    # must not light the eye from either side of it.
    nearby = [b for b in BLACKOUT
              if abs((date.fromisoformat(b) - date.fromisoformat(day)).days) < 1]
    if nearby:
        print(f"BLACKOUT: {day} is the dragon's eye. Do nothing today -- "
              f"no commit, no PR, no issue. One contribution ruins it permanently.")
        return 1
    print(f"{day}: not a blackout day (the eye is {', '.join(BLACKOUT)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
