#!/usr/bin/env python3
"""Fetch GitHub profile stats into data/github.json (run in GitHub Actions).

  repos      public repositories (same number GitHub shows on your profile)
  stars      stars across those repos
  followers  followers
  commits / loc_add / loc_del   your commits and line changes in your repos (incl. forks)
                                (GET /repos/{o}/{r}/stats/contributors)

Usage: GITHUB_TOKEN=... python3 scripts/fetch_github.py <user> data/github.json
If the API fails, the previous file is left untouched.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"


def get(path, tries=8):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "profile-readme",
        **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {})})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 202:  # stats are being computed, ask again
                    time.sleep(3 + 2 * i)
                    continue
                if r.status == 204:
                    return []
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (502, 503) and i < tries - 1:
                time.sleep(3)
                continue
            raise
    return None  # still computing


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    user, out = sys.argv[1], sys.argv[2]
    prev = json.load(open(out)) if os.path.exists(out) else {}
    u = get(f"/users/{user}")
    repos = []
    page = 1
    while True:
        batch = get(f"/users/{user}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    own = [r for r in repos if not r["fork"]]

    per_repo, commits, add, dele = {}, 0, 0, 0
    for r in repos:  # forks too: only your own commits are counted
        stats = get(f"/repos/{user}/{r['name']}/stats/contributors")
        if not stats:  # still computing (or empty cache on GitHub's side): reuse last known numbers
            old = prev.get("per_repo", {}).get(r["name"])
            if old:
                per_repo[r["name"]] = old
            continue
        for c in stats or []:
            if (c.get("author") or {}).get("login", "").lower() == user.lower():
                a = sum(w["a"] for w in c["weeks"]); d = sum(w["d"] for w in c["weeks"])
                per_repo[r["name"]] = [c["total"], a, d]
    for c, a, d in per_repo.values():
        commits += c; add += a; dele += d

    data = {
        "updated": dt.date.today().isoformat(),
        "repos": str(u["public_repos"]),
        "stars": str(sum(r["stargazers_count"] for r in own)),
        "followers": str(u["followers"]),
        "commits": f"{commits:,}",
        "loc": f"{add - dele:,}", "loc_add": f"{add:,}", "loc_del": f"{dele:,}",
        "contributed": str(len(per_repo)),
        "per_repo": per_repo,
    }
    json.dump(data, open(out, "w"), indent=1)
    print(f"github: {data['repos']} repos, {data['commits']} commits, {data['loc']} loc")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep yesterday's numbers rather than failing the whole update
        print(f"! github fetch failed: {e}", file=sys.stderr)
