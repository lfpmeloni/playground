"""Read the contribution graph back from GitHub, with no token at all.

The primary route is the public calendar fragment the profile page itself
loads (github.com/users/<login>/contributions). It needs no auth, works from
a Claude Code cloud session (where GraphQL is blocked) and from Actions (where
the built-in GITHUB_TOKEN has no `viewer` to ask about), and it hands back
the exact shade GitHub painted -- data-level -- instead of a colour we have to
decode. With no from/to it covers the trailing year, the same window the
profile page rescales its bands against.

GraphQL stays as a fallback for a machine with a real user login.

Private contributions only appear here if "Include private contributions on my
profile" is switched on -- which they must be anyway for the dragon to show.

  graph.py            print a one-line summary of the last 14 days (smoke test)
"""

import html
import json
import os
import re
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config.json")))
LOGIN = CFG["repo"].split("/")[0]

URL = f"https://github.com/users/{LOGIN}/contributions"

_TD = re.compile(r"<td\b[^>]*>", re.S)
_ATTR = re.compile(r'([\w-]+)="([^"]*)"')
_TIP = re.compile(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>(.*?)</tool-tip>', re.S)
_COUNT = re.compile(r"^\s*(No|\d[\d,]*)\s+contributions?\b")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""
GQL_LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
             "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


class ReadBackError(Exception):
    pass


def parse(page: str):
    """{date: {"date", "count", "level"}} from the calendar HTML."""
    tips = {}
    for target, text in _TIP.findall(page):
        m = _COUNT.match(html.unescape(text))
        if m:
            tips[target] = 0 if m.group(1) == "No" else int(m.group(1).replace(",", ""))
    days = {}
    for tag in _TD.findall(page):
        a = dict(_ATTR.findall(tag))
        if "data-date" not in a or "data-level" not in a:
            continue
        if a.get("id") not in tips:
            raise ReadBackError(f"no count tooltip for {a['data-date']} -- page format changed?")
        days[a["data-date"]] = {"date": a["data-date"], "count": tips[a["id"]],
                                "level": int(a["data-level"])}
    if len(days) < 360:
        raise ReadBackError(f"only {len(days)} days parsed from {URL} -- page format changed?")
    return days


def fetch_html():
    req = urllib.request.Request(URL, headers={"User-Agent": "commitzilla-verify"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return parse(r.read().decode("utf-8"))
    except ReadBackError:
        raise
    except Exception as e:  # network, proxy, HTTP status
        raise ReadBackError(f"GET {URL}: {e}") from e


def fetch_graphql():
    out = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={LOGIN}"],
                         capture_output=True, text=True)
    if out.returncode:
        raise ReadBackError(f"gh api graphql: {out.stderr.strip()}")
    weeks = json.loads(out.stdout)["data"]["user"]["contributionsCollection"] \
        ["contributionCalendar"]["weeks"]
    return {d["date"]: {"date": d["date"], "count": d["contributionCount"],
                        "level": GQL_LEVEL[d["contributionLevel"]]}
            for w in weeks for d in w["contributionDays"]}


def fetch():
    """Trailing-year calendar. Returns (days, source). Raises ReadBackError."""
    errors = []
    for name, fn in (("html", fetch_html), ("graphql", fetch_graphql)):
        try:
            return fn(), name
        except ReadBackError as e:
            errors.append(f"{name}: {e}")
    raise ReadBackError("every read-back route failed:\n  " + "\n  ".join(errors))


def bands(days):
    """Lowest count seen at each level -- reaching it guarantees that level."""
    out = {}
    for d in days.values():
        if d["level"] not in out or d["count"] < out[d["level"]]:
            out[d["level"]] = d["count"]
    return dict(sorted(out.items()))


if __name__ == "__main__":
    try:
        days, src = fetch()
    except ReadBackError as e:
        raise SystemExit(str(e))
    last = sorted(days)[-14:]
    print(f"read {len(days)} days via {src}; bands {bands(days)}")
    print(" ".join(f"{d[5:]}:L{days[d]['level']}({days[d]['count']})" for d in last))
    sys.exit(0)
