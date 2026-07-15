# Kicktipp WC 2026 Dashboard — Project Instructions

## Overview
Static GitHub Pages site visualizing a Kicktipp.de World Cup 2026 prediction league ("Siguran Dobitak 2026"). Data comes from zip-exported CSVs (Kicktipp) + scraped actual match results (GitHub dataset). The site is **vanilla HTML/CSS/JS**, no framework, no bundler. ECharts is loaded via CDN for charts.

## Project Structure
```
kicktipp/
├── .github/
│   ├── INSTRUCTIONS.md          ← This file
│   └── PLAN.md                  ← Original plan (reference)
├── *.csv.zip                    ← Raw Kicktipp exports (17 files)
├── data/
│   └── results_cache.json       ← Cached match results + manual injections
├── scripts/
│   ├── build_data.py            ← Pipeline: CSVs + results → site/data/data.js
│   ├── scrape_results.py        ← Fetches WC 2026 results from GitHub dataset
│   └── update.sh                ← Build + deploy to gh-pages in one command
├── site/
│   ├── index.html               ← Single-page dashboard
│   ├── css/style.css            ← Tokyo Night theme
│   ├── js/app.js                ← All rendering logic (single file)
│   └── data/
│       └── data.js              ← Generated: window.KICKTIPP = {...}
└── README.md
```

## Theme: Tokyo Night
| Variable | Value | Usage |
|---|---|---|
| `--bg` | `#1a1b26` | Page background |
| `--bg-card` | `#24283b` | Card backgrounds |
| `--border` | `#414868` | Borders, dividers |
| `--text` | `#c0caf5` | Primary text |
| `--text-muted` | `#9aa5ce` | Secondary text |
| `--accent` | `#7aa2f7` | Primary accent (blue) |
| `--success` | `#9ece6a` | Green (exact predictions) |
| `--warning` | `#e0af68` | Orange (partial predictions) |
| `--danger` | `#f7768e` | Red (missed predictions, highlights) |

**No purple/lila.** Font: Inter (Google Fonts).

## Scoring Rules
| Scenario | Points |
|---|---|
| Exact score (incl. exact draw) | 4 |
| Correct winner + correct goal difference | 3 |
| Draw predicted, not exact result | 3 |
| Correct winner only | 2 |
| Missed / wrong | 0 |
| Bonus: WC winner correct | 10 |
| Bonus: Top scorer correct | 10 |

## Data Pipeline

### `scripts/build_data.py`
Reads `*.csv.zip` files + `results_cache.json`, computes all derived stats, writes `site/data/data.js`.

**Output structure (`window.KICKTIPP`):**

| Key | Type | Description |
|---|---|---|
| `users` | `string[]` | Ordered list of 15 player names |
| `stages` | `string[]` | `["md1"..."md10", "r32", "r16", "qf", "sf", "final"]` |
| `stage_labels` | `object` | Stage key → display name map |
| `points_per_stage` | `{user: {stage: pts}}` | Points each user earned per stage |
| `rankings` | `{stage: [{user, rank, points, stage_points}]}` | Cumulative rankings per stage |
| `time_on_top` | `{user: float}` | Stages spent in 1st place (tie-split) |
| `accuracy` | `{user: {exact, exact_draw, winner_plus_diff, draw_pred_no_exact, correct_winner, missed, total_predicted, total_played, four_pointers: [...]}}` | Per-user prediction accuracy |
| `scoring_distribution` | `{user: {exact, winner_plus_diff, draw_pred_no_exact, correct_winner, missed, total_predicted, total_played}}` | Same as accuracy, flattened for charts |
| `bonus_points` | `{user: int}` | Bonus points already earned |
| `bonus_preds` | `{user: {wc_winner: string, top_scorer: string}}` | Each user's bonus picks |
| `what_if` | `{user: {current, points_possible, max_possible, status, verdict, above_users: [...]}}` | "What's needed to win" analysis |
| `timeline` | `[{stage, label, users: [{user, points, rank}]}]` | Points progression for race animation |
| `top_scorers` | `[{name, country_name, country_code, flag, goals}]` | Top scorers from dataset |
| `results_meta` | `{total_matches, completed, scheduled, wc_winner_determined, top_scorer_names}` | Tournament state |
| `export_date` | `string` | ISO timestamp of build |

### `points_possible` Logic
```
points_possible = 12 (base) + WC bonus + TS bonus
```
- **Base**: 3 remaining games × 4 pts = 12 (for all users)
- **WC bonus**: 10 if user's pick is ESP, ENG, or ARG (teams still alive)
- **TS bonus**: 10 if user's pick's country is alive (ESP/ENG/ARG/FRA) OR player is tied for #1 in goals

### `what_if` Status Logic
- `"leading"`: User is #1
- `"eliminated"`: `current + points_possible < leader_current`
- `"possible"`: Can still mathematically catch the leader

### Manual Result Injection
`build_data.py` injects FRA 0:2 ESP into `results_cache.json` if not present (until GitHub dataset updates). This marks the semi-final as played and sets `wc_winner_determined = true`, `wc_winner = "ESP"`.

### `scripts/scrape_results.py`
Fetches `matches_detailed.csv` and `player_stats.csv` from the GitHub dataset. Parses into structured results. Falls back to `data/results_cache.json` on network failure.

### `scripts/update.sh`
Builds data, checks out `gh-pages`, copies site files to branch root, commits, pushes, returns to `master`.
```bash
./scripts/update.sh          # build + deploy
./scripts/update.sh --no-push  # build + stage only
```

## Site Sections (index.html)

### 1. Hero
- Tournament title, export date, match count
- **Animated counters**: Players, Matches Played, Matches Left, Leader Points
- **Top 5 scorers** with flag emojis

### 2. Standings (`#standings`)
- Sortable table: Rank, Player, Points, Exact, Winner, Missed, Played, No Prediction
- Wrapped in `.card-scroll` + `.table-wrapper` for horizontal scroll on narrow screens
- Rank badges: gold (#1), silver (#2), bronze (#3), gray (other)

### 3. Points Race (`#race`)
- Horizontal bar chart (ECharts) showing points per user at current stage
- **Play/Pause/Reset** buttons animate through stages
- **Player dropdown**: select a player to highlight their bar in red (`#f7768e`)
- Stage label updates as animation progresses

### 4. Prediction Quality (`#quality`)
- Grid of cards, one per user
- Each card contains:
  - **Donut chart** (ECharts pie): Exact (green) / Partial (blue) / Wrong (red)
  - **Legend** dots below donut
  - **Stats row**: Exact count, Winner count, Missed count
  - **4-Pointer list**: Matches where user got exact score
- Winner count = `correct_winner + winner_plus_diff + draw_pred_no_exact` (matches standings table)

### 5. What's Needed (`#what-if`)
- Grid of cards, one per user
- Status badge: Leading (green), Possible (blue), Eliminated (gray)
- Stats: Current, Points Possible, Max Possible
- Verdict: Plain English explanation
- "Users Above" list showing gap to each rival

## Deployment
- **`master` branch**: Source code + site/ directory
- **`gh-pages` branch**: Deployed site (index.html, css/, js/, data/ at root)
- GitHub Pages serves from `gh-pages`
- Remote: `git@github.com:nyquist-h/sigurandobitak2026.git`

## Current Tournament State
- **101/104 matches completed** (3 remaining: 1 SF, 1 Final, 1 3rd place)
- **WC winner**: ESP (determined via manual FRA 0:2 ESP injection)
- **Top scorers**: Mbappé (FRA) 8, Messi (ARG) 8, Haaland (NOR) 7, Kane (ENG) 6, Bellingham (ENG) 6
- **Leader**: Dzeko007 with 177 pts, max 199

## Common Tasks

### Rebuild data only
```bash
python3 scripts/build_data.py
```

### Rebuild + deploy
```bash
./scripts/update.sh
```

### Serve locally for testing
```bash
cd site && python3 -m http.server 8080
# Open http://localhost:8080
```

### Add a new manual result
Edit `scripts/build_data.py` in the manual injection block:
```python
if "HOME - AWAY" not in result["matches"]:
    result["matches"]["HOME - AWAY"] = {
        "home": "HOME", "away": "AWAY",
        "hg": 0, "ag": 0, "played": True,
        "stage": "Stage name", "date": "YYYY-MM-DD",
        "result_type": "Regular",
    }
```

### Update alive teams for points_possible
Edit `alive_teams` in `compute_what_if()` in `build_data.py`:
```python
alive_teams = {"ESP", "ENG", "ARG"}  # Update when teams are eliminated
```

## Key Implementation Notes
- **Single JS file**: All rendering in `site/js/app.js` (~440 lines)
- **ECharts** initialized on DOMContentLoaded, resized on window resize
- **Donut charts** stored in `qualityDonutCharts[]` array for resize handling
- **Race chart** stored in `raceChart`, stage index in `raceStageIndex`
- **Animated counters** use `requestAnimationFrame` with cubic ease-out
- **Table scroll**: `.card-scroll` removes padding, `.table-wrapper` adds padding + `overflow-x: auto`
- **Winner count formula** must match between standings and quality cards: `correct_winner + winner_plus_diff + draw_pred_no_exact`
