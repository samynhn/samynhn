#!/usr/bin/env python3
"""Draw the neofetch-style profile card and refresh the paper links in README.md.

Inputs (all in data/):
  github.json          GitHub stats (scripts/fetch_github.py, this repo)
  ai-summary.json      pushed here by the private ai-usage repo
  papers-summary.json  pushed here by the private paper-library repo
  ascii.txt            the portrait
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import render_profile  # noqa: E402

GITHUB_SINCE = "2019-07-04"  # account creation date, for the Uptime row
D = ROOT / "data"


def load(name):
    p = D / name
    return json.loads(p.read_text()) if p.exists() else {}


today = dt.datetime.now(ZoneInfo("Asia/Taipei")).date()
gh, ai, pp = load("github.json"), load("ai-summary.json"), load("papers-summary.json")
st = {k: gh.get(k, "-") for k in ("repos", "stars", "commits", "followers", "loc", "loc_add", "loc_del")}
st.update(ai_tokens_30d=ai.get("tokens_30d", "-"), ai_primary=ai.get("primary", "-"),
          papers=pp.get("papers", "-"), top_folder=pp.get("top_folder", "-"),
          uptime=render_profile.uptime(dt.date.fromisoformat(GITHUB_SINCE), today))
art = (D / "ascii.txt").read_text().rstrip("\n").split("\n") if (D / "ascii.txt").exists() else None
for theme in render_profile.THEMES:
    (ROOT / "assets" / f"profile-{theme}.svg").write_text(render_profile.render(st, theme, art))
print("drew profile cards")
