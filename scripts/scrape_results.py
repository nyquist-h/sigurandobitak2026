#!/usr/bin/env python3
"""Scrape 2026 FIFA World Cup match results from GitHub dataset."""

import json
import sys
import urllib.request

MATCHES_URL = "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/matches_detailed.csv"
PLAYER_STATS_URL = "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/player_stats.csv"


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
        # Simple CSV parse (no quoted commas in this dataset)
        vals = [v.strip() for v in line.split(",")]
        row = {}
        for i, h in enumerate(headers):
            row[h] = vals[i] if i < len(vals) else ""
        rows.append(row)
    return rows


def main():
    print("Downloading matches_detailed.csv...", file=sys.stderr)
    matches_text = fetch_text(MATCHES_URL)
    matches = parse_csv(matches_text)

    print("Downloading player_stats.csv...", file=sys.stderr)
    players_text = fetch_text(PLAYER_STATS_URL)
    players = parse_csv(players_text)

    # Build results dict
    results = {}
    for m in matches:
        home = m.get("home_fifa_code", "").strip()
        away = m.get("away_fifa_code", "").strip()
        if not home or not away:
            continue  # not played yet

        home_score = m.get("home_score", "").strip()
        away_score = m.get("away_score", "").strip()
        if not home_score or not away_score:
            continue  # not played yet

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

    # Top scorers
    top_scorers = sorted(players, key=lambda p: int(p.get("goals", 0) or 0), reverse=True)[:10]
    top_scorer_list = [
        {"name": p["player_name"], "goals": int(p.get("goals", 0) or 0)}
        for p in top_scorers
    ]

    output = {
        "source": "https://github.com/mominullptr/FIFA-World-Cup-2026-Dataset",
        "scraped_at": __import__("datetime").datetime.now().isoformat(),
        "matches": results,
        "top_scorers": top_scorer_list,
        "stats": {
            "total_matches": len(matches),
            "completed": sum(1 for m in matches if m.get("status") == "Completed"),
            "scheduled": sum(1 for m in matches if m.get("status") == "Scheduled"),
        },
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\nTotal matches: {len(matches)}", file=sys.stderr)
    print(f"Completed: {output['stats']['completed']}", file=sys.stderr)
    print(f"Scheduled: {output['stats']['scheduled']}", file=sys.stderr)


if __name__ == "__main__":
    main()
