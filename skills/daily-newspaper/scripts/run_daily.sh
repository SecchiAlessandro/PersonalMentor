#!/usr/bin/env bash
# PersonalMentor — Daily Newspaper Pipeline
# Run this script at 8 PM daily via cron or manually.
#
# Usage: bash scripts/run_daily.sh
# Cron:  0 20 * * * cd /path/to/PersonalMentor && bash skills/daily-newspaper/scripts/run_daily.sh

set -euo pipefail

# Resolve project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TODAY=$(date +%Y-%m-%d)
CONTENT_DIR="/tmp/pm_daily_${TODAY}"
OUTPUT_FILE="${PROJECT_ROOT}/output/daily/${TODAY}.html"

echo "=== PersonalMentor Daily Newspaper ==="
echo "Date: ${TODAY}"
echo "Project: ${PROJECT_ROOT}"
echo ""

# Step 1: Create working directory
mkdir -p "${CONTENT_DIR}"
mkdir -p "${PROJECT_ROOT}/output/daily"

# Step 2: Fetch RSS feeds
echo "[1/4] Fetching RSS feeds..."
python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_rss.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --output "${CONTENT_DIR}/rss.json" \
  || echo "WARNING: RSS fetch failed, continuing with empty data"

# Step 3: Fetch job listings
echo "[2/4] Fetching job listings..."
python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_jobs.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --interests "${PROJECT_ROOT}/profile/interests.yaml" \
  --output "${CONTENT_DIR}/jobs.json" \
  || echo "WARNING: Jobs fetch failed, continuing with empty data"

# Step 4: Fetch events
echo "[3/4] Fetching events..."
python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_events.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --output "${CONTENT_DIR}/events.json" \
  || echo "WARNING: Events fetch failed, continuing with empty data"

# Step 5: Render HTML
echo "[4/4] Rendering newspaper..."
python3 "${PROJECT_ROOT}/skills/daily-newspaper/scripts/render_newspaper.py" \
  --profile-dir "${PROJECT_ROOT}/profile/" \
  --content-dir "${CONTENT_DIR}" \
  --output "${OUTPUT_FILE}"

# Step 6: Register artifact
echo ""
echo "Registering artifact..."
python3 "${PROJECT_ROOT}/skills/memory-manager/scripts/register_artifact.py" \
  --type daily-newspaper \
  --path "output/daily/${TODAY}.html" \
  --sections "top-stories,jobs,calendar,birthdays,events,skills,pulse,reading" \
  --item-count 0 \
  --sources "rss,jobs,events"

python3 "${PROJECT_ROOT}/skills/memory-manager/scripts/log_action.py" \
  --action artifact_generated \
  --detail "Daily newspaper for ${TODAY}"

# Cleanup
rm -rf "${CONTENT_DIR}"

echo ""
echo "=== Done ==="
echo "Output: ${OUTPUT_FILE}"
