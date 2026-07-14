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
    # Use csv.DictReader with semicolon delimiter
    reader = csv.DictReader(io.StringIO(data), delimiter=";", quotechar='"')
    rows = []
    for row in reader:
        # Strip whitespace from keys and values
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
        "predictions": {},  # stage_key -> rows
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

        result = build_results(matches, players)
        # Save cache
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
                    # This is a match column
                    val = val.strip()
                    # Normalize team codes in match key
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
    """Compute per-user prediction accuracy stats.
    Returns: {user_name: {
        "exact": int, "exact_draw": int, "winner_plus_diff": int,
        "draw_pred_no_exact": int, "correct_winner": int, "missed": int,
        "total_predicted": int, "total_played": int,
        "four_pointers": [{"match": "...", "predicted": "...", "actual": "..."}],
    }}
    """
    stats = {}

    for stage_key, stage_preds in predictions.items():
        for user_name, user_preds in stage_preds.items():
            if user_name not in stats:
                stats[user_name] = {
                    "exact": 0,
                    "exact_draw": 0,
                    "winner_plus_diff": 0,
                    "draw_pred_no_exact": 0,
                    "correct_winner": 0,
                    "missed": 0,
                    "total_predicted": 0,
                    "total_played": 0,
                    "four_pointers": [],
                }

            for match_key, pred in user_preds.items():
                # Skip empty, "-:-", "0:999" predictions
                if not pred or pred in ("-:-", "0:999"):
                    continue

                stats[user_name]["total_predicted"] += 1

                if match_key not in results:
                    continue  # match not played yet

                result = results[match_key]
                hg, ag = result["hg"], result["ag"]
                stats[user_name]["total_played"] += 1

                # Parse prediction
                pred_match = re.match(r"(\d+):(\d+)", pred)
                if not pred_match:
                    stats[user_name]["missed"] += 1
                    continue

                ph, pa = int(pred_match.group(1)), int(pred_match.group(2))
                pred_diff = ph - pa
                real_diff = hg - ag

                # Exact score
                if ph == hg and pa == ag:
                    stats[user_name]["exact"] += 1
                    if hg == ag:
                        stats[user_name]["exact_draw"] += 1
                    stats[user_name]["four_pointers"].append({
                        "match": match_key,
                        "predicted": pred,
                        "actual": f"{hg}:{ag}",
                        "stage": stage_key,
                    })
                # Draw predicted, no exact
                elif hg == ag and ph == pa:
                    stats[user_name]["draw_pred_no_exact"] += 1
                # Correct winner + goal difference (non-draw)
                elif hg != ag and ph != pa:
                    if (pred_diff > 0 and real_diff > 0) or (pred_diff < 0 and real_diff < 0):
                        if abs(pred_diff) == abs(real_diff):
                            stats[user_name]["winner_plus_diff"] += 1
                        else:
                            stats[user_name]["correct_winner"] += 1
                    else:
                        stats[user_name]["missed"] += 1
                # Correct winner only
                elif (pred_diff > 0 and real_diff > 0) or (pred_diff < 0 and real_diff < 0):
                    stats[user_name]["correct_winner"] += 1
                else:
                    stats[user_name]["missed"] += 1

    return stats


# ── Parse overview data ───────────────────────────────────────────────
def parse_overview(rows: list[dict]) -> tuple[list[str], dict, dict]:
    """Parse general overview CSV.
    Returns: (user_names, points_per_stage, bonus_points)
    """
    user_names = []
    points_per_stage = {}  # {user: {stage: int}}
    bonus_points = {}  # {user: int}

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
    """Compute cumulative rankings per stage.
    Returns: {stage_key: [{user, rank, points, cumulative}]}
    """
    rankings = {}
    cumulative = {name: 0 for name in user_names}

    for stage_key in STAGE_KEYS:
        # Update cumulative points
        for name in user_names:
            cumulative[name] += points_per_stage.get(name, {}).get(stage_key, 0)

        # Sort by cumulative points (descending), then by name (ascending) for ties
        sorted_users = sorted(user_names, key=lambda n: (-cumulative[n], n))

        # Assign ranks (handle ties)
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
                "user": name,
                "rank": rank,
                "points": pts,
                "stage_points": points_per_stage.get(name, {}).get(stage_key, 0),
            })

        rankings[stage_key] = stage_rankings

    return rankings


# ── Compute time on 1st place ─────────────────────────────────────────
def compute_time_on_top(rankings: dict, user_names: list[str]) -> dict:
    """Compute how many stages each user was in 1st place (with tie-splitting)."""
    time_on_top = {name: 0.0 for name in user_names}

    for stage_key, stage_rankings in rankings.items():
        # Find all users with rank 1
        first_place = [r for r in stage_rankings if r["rank"] == 1]
        if first_place:
            split = 1.0 / len(first_place)
            for r in first_place:
                time_on_top[r["user"]] += split

    return time_on_top


# ── Compute "what is needed to win" ───────────────────────────────────
def compute_what_if(points_per_stage: dict, user_names: list[str], predictions: dict) -> dict:
    """For each user, compute what's needed to win.
    Compares against every user above them.
    """
    # Current total points per user
    current = {}
    for name in user_names:
        current[name] = sum(points_per_stage.get(name, {}).get(s, 0) for s in STAGE_KEYS)

    # Remaining matches per user (stages with predictions but no points yet)
    remaining = {}
    for name in user_names:
        count = 0
        for stage_key in STAGE_KEYS:
            pts = points_per_stage.get(name, {}).get(stage_key, 0)
            if pts == 0:
                # Check if user has predictions for this stage
                stage_preds = predictions.get(stage_key, {})
                user_preds = stage_preds.get(name, {})
                # Count non-empty predictions
                for mk, pv in user_preds.items():
                    if pv and pv not in ("-:-", "0:999"):
                        count += 1
        remaining[name] = count

    # Sort users by current points (descending)
    sorted_users = sorted(user_names, key=lambda n: (-current[n], n))

    what_if = {}
    for name in user_names:
        above = [u for u in sorted_users if current[u] > current[name]]
        max_possible = current[name] + 4 * remaining[name]

        if not above:
            # Already leading
            status = "leading"
            verdict = f"{name} is currently in the lead with {current[name]} points."
        elif max_possible <= min(current[u] for u in above):
            status = "eliminated"
            verdict = f"{name} is mathematically eliminated. Max possible ({max_possible}) is less than the leader's current ({max(current[u] for u in above)})."
        else:
            status = "possible"
            # Find the gap to each user above
            gaps = []
            for u in above:
                gap = current[u] - current[name]
                gaps.append(f"{u}: {gap} pts behind")
            verdict = f"{name} needs {', '.join(gaps)}. Must score 4 pts in every remaining match ({remaining[name]} matches, max {4 * remaining[name]} pts) AND all users above must score 0."

        what_if[name] = {
            "current": current[name],
            "remaining_matches": remaining[name],
            "max_possible": max_possible,
            "status": status,
            "verdict": verdict,
            "above_users": [{"user": u, "current": current[u], "remaining": remaining[u]} for u in above],
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
                "user": r["user"],
                "points": r["points"],
                "rank": r["rank"],
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
    what_if = compute_what_if(points_per_stage, user_names, predictions)

    print("Building race timeline...", file=sys.stderr)
    timeline = build_race_timeline(rankings, user_names)

    # ── Assemble output ───────────────────────────────────────────────
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
        "results_meta": results_data["stats"],
        "export_date": datetime.now().isoformat(),
    }

    # Write data.js
    js_path = SITE_DATA / "data.js"
    with open(js_path, "w") as f:
        f.write("window.KICKTIPP = ")
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write(";\n")

    print(f"\nWrote {js_path}", file=sys.stderr)
    print(f"Users: {len(user_names)}", file=sys.stderr)
    print(f"Stages: {len(STAGE_KEYS)}", file=sys.stderr)
    print(f"Results: {len(results)} matches", file=sys.stderr)

    # Print summary
    print("\n=== TOP SCORERS ===", file=sys.stderr)
    for ts in top_scorers[:5]:
        print(f"  {ts['name']}: {ts['goals']} goals", file=sys.stderr)

    print("\n=== TIME ON 1ST PLACE ===", file=sys.stderr)
    sorted_tot = sorted(time_on_top.items(), key=lambda x: -x[1])
    for name, val in sorted_tot:
        print(f"  {name}: {val:.1f} stages", file=sys.stderr)

    print("\n=== WHAT IF ===", file=sys.stderr)
    for name in user_names[:5]:
        wi = what_if[name]
        print(f"  {name}: {wi['current']} pts, max {wi['max_possible']}, {wi['status']}", file=sys.stderr)


if __name__ == "__main__":
    main()
