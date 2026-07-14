#!/usr/bin/env python3
"""
build_data.py — Extract Kicktipp zip exports, fetch match results,
compute all derived statistics, and emit site/data/data.js.
"""

import csv
import io
import json
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SITE_DATA = ROOT / "site" / "data"
SITE_DATA.mkdir(parents=True, exist_ok=True)

# ── Team code alias map (Kicktipp → standard FIFA) ─────────────────────
TEAM_ALIAS = {
    "CH": "SUI",
    "CUR": "CUW",
    "SAR": "KSA",
    "IRK": "IRQ",
    "CPV": "CPV",
    "CIV": "CIV",
    "COD": "COD",
    "KSA": "KSA",
    "RSA": "RSA",
    "BIH": "BIH",
    "CZE": "CZE",
    "PAR": "PAR",
    "MEX": "MEX",
    "QAT": "QAT",
    "BRA": "BRA",
    "MOR": "MAR",
    "HAI": "HAI",
    "SCO": "SCO",
    "AUS": "AUS",
    "TUR": "TUR",
    "KOR": "KOR",
    "CAN": "CAN",
    "USA": "USA",
    "GER": "GER",
    "NED": "NED",
    "JPN": "JPN",
    "SWE": "SWE",
    "TUN": "TUN",
    "BEL": "BEL",
    "EGY": "EGY",
    "IRN": "IRN",
    "NZL": "NZL",
    "ESP": "ESP",
    "URU": "URU",
    "FRA": "FRA",
    "SEN": "SEN",
    "IRQ": "IRQ",
    "NOR": "NOR",
    "ARG": "ARG",
    "ALG": "ALG",
    "AUT": "AUT",
    "JOR": "JOR",
    "POR": "POR",
    "COL": "COL",
    "ENG": "ENG",
    "CRO": "CRO",
    "GHA": "GHA",
    "PAN": "PAN",
    "UZB": "UZB",
}


def normalize_code(code: str) -> str:
    code = code.strip()
    return TEAM_ALIAS.get(code, code)


# ── Stage key mapping ──────────────────────────────────────────────────
STAGE_KEYS = [
    "md1", "md2", "md3", "md4", "md5", "md6", "md7", "md8", "md9", "md10",
    "r32", "r16", "qf", "sf", "final",
]

STAGE_LABELS = {
    "md1": "Matchday 1",
    "md2": "Matchday 2",
    "md3": "Matchday 3",
    "md4": "Matchday 4",
    "md5": "Matchday 5",
    "md6": "Matchday 6",
    "md7": "Matchday 7",
    "md8": "Matchday 8",
    "md9": "Matchday 9",
    "md10": "Matchday 10",
    "r32": "Sixteenth final",
    "r16": "Round of 16",
    "qf": "Quarter-final",
    "sf": "Semi-finals",
    "final": "Final",
}

# Map CSV filename patterns to stage keys
def filename_to_stage(filename: str) -> str | None:
    fn = filename.lower()
    if "general overview" in fn:
        return "overview"
    if "leaderboard" in fn:
        return "leaderboard"
    if "bonus" in fn:
        return "bonus"
    for i in range(1, 11):
        if f"matchday {i}" in fn:
            return f"md{i}"
    if "sixteenth final" in fn:
        return "r32"
    if "round of 16" in fn:
        return "r16"
    if "quarter-final" in fn:
        return "qf"
    if "semi-final" in fn:
        return "sf"
    if "final" in fn and "quarter" not in fn:
        return "final"
    return None


# ── CSV parsing ────────────────────────────────────────────────────────
def parse_csv_zip(zip_path: Path) -> list[dict]:
    """Extract and parse a single CSV from a zip file."""
    with zipfile.ZipFile(zip_path) as z:
        name = z.namelist()[0]
        data = z.read(name).decode("utf-8")
    reader = csv.DictReader(io.StringIO(data), delimiter=";", quotechar='"')
    rows = []
    for row in reader:
        cleaned = {}
        for k, v in row.items():
            key = k.strip() if k else k
            val = v.strip() if v else ""
            cleaned[key] = val
        rows.append(cleaned)
    return rows


# ── Extract all zip files ─────────────────────────────────────────────
def load_all_zips() -> dict:
    """Load all zip files and return structured data."""
    data = {
        "overview": None,
        "leaderboard": None,
        "bonus": None,
        "predictions": {},
    }

    zips = sorted(ROOT.glob("*.csv.zip"))
    print(f"Found {len(zips)} zip files", file=sys.stderr)

    for zp in zips:
        stage = filename_to_stage(zp.name)
        if not stage:
            print(f"WARNING: Unknown stage for {zp.name}", file=sys.stderr)
            continue

        rows = parse_csv_zip(zp)
        if stage == "overview":
            data["overview"] = rows
        elif stage == "leaderboard":
            data["leaderboard"] = rows
        elif stage == "bonus":
            data["bonus"] = rows
        else:
            data["predictions"][stage] = rows

    return data


# ── Fetch match results ───────────────────────────────────────────────
def fetch_results() -> dict:
    """Download match results from GitHub dataset (with cache fallback)."""
    sys.path.insert(0, str(Path(__file__).parent))
    from scrape_results import build_results, fetch_text, load_cache, parse_csv

    try:
        matches_text = fetch_text(
            "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/matches_detailed.csv"
        )
        matches = parse_csv(matches_text)

        players_text = fetch_text(
            "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/player_stats.csv"
        )
        players = parse_csv(players_text)

        teams_text = fetch_text(
            "https://raw.githubusercontent.com/mominullptr/FIFA-World-Cup-2026-Dataset/main/teams.csv"
        )
        teams = parse_csv(teams_text)

        result = build_results(matches, players, teams)
        from scrape_results import save_cache
        save_cache(result)
        return result
    except Exception as e:
        print(f"Download failed: {e}, trying cache...", file=sys.stderr)
        cached = load_cache()
        if cached:
            print("Using cached results.", file=sys.stderr)
            return cached
        raise


# ── Parse user predictions ────────────────────────────────────────────
def parse_predictions(data: dict) -> dict:
    """Parse prediction CSVs into structured format.
    Returns: {stage_key: {user_name: {match_key: "h:a" | ""}}}
    """
    predictions = {}

    for stage_key, rows in data["predictions"].items():
        stage_preds = {}
        for row in rows:
            name = row.get("Name", "").strip()
            if not name:
                continue
            user_preds = {}
            for col, val in row.items():
                if col in ("Name", "PlayerID"):
                    continue
                if " - " in col:
                    val = val.strip()
                    parts = col.split(" - ")
                    if len(parts) == 2:
                        home_code = normalize_code(parts[0])
                        away_code = normalize_code(parts[1])
                        match_key = f"{home_code} - {away_code}"
                        user_preds[match_key] = val
            stage_preds[name] = user_preds
        predictions[stage_key] = stage_preds

    return predictions


# ── Compute prediction accuracy ───────────────────────────────────────
def compute_accuracy(predictions: dict, results: dict) -> dict:
    """Compute per-user prediction accuracy stats."""
    stats = {}

    for stage_key, stage_preds in predictions.items():
        for user_name, user_preds in stage_preds.items():
            if user_name not in stats:
                stats[user_name] = {
                    "exact": 0, "exact_draw": 0, "winner_plus_diff": 0,
                    "draw_pred_no_exact": 0, "correct_winner": 0, "missed": 0,
                    "total_predicted": 0, "total_played": 0, "four_pointers": [],
                }

            for match_key, pred in user_preds.items():
                if not pred or pred in ("-:-", "0:999"):
                    continue

                stats[user_name]["total_predicted"] += 1

                if match_key not in results:
                    continue

                result = results[match_key]
                hg, ag = result["hg"], result["ag"]
                stats[user_name]["total_played"] += 1

                pred_match = re.match(r"(\d+):(\d+)", pred)
                if not pred_match:
                    stats[user_name]["missed"] += 1
                    continue

                ph, pa = int(pred_match.group(1)), int(pred_match.group(2))
                pred_diff = ph - pa
                real_diff = hg - ag

                if ph == hg and pa == ag:
                    stats[user_name]["exact"] += 1
                    if hg == ag:
                        stats[user_name]["exact_draw"] += 1
                    stats[user_name]["four_pointers"].append({
                        "match": match_key, "predicted": pred,
                        "actual": f"{hg}:{ag}", "stage": stage_key,
                    })
                elif hg == ag and ph == pa:
                    stats[user_name]["draw_pred_no_exact"] += 1
                elif hg != ag and ph != pa:
                    if (pred_diff > 0 and real_diff > 0) or (pred_diff < 0 and real_diff < 0):
                        if abs(pred_diff) == abs(real_diff):
                            stats[user_name]["winner_plus_diff"] += 1
                        else:
                            stats[user_name]["correct_winner"] += 1
                    else:
                        stats[user_name]["missed"] += 1
                elif (pred_diff > 0 and real_diff > 0) or (pred_diff < 0 and real_diff < 0):
                    stats[user_name]["correct_winner"] += 1
                else:
                    stats[user_name]["missed"] += 1

    return stats


# ── Parse overview data ───────────────────────────────────────────────
def parse_overview(rows: list[dict]) -> tuple[list[str], dict, dict]:
    """Parse general overview CSV."""
    user_names = []
    points_per_stage = {}
    bonus_points = {}

    for row in rows:
        name = row.get("Name", "").strip()
        if not name:
            continue
        user_names.append(name)
        points_per_stage[name] = {}
        for stage_key in STAGE_KEYS:
            label = STAGE_LABELS.get(stage_key, stage_key)
            val = row.get(label, "0").strip()
            try:
                points_per_stage[name][stage_key] = int(val)
            except (ValueError, TypeError):
                points_per_stage[name][stage_key] = 0
        bonus_points[name] = int(row.get("Bonus points", "0").strip() or "0")

    return user_names, points_per_stage, bonus_points


# ── Parse bonus predictions ───────────────────────────────────────────
def parse_bonus(rows: list[dict]) -> dict:
    """Parse bonus predictions CSV."""
    bonus = {}
    for row in rows:
        name = row.get("Name", "").strip()
        if not name:
            continue
        bonus[name] = {
            "wc_winner": row.get("WC", "").strip(),
            "top_scorer": row.get("Tor", "").strip(),
        }
    return bonus


# ── Compute stage rankings ────────────────────────────────────────────
def compute_rankings(points_per_stage: dict, user_names: list[str]) -> dict:
    """Compute cumulative rankings per stage."""
    rankings = {}
    cumulative = {name: 0 for name in user_names}

    for stage_key in STAGE_KEYS:
        for name in user_names:
            cumulative[name] += points_per_stage.get(name, {}).get(stage_key, 0)

        sorted_users = sorted(user_names, key=lambda n: (-cumulative[n], n))

        stage_rankings = []
        prev_points = None
        prev_rank = 0
        for i, name in enumerate(sorted_users):
            pts = cumulative[name]
            if pts == prev_points:
                rank = prev_rank
            else:
                rank = i + 1
                prev_rank = rank
            prev_points = pts
            stage_rankings.append({
                "user": name, "rank": rank, "points": pts,
                "stage_points": points_per_stage.get(name, {}).get(stage_key, 0),
            })

        rankings[stage_key] = stage_rankings

    return rankings


# ── Compute time on 1st place ─────────────────────────────────────────
def compute_time_on_top(rankings: dict, user_names: list[str]) -> dict:
    """Compute how many stages each user was in 1st place (with tie-splitting)."""
    time_on_top = {name: 0.0 for name in user_names}

    for stage_key, stage_rankings in rankings.items():
        first_place = [r for r in stage_rankings if r["rank"] == 1]
        if first_place:
            split = 1.0 / len(first_place)
            for r in first_place:
                time_on_top[r["user"]] += split

    return time_on_top


# ── Compute "what is needed to win" ───────────────────────────────────
def compute_what_if(
    points_per_stage: dict,
    user_names: list[str],
    predictions: dict,
    results: dict,
    results_meta: dict,
    bonus_preds: dict,
    top_scorers: list[dict],
) -> dict:
    """For each user, compute points possible and status."""
    current = {}
    for name in user_names:
        current[name] = sum(points_per_stage.get(name, {}).get(s, 0) for s in STAGE_KEYS)

    kicktipp_pending = {}
    for name in user_names:
        cnt = 0
        for stage_key, stage_preds in predictions.items():
            user_preds = stage_preds.get(name, {})
            for mk, pv in user_preds.items():
                if pv and pv not in ("-:-", "0:999") and mk not in results:
                    cnt += 1
        kicktipp_pending[name] = cnt

    wc_determined = results_meta.get("wc_winner_determined", False)
    top_scorer_countries = set()
    if top_scorers:
        top_goal_count = top_scorers[0]["goals"]
        top_scorer_countries = {
            s.get("country_code", "")
            for s in top_scorers
            if s["goals"] == top_goal_count and s.get("country_code")
        }

    bonus_eligible = {}
    for name in user_names:
        bp = bonus_preds.get(name, {})
        wc_pick = bp.get("wc_winner", "")
        ts_pick = bp.get("top_scorer", "")
        wc_ok = not wc_determined
        ts_ok = not top_scorer_countries or ts_pick in top_scorer_countries
        bonus_eligible[name] = (10 if wc_ok else 0) + (10 if ts_ok else 0)

    points_possible = {}
    for name in user_names:
        points_possible[name] = 4 * kicktipp_pending[name] + bonus_eligible[name]

    sorted_users = sorted(user_names, key=lambda n: (-current[n], n))
    leader_current = current[sorted_users[0]] if sorted_users else 0

    what_if = {}
    for name in user_names:
        above = [u for u in sorted_users if current[u] > current[name]]
        max_possible = current[name] + points_possible[name]

        if not above:
            status = "leading"
            verdict = f"{name} is currently leading with {current[name]} points."
        elif max_possible < leader_current:
            status = "eliminated"
            verdict = f"{name} is eliminated. Max possible ({max_possible}) cannot reach the leader ({leader_current})."
        else:
            status = "possible"
            gaps = []
            for u in above:
                gap = current[u] - current[name]
                gaps.append(f"{u}: {gap} pts behind")
            verdict = f"{name} can still earn up to {points_possible[name]} points. {' '.join(gaps)}"

        what_if[name] = {
            "current": current[name],
            "points_possible": points_possible[name],
            "kicktipp_pending": kicktipp_pending[name],
            "max_possible": max_possible,
            "status": status,
            "verdict": verdict,
            "above_users": [
                {"user": u, "current": current[u], "points_possible": points_possible[u]}
                for u in above
            ],
        }

    return what_if


# ── Build race timeline ───────────────────────────────────────────────
def build_race_timeline(rankings: dict, user_names: list[str]) -> list[dict]:
    """Build data for the bar chart race animation."""
    timeline = []
    for stage_key in STAGE_KEYS:
        stage_data = rankings.get(stage_key, [])
        entry = {
            "stage": stage_key,
            "label": STAGE_LABELS.get(stage_key, stage_key),
            "users": [],
        }
        for r in stage_data:
            entry["users"].append({
                "user": r["user"], "points": r["points"], "rank": r["rank"],
            })
        timeline.append(entry)
    return timeline


# ── Main ──────────────────────────────────────────────────────────────
def main():
    print("Loading Kicktipp zip exports...", file=sys.stderr)
    data = load_all_zips()

    print("Fetching match results...", file=sys.stderr)
    results_data = fetch_results()
    results = results_data["matches"]
    top_scorers = results_data["top_scorers"]
    results_meta = results_data["stats"]

    print("Parsing predictions...", file=sys.stderr)
    predictions = parse_predictions(data)

    print("Computing prediction accuracy...", file=sys.stderr)
    accuracy = compute_accuracy(predictions, results)

    print("Parsing overview...", file=sys.stderr)
    user_names, points_per_stage, bonus_points = parse_overview(data["overview"] or [])

    print("Parsing bonus predictions...", file=sys.stderr)
    bonus_preds = parse_bonus(data["bonus"] or [])

    print("Computing rankings...", file=sys.stderr)
    rankings = compute_rankings(points_per_stage, user_names)

    print("Computing time on top...", file=sys.stderr)
    time_on_top = compute_time_on_top(rankings, user_names)

    print("Computing what-if scenarios...", file=sys.stderr)
    what_if = compute_what_if(
        points_per_stage, user_names, predictions, results,
        results_meta, bonus_preds, top_scorers,
    )

    print("Building race timeline...", file=sys.stderr)
    timeline = build_race_timeline(rankings, user_names)

    output = {
        "users": user_names,
        "stages": STAGE_KEYS,
        "stage_labels": STAGE_LABELS,
        "points_per_stage": points_per_stage,
        "rankings": rankings,
        "time_on_top": time_on_top,
        "accuracy": accuracy,
        "bonus_points": bonus_points,
        "bonus_preds": bonus_preds,
        "what_if": what_if,
        "timeline": timeline,
        "top_scorers": top_scorers,
        "results_meta": results_meta,
        "export_date": datetime.now().isoformat(),
    }

    js_path = SITE_DATA / "data.js"
    with open(js_path, "w") as f:
        f.write("window.KICKTIPP = ")
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write(";\n")

    print(f"\nWrote {js_path}", file=sys.stderr)
    print(f"Users: {len(user_names)}", file=sys.stderr)
    print(f"Stages: {len(STAGE_KEYS)}", file=sys.stderr)
    print(f"Results: {len(results)} matches", file=sys.stderr)

    print("\n=== TOP SCORERS ===", file=sys.stderr)
    for ts in top_scorers[:5]:
        flag = ts.get("flag", "")
        country = ts.get("country_name", "")
        print(f"  {flag} {ts['name']} ({country}): {ts['goals']} goals", file=sys.stderr)

    print("\n=== TIME ON 1ST PLACE ===", file=sys.stderr)
    sorted_tot = sorted(time_on_top.items(), key=lambda x: -x[1])
    for name, val in sorted_tot:
        print(f"  {name}: {val:.1f} stages", file=sys.stderr)

    print("\n=== WHAT IF ===", file=sys.stderr)
    for name in user_names[:5]:
        wi = what_if[name]
        print(f"  {name}: {wi['current']} pts, +{wi['points_possible']} possible, max {wi['max_possible']}, {wi['status']}", file=sys.stderr)


if __name__ == "__main__":
    main()
