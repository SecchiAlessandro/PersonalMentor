#!/usr/bin/env bash
# PersonalMentor — Daily Newspaper Pipeline
# Run this script daily at 07:00 via launchd or manually.
#
# Usage: bash skills/daily-newspaper/scripts/run_daily.sh
# Launchd: see ~/Library/LaunchAgents/com.personalmentor.daily.plist

set -euo pipefail

# Resolve project root (relative to this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Activate virtual environment if available
if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
  source "${PROJECT_ROOT}/.venv/bin/activate"
fi

# Load environment variables from .env (for manual runs)
if [ -f "${PROJECT_ROOT}/.env" ]; then
  set -a
  source "${PROJECT_ROOT}/.env"
  set +a
fi

# Profile detection gate: if no identity or no name, launch onboarding
if ! python3 -c "
import yaml
d = yaml.safe_load(open('${PROJECT_ROOT}/profile/identity.yaml'))
assert d and d.get('name', '')
" 2>/dev/null; then
  echo "No profile found. Starting onboarding wizard..."
  echo ""

  # Start feedback server (serves welcome page at /)
  if ! curl -s http://localhost:9847/health >/dev/null 2>&1; then
    python3 "${SCRIPT_DIR}/feedback_server.py" &
    sleep 1
  fi

  # Open browser to welcome page
  WELCOME_URL="http://localhost:9847/"
  if command -v open &>/dev/null; then
    open "$WELCOME_URL"
  elif command -v xdg-open &>/dev/null; then
    xdg-open "$WELCOME_URL"
  else
    echo "Open in your browser: $WELCOME_URL"
  fi

  echo "Complete the onboarding wizard at: $WELCOME_URL"
  echo "Then re-run this script to generate your first newspaper."
  exit 0
fi

TODAY=$(date +%Y-%m-%d)
TOMORROW=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d 2>/dev/null || echo "")
CONTENT_DIR="/tmp/pm_daily_${TODAY}"
OUTPUT_FILE="${PROJECT_ROOT}/output/daily/${TODAY}.html"

echo "=== PersonalMentor Daily Newspaper ==="
echo "Date: ${TODAY}"
echo "Project: ${PROJECT_ROOT}"
echo ""

# Step 1: Create working directory
mkdir -p "${CONTENT_DIR}"
mkdir -p "${PROJECT_ROOT}/output/daily"

# Steps 2-4: Fetch RSS, jobs, and events in parallel
echo "[1-3/7] Fetching RSS feeds, job listings, and events in parallel..."

(python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_rss.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --output "${CONTENT_DIR}/rss.json" \
  || echo "WARNING: RSS fetch failed, continuing with empty data") &
PID_RSS=$!

(python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_jobs.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --interests "${PROJECT_ROOT}/profile/interests.yaml" \
  --output "${CONTENT_DIR}/jobs.json" \
  || echo "WARNING: Jobs fetch failed, continuing with empty data") &
PID_JOBS=$!

(python3 "${PROJECT_ROOT}/skills/web-scraper/scripts/fetch_events.py" \
  --config "${PROJECT_ROOT}/profile/sources.yaml" \
  --output "${CONTENT_DIR}/events.json" \
  || echo "WARNING: Events fetch failed, continuing with empty data") &
PID_EVENTS=$!

# Wait for all three fetchers to complete
wait $PID_RSS  || true
wait $PID_JOBS || true
wait $PID_EVENTS || true
echo "  All fetchers complete."

# Step 5: Fetch Google Calendar (optional)
CALENDAR_ARGS=""
echo "[4/7] Fetching calendar (gog)..."
if command -v gog &>/dev/null; then
  # Fetch calendar events for today only
  WEEK_END="${TOMORROW}"
  if gog calendar events primary --from "${TODAY}T00:00:00Z" --to "${WEEK_END}T23:59:59Z" --json > "${CONTENT_DIR}/gog_calendar.json" 2>/dev/null; then
    GOG_SIZE=$(wc -c < "${CONTENT_DIR}/gog_calendar.json" | tr -d ' ')
    echo "  Calendar fetched (${GOG_SIZE} bytes)."
    # Debug: show first 500 chars of raw gog output
    echo "  DEBUG gog raw (first 500 chars):"
    head -c 500 "${CONTENT_DIR}/gog_calendar.json" | sed 's/^/    /'
    echo ""
  else
    echo "  WARNING: gog calendar fetch failed (OAuth not configured?)"
    rm -f "${CONTENT_DIR}/gog_calendar.json"
  fi

  # Parse gog output into render-friendly format
  if [ -f "${CONTENT_DIR}/gog_calendar.json" ]; then
    python3 "${SCRIPT_DIR}/parse_gog.py" \
      --calendar-in "${CONTENT_DIR}/gog_calendar.json" \
      --calendar-out "${CONTENT_DIR}/calendar.json" \
      || echo "  WARNING: gog parse failed"
  fi

  # Set render args if parsed files exist
  if [ -f "${CONTENT_DIR}/calendar.json" ]; then
    CALENDAR_ARGS="--calendar-json ${CONTENT_DIR}/calendar.json"
  fi
else
  echo "  gog not installed — skipping. Install: brew install steipete/tap/gogcli"
fi

# Step 6: Generate German Sentence of the Day
GERMAN_ARGS=""
echo "[5/7] Generating German Sentence of the Day..."
if python3 "${SCRIPT_DIR}/generate_german.py" \
  --output "${CONTENT_DIR}/german.json" \
  --date "${TODAY}" 2>&1; then
  GERMAN_ARGS="--german-json ${CONTENT_DIR}/german.json"
else
  echo "  WARNING: German sentence generation failed (GEMINI_API_KEY set?)"
fi

# Step 7: Analyze feedback (updates learned-preferences.yaml)
echo "[6/9] Analyzing feedback..."
if [ -f "${PROJECT_ROOT}/memory/feedback.jsonl" ]; then
  python3 "${SCRIPT_DIR}/analyze_feedback.py" \
    || echo "  WARNING: Feedback analysis failed, using defaults"
else
  echo "  No feedback yet — skipping."
fi

# Step 8: Render HTML
echo "[7/9] Rendering newspaper..."
python3 "${PROJECT_ROOT}/skills/daily-newspaper/scripts/render_newspaper.py" \
  --profile-dir "${PROJECT_ROOT}/profile/" \
  --content-dir "${CONTENT_DIR}" \
  --output "${OUTPUT_FILE}" \
  ${CALENDAR_ARGS} ${GERMAN_ARGS}

# Step 9: Start feedback server (if not already running)
echo "[8/9] Starting feedback server..."
if curl -s http://localhost:9847/health >/dev/null 2>&1; then
  echo "  Feedback server already running."
else
  python3 "${SCRIPT_DIR}/feedback_server.py" &
  echo "  Feedback server started (PID $!)."
fi

# Step 10: Register artifact
echo "[9/9] Registering artifact..."
python3 "${PROJECT_ROOT}/skills/memory-manager/scripts/register_artifact.py" \
  --type daily-newspaper \
  --path "output/daily/${TODAY}.html" \
  --sections "news,jobs,events,calendar-events,german-sentence" \
  --item-count 0 \
  --sources "rss,jobs,events,calendar,gemini"

python3 "${PROJECT_ROOT}/skills/memory-manager/scripts/log_action.py" \
  --action artifact_generated \
  --detail "Daily newspaper for ${TODAY}"

# Keep temp dir for debugging (preserve last run, clean older ones)
find /tmp -maxdepth 1 -name "pm_daily_*" ! -name "pm_daily_${TODAY}" -type d -mtime +3 -exec rm -rf {} + 2>/dev/null || true
echo "DEBUG: Content dir preserved at ${CONTENT_DIR}"

echo ""
echo "=== Done ==="
echo "Output: ${OUTPUT_FILE}"
