#!/usr/bin/env python3
"""Scrape 2026 FIFA World Cup match results from GitHub dataset.

Usage:
    python3 scrape_results.py              # download fresh, save cache
    python3 scrape_results.py --cached     # read from cache only
    python3 scrape_results.py --no-cache   # download fresh, don't save cache
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

MATCHES_URL = "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/matches_detailed.csv"
PLAYER_STATS_URL = "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/player_stats.csv"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "results_cache.json"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Kicktipp-Dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if not lines:
        return []
    headers = [h.strip() for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        vals = [v.strip() for v in line.split(",")]
        row = {}
        for i, h in enumerate(headers):
            row[h] = vals[i] if i < len(vals) else ""
        rows.append(row)
    return rows


def save_cache(data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Cache saved to {CACHE_FILE}", file=sys.stderr)


def load_cache() -> dict | None:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return None


def build_results(matches: list[dict], players: list[dict]) -> dict:
    results = {}
    for m in matches:
        home = m.get("home_fifa_code", "").strip()
        away = m.get("away_fifa_code", "").strip()
        if not home or not away:
            continue
        home_score = m.get("home_score", "").strip()
        away_score = m.get("away_score", "").strip()
        if not home_score or not away_score:
            continue
        match_key = f"{home} - {away}"
        results[match_key] = {
            "home": home,
            "away": away,
            "hg": int(home_score),
            "ag": int(away_score),
            "played": True,
            "stage": m.get("stage_name", ""),
            "date": m.get("date", ""),
            "result_type": m.get("result_type", "Regular"),
        }

    top_scorers = sorted(players, key=lambda p: int(p.get("goals", 0) or 0), reverse=True)[:10]
    top_scorer_list = [
        {"name": p["player_name"], "goals": int(p.get("goals", 0) or 0)}
        for p in top_scorers
    ]

    return {
        "source": "https://github.com/mominullptr/FIFA-World-Cup-2026-Dataset",
        "scraped_at": datetime.now().isoformat(),
        "matches": results,
        "top_scorers": top_scorer_list,
        "stats": {
            "total_matches": len(matches),
            "completed": sum(1 for m in matches if m.get("status") == "Completed"),
            "scheduled": sum(1 for m in matches if m.get("status") == "Scheduled"),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached", action="store_true", help="Read from cache only (no download)")
    parser.add_argument("--no-cache", action="store_true", help="Download fresh, don't save cache")
    args = parser.parse_args()

    # --cached: read from cache only
    if args.cached:
        cached = load_cache()
        if not cached:
            print("ERROR: No cache found. Run without --cached first.", file=sys.stderr)
            sys.exit(1)
        print(f"Loaded from cache ({CACHE_FILE})", file=sys.stderr)
        print(json.dumps(cached, indent=2, ensure_ascii=False))
        return

    # Try to download
    try:
        print("Downloading matches_detailed.csv...", file=sys.stderr)
        matches_text = fetch_text(MATCHES_URL)
        matches = parse_csv(matches_text)

        print("Downloading player_stats.csv...", file=sys.stderr)
        players_text = fetch_text(PLAYER_STATS_URL)
        players = parse_csv(players_text)

        result = build_results(matches, players)

        if not args.no_cache:
            save_cache(result)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"\nTotal matches: {len(matches)}", file=sys.stderr)
        print(f"Completed: {result['stats']['completed']}", file=sys.stderr)
        print(f"Scheduled: {result['stats']['scheduled']}", file=sys.stderr)

    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        cached = load_cache()
        if cached:
            print(f"Falling back to cache ({CACHE_FILE})", file=sys.stderr)
            print(json.dumps(cached, indent=2, ensure_ascii=False))
        else:
            print("ERROR: No cache available and download failed.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
