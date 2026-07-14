#!/usr/bin/env bash
# update.sh — Build data, swap to gh-pages, commit & push in one command.
#
# Usage:
#   ./scripts/update.sh              # build + deploy
#   ./scripts/update.sh --no-push    # build + stage, but don't push
#
# Prerequisites:
#   - You are on the `master` branch
#   - A remote named `origin` is configured
#   - Fresh *.csv.zip files are in the repo root (if predictions changed)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

NO_PUSH=false
if [[ "${1:-}" == "--no-push" ]]; then
    NO_PUSH=true
fi

echo "=== Step 1: Build data.js ==="
python3 scripts/build_data.py

echo ""
echo "=== Step 2: Switch to gh-pages ==="
CURRENT_BRANCH="$(git branch --show-current)"
git stash --include-untracked 2>/dev/null || true
git checkout gh-pages 2>/dev/null

echo ""
echo "=== Step 3: Copy site files to root ==="
# Remove old deploy files
rm -rf css/ js/ data/ index.html
# Copy fresh files from master's site/
git checkout "$CURRENT_BRANCH" -- site/
mv site/* .
rm -rf site/
# Unstage the site/ directory (it was staged by checkout)
git reset HEAD site/ 2>/dev/null || true

echo ""
echo "=== Step 4: Commit & push ==="
git add css/ js/ data/ index.html
if git diff --cached --quiet; then
    echo "No changes to deploy."
else
    git commit -m "deploy: $(date -u '+%Y-%m-%d %H:%M UTC')"
    if [[ "$NO_PUSH" == false ]]; then
        git push origin gh-pages
        echo "Pushed to gh-pages."
    else
        echo "Changes committed but NOT pushed (use --no-push to skip)."
    fi
fi

echo ""
echo "=== Step 5: Return to $CURRENT_BRANCH ==="
git checkout "$CURRENT_BRANCH"
git stash pop 2>/dev/null || true

echo ""
echo "Done. Dashboard updated."
