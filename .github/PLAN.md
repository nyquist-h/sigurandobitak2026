# Kicktipp WC 2026 Dashboard — Plan

## Overview
Static GitHub Pages site visualizing Kicktipp.de World Cup 2026 prediction league data.
Data comes from zip‑exported CSVs + scraped actual match results from Wikipedia.

## Locked Decisions
| # | Decision |
|---|---|
| A | Scrape results from Wikipedia ("2026 FIFA World Cup") |
| B | Bonus = WC winner + top scorer only, 10 pts each |
| C | Ties for 1st split credit (0.5, 0.33, etc.) |
| D | "What is needed" compares to **every user above** the focal user |
| E | Site lives in `/home/nyquist/kicktipp/site/`, deployed to `gh-pages` branch |

## Data Sources
- **17 zip files** in repo root, each containing one `;`‑delimited CSV:
  - General overview (rankings, points per stage, total)
  - Matchday 1 leaderboard (with emails — **stripped**)
  - Predictions: Matchday 1–10, Sixteenth final, Round of 16, Quarter‑final, Semi‑finals
  - Bonus predictions (WC winner, top scorer, group winners, semi‑finalists)
- **Wikipedia**: "2026 FIFA World Cup" for actual match results

## Scoring Rules (Kicktipp standard + draw bonus)
| Scenario | Points |
|---|---|
| Exact score (incl. exact draw) | 4 |
| Correct winner + correct goal difference (non‑draw) | 3 |
| Draw predicted, no exact result | 3 |
| Correct winner only | 2 |
| Missed / wrong | 0 |
| Bonus: WC winner correct | 10 |
| Bonus: Top scorer correct | 10 |

## Project Structure
```
kicktipp/
├── .github/PLAN.md
├── *.csv.zip                    ← raw Kicktipp exports
├── scripts/
│   ├── scrape_results.py        ← fetches WC 2026 results from Wikipedia
│   └── build_data.py            ← zips + scraped results → site/data/data.js
├── site/
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── overview.js
│   │   ├── per_user.js
│   │   ├── what_if.js
│   │   ├── race.js
│   │   └── bonus.js
│   ├── data/
│   │   └── data.js              ← compiled JSON (window.KICKTIPP)
│   └── assets/
└── README.md
```

## Implementation Steps

### 1. Extract & Parse CSVs
- Loop `*.zip` → extract single CSV → parse with `;` delimiter, strip `"…"`
- Build typed structures: users, predictions, points, bonus
- Emails **dropped**, never written to `data.js`

### 2. Scrape Actual Results (`scrape_results.py`)
- Source: Wikipedia "2026 FIFA World Cup" — group stage tables + knockout bracket
- Alias map: team‑code ↔ Wikipedia name (BIH ↔ Bosnia and Herzegovina, etc.)
- Output: `results.json` mapping `(stage_key, match_key) → {home, away, hg, ag, played}`
- Unmatched matches logged + skipped

### 3. Compute Derived Stats (`build_data.py`)
Per `(user, match)`:
- `exact_score` → 4 pts | `correct_winner_plus_diff` → 3 pts | `draw_pred_no_exact` → 3 pts | `correct_winner` → 2 pts | miss → 0

Aggregates:
- **Stage rankings** (cumulative) per stage
- **Time on 1st place** with tie‑splitting
- **Per‑user quality counts**: exact, exact_draw, winner_only, winner_plus_diff, draw_pred_no_exact, missed
- **Bonus hits**: WC winner ✓ + 10, top scorer ✓ + 10
- **Race timeline**: cumulative points per user × 15 stages (MD1–10 + R32 + R16 + QF + SF + Final)
- **"What is needed"**: current, max_possible, gap to each rival above, status (eliminated / must_perfect / safe)

### 4. Static Site (`site/`)
- Vanilla HTML + ES modules, no bundler
- ECharts via CDN (dark theme, native animations, timeline for race)
- Inter font, dark slate `#0b0f17`, accent gradient `#7c3aed → #06b6d4`
- Responsive, mobile‑friendly

**Sections**:
1. Hero — tournament name, "data as of" timestamp
2. Standings — sortable table with sparkline
3. Time on 1st Place — horizontal bar chart, tie‑split toggle
4. Prediction Quality — 15 user cards with donut + 4‑pointer list
5. What is needed to win — per‑user card with status badge + plain‑English verdict
6. Points‑over‑Time Race — bar chart race with ▶/⏸ + timeline slider
7. Bonus — grid of WC pick + top scorer pick, ✓/✗ overlay

### 5. Deployment
- `gh-pages` branch containing only `site/` contents
- GitHub Pages auto‑serves from that branch

## Out of Scope
- Editing predictions back into Kicktipp
- Notifications / live updates
- Multi‑tournament support
- Mobile native app
