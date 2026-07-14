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
TEAMS_URL = "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/teams.csv"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "results_cache.json"

FIFA_TO_ISO = {
    "AFG": "AF", "ALB": "AL", "ALG": "DZ", "AND": "AD", "ANG": "AO",
    "ARG": "AR", "ARM": "AM", "AUS": "AU", "AUT": "AT", "AZE": "AZ",
    "BHR": "BH", "BAN": "BD", "BLR": "BY", "BEL": "BE", "BEN": "BJ",
    "BOL": "BO", "BIH": "BA", "BRA": "BR", "BUL": "BG", "BUR": "BF",
    "BDI": "BI", "CPV": "CV", "CMR": "CM", "CAN": "CA", "CHI": "CL",
    "CHN": "CN", "COL": "CO", "COD": "CD", "CIV": "CI", "CRC": "CR",
    "CRO": "HR", "CUB": "CU", "CYP": "CY", "CZE": "CZ", "DEN": "DK",
    "ECU": "EC", "EGY": "EG", "SLV": "SV", "ENG": "GB", "EQG": "GQ",
    "ERI": "ER", "EST": "EE", "ETH": "ET", "FRO": "FO", "FIJ": "FJ",
    "FIN": "FI", "FRA": "FR", "GAB": "GA", "GAM": "GM", "GEO": "GE",
    "GER": "DE", "GHA": "GH", "GRE": "GR", "GRN": "GD", "GUA": "GT",
    "GUI": "GN", "GNB": "GW", "GUY": "GY", "HAI": "HT", "HON": "HN",
    "HKG": "HK", "HUN": "HU", "ISL": "IS", "IND": "IN", "IDN": "ID",
    "IRN": "IR", "IRQ": "IQ", "ISR": "IL", "ITA": "IT", "JAM": "JM",
    "JPN": "JP", "JOR": "JO", "KAZ": "KZ", "KEN": "KE", "KOR": "KR",
    "KOS": "XK", "KUW": "KW", "KGZ": "KG", "LAO": "LA", "LVA": "LV",
    "LIB": "LB", "LES": "LS", "LBR": "LR", "LBY": "LY", "LIE": "LI",
    "LTU": "LT", "LUX": "LU", "MAC": "MO", "MAD": "MG", "MWI": "MW",
    "MAS": "MY", "MDV": "MV", "MLI": "ML", "MLT": "MT", "MTN": "MR",
    "MRI": "MU", "MEX": "MX", "MDA": "MD", "MNG": "MN", "MNE": "ME",
    "MAR": "MA", "MOZ": "MZ", "MYA": "MM", "NAM": "NA", "NEP": "NP",
    "NED": "NL", "NZL": "NZ", "NCA": "NI", "NIG": "NE", "NGA": "NG",
    "NIR": "GB", "NOR": "NO", "OMA": "OM", "PAK": "PK", "PLE": "PS",
    "PAN": "PA", "PAR": "PY", "PER": "PE", "PHI": "PH", "POL": "PL",
    "POR": "PT", "QAT": "QA", "ROU": "RO", "RUS": "RU", "RWA": "RW",
    "KSA": "SA", "SCO": "GB-SCT", "SEN": "SN", "SRB": "RS", "SEY": "SC",
    "SLE": "SL", "SGP": "SG", "SVK": "SK", "SVN": "SI", "SOL": "SB",
    "SOM": "SO", "RSA": "ZA", "ESP": "ES", "SUD": "SD", "SUR": "SR",
    "SWZ": "SZ", "SWE": "SE", "SUI": "CH", "SYR": "SY", "TAH": "PF",
    "TJK": "TJ", "TAN": "TZ", "THA": "TH", "TOG": "TG", "TRI": "TT",
    "TUN": "TN", "TUR": "TR", "TKM": "TM", "UGA": "UG", "UKR": "UA",
    "UAE": "AE", "URU": "UY", "USA": "US", "UZB": "UZ", "VEN": "VE",
    "VIE": "VN", "WAL": "GB-WLS", "YEM": "YE", "ZAM": "ZM", "ZIM": "ZW",
    "CUW": "CW", "CUR": "CW",
}


def flag_emoji(fifa_code: str) -> str:
    iso = FIFA_TO_ISO.get(fifa_code, fifa_code)
    if "-" in iso:
        iso = iso.split("-")[0]
    if len(iso) != 2:
        return ""
    a = ord(iso[0].upper()) - ord("A")
    b = ord(iso[1].upper()) - ord("A")
    return chr(0x1F1E6 + a) + chr(0x1F1E6 + b)


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


def build_results(matches: list[dict], players: list[dict], teams: list[dict]) -> dict:
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

    team_map = {}
    for t in teams:
        tid = t.get("team_id", "").strip()
        if tid:
            team_map[tid] = {
                "name": t.get("team_name", "").strip(),
                "fifa_code": t.get("fifa_code", "").strip(),
            }

    player_team_map = {}
    for p in players:
        pid = p.get("player_id", "").strip()
        tid = p.get("team_id", "").strip()
        if pid and tid in team_map:
            player_team_map[pid] = team_map[tid]

    top_scorers = sorted(players, key=lambda p: int(p.get("goals", 0) or 0), reverse=True)[:10]
    top_scorer_list = []
    for p in top_scorers:
        goals = int(p.get("goals", 0) or 0)
        if goals == 0:
            break
        pid = p.get("player_id", "").strip()
        team_info = player_team_map.get(pid, {})
        fifa_code = team_info.get("fifa_code", "")
        country_name = team_info.get("name", "")
        top_scorer_list.append({
            "name": p["player_name"],
            "country_name": country_name,
            "country_code": fifa_code,
            "flag": flag_emoji(fifa_code),
            "goals": goals,
        })

    final_matches = [m for m in matches if m.get("stage_name", "").strip() == "Final"]
    wc_winner_determined = any(
        m.get("home_score", "").strip() and m.get("away_score", "").strip()
        for m in final_matches
    )

    top_goal_count = top_scorer_list[0]["goals"] if top_scorer_list else 0
    top_scorer_names = {s["name"] for s in top_scorer_list if s["goals"] == top_goal_count}

    return {
        "source": "https://github.com/mominullptr/FIFA-World-Cup-2026-Dataset",
        "scraped_at": datetime.now().isoformat(),
        "matches": results,
        "top_scorers": top_scorer_list,
        "stats": {
            "total_matches": len(matches),
            "completed": sum(1 for m in matches if m.get("status") == "Completed"),
            "scheduled": sum(1 for m in matches if m.get("status") == "Scheduled"),
            "wc_winner_determined": wc_winner_determined,
            "top_scorer_names": list(top_scorer_names),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cached", action="store_true", help="Read from cache only (no download)")
    parser.add_argument("--no-cache", action="store_true", help="Download fresh, don't save cache")
    args = parser.parse_args()

    if args.cached:
        cached = load_cache()
        if not cached:
            print("ERROR: No cache found. Run without --cached first.", file=sys.stderr)
            sys.exit(1)
        print(f"Loaded from cache ({CACHE_FILE})", file=sys.stderr)
        print(json.dumps(cached, indent=2, ensure_ascii=False))
        return

    try:
        print("Downloading matches_detailed.csv...", file=sys.stderr)
        matches_text = fetch_text(MATCHES_URL)
        matches = parse_csv(matches_text)

        print("Downloading player_stats.csv...", file=sys.stderr)
        players_text = fetch_text(PLAYER_STATS_URL)
        players = parse_csv(players_text)

        print("Downloading teams.csv...", file=sys.stderr)
        teams_text = fetch_text(TEAMS_URL)
        teams = parse_csv(teams_text)

        result = build_results(matches, players, teams)

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
