# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> This file also serves as the agent's working memory, loaded at the start of every session.

## User Identity

- **Name:** Alessandro Secchi
- **Title:** Control Software Engineer at Hitachi Energy
- **Location:** Baden, Switzerland
- **Key facts:** ETH Zurich MAS in Management & Economics (2024-2026), MSc EE from Politecnico di Milano (summa cum laude), co-founded EMS, Hitachi Sustainability Inspiration of the Year 2025, builds AI tools for energy (EnergyForecaster, LumadaAI)
- **Active goal:** Searching for AI/ML + Energy hybrid roles (Switzerland / Remote)

## Preferences

- **Theme:** golden-hour (actual running theme, defined in `profile/preferences.yaml`)
- **Tone:** casual
- **Language:** en
- **Delivery time:** 07:00

## Commands

### Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Run the full daily pipeline
```bash
bash skills/daily-newspaper/scripts/run_daily.sh
```
This runs all steps: fetch content, generate German sentence, analyze feedback, render HTML, start feedback server, register artifact, git push. Output goes to `output/daily/YYYY-MM-DD.html`.

### Run individual pipeline steps
```bash
# RSS feeds
python3 skills/web-scraper/scripts/fetch_rss.py --config profile/sources.yaml --output /tmp/rss.json

# Job boards (scored against profile)
python3 skills/web-scraper/scripts/fetch_jobs.py --config profile/sources.yaml --interests profile/interests.yaml --output /tmp/jobs.json

# Events
python3 skills/web-scraper/scripts/fetch_events.py --config profile/sources.yaml --output /tmp/events.json

# German sentence (requires GEMINI_API_KEY in .env)
python3 skills/daily-newspaper/scripts/generate_german.py --output /tmp/german.json --date "2026-02-18"

# Google Calendar (requires gog CLI + OAuth)
gog calendar events primary --from 2026-02-18T00:00:00Z --to 2026-02-19T23:59:59Z --json

# Render HTML from collected content
python3 skills/daily-newspaper/scripts/render_newspaper.py --profile-dir profile/ --content-dir /tmp/pm_daily_2026-02-18 --output output/daily/2026-02-18.html

# Feedback analysis
python3 skills/daily-newspaper/scripts/analyze_feedback.py
```

### Scheduling (macOS launchd)
```bash
launchctl load ~/Library/LaunchAgents/com.personalmentor.daily.plist    # Enable
launchctl unload ~/Library/LaunchAgents/com.personalmentor.daily.plist  # Disable
launchctl start com.personalmentor.daily                                # Manual trigger
```
Plist at `~/Library/LaunchAgents/com.personalmentor.daily.plist`. Runs daily at 07:00. Logs to `memory/daily-run.log`.

## Architecture

PersonalMentor is an autonomous agent that generates a daily HTML newspaper tailored to the user's profile. It runs unattended via macOS launchd, fetches content from RSS/job boards/calendar, and publishes to GitHub Pages.

### Daily Pipeline (run_daily.sh)

```
launchd trigger (07:00)
    │
    ├─ [PARALLEL] fetch_rss.py + fetch_jobs.py + fetch_events.py
    │  (10 RSS feeds, 8 job boards, 2 event sources → JSON files in /tmp/pm_daily_DATE/)
    │
    ├─ [SEQUENTIAL] gog calendar → parse_gog.py → calendar.json
    ├─ generate_german.py (Gemini API) → german.json
    ├─ analyze_feedback.py → updates memory/learned-preferences.yaml
    │
    ├─ render_newspaper.py
    │  (merges all JSON + profile + theme → single self-contained HTML)
    │
    ├─ feedback_server.py on localhost:9847 (auto-shutdown after 2h)
    ├─ register_artifact.py → memory/artifacts.yaml
    └─ git add + commit + push → GitHub Pages
```

### Key Design Decisions

- **Single-file HTML output**: All CSS inlined, no external dependencies. Files can be 1+ MB when Gemini illustrations are embedded.
- **Job scoring algorithm** (`fetch_jobs.py`): role match +0.3, location match +0.2, company match +0.2, base +0.3. Target roles/companies/locations come from `profile/interests.yaml`.
- **Adaptive content**: `analyze_feedback.py` reads `memory/feedback.jsonl` and adjusts per-section item counts (range 2-7) based on user ratings. Stored in `memory/learned-preferences.yaml`.
- **Gemini model fallback chain**: gemini-2.5-flash → gemini-2.0-flash → gemini-2.5-flash-lite (for German sentence generation).
- **10 color themes** in `skills/theme-factory/themes/`. Current theme: golden-hour. Applied via CSS variables at render time.

### Four Core Skills

| Skill | Entry Point | Purpose |
|---|---|---|
| `daily-newspaper` | `skills/daily-newspaper/scripts/run_daily.sh` | Pipeline orchestrator + HTML renderer + German generator + feedback system |
| `web-scraper` | `skills/web-scraper/scripts/fetch_*.py` | RSS, job board, and event content fetching |
| `profile-manager` | `skills/profile-manager/scripts/` | CV parsing (PDF/DOCX), website scraping, onboarding interview |
| `memory-manager` | `skills/memory-manager/scripts/` | Append-only logging, artifact registry, preference learning |

### Data Flow

- **Profile** (`profile/*.yaml`): User identity, interests, preferences, content sources. Read by pipeline scripts.
- **Memory** (`memory/`): `artifacts.yaml` (artifact registry), `learned-preferences.yaml` (adaptive section weights), `feedback.jsonl` (raw user ratings), `session-log.jsonl` (action log).
- **Output** (`output/daily/`): Generated HTML newspapers, committed and pushed to GitHub for hosting at `alessandrosecchi.com/PersonalMentor/`.

### External Dependencies

- **GEMINI_API_KEY** (in `.env`): Required for German sentence generation via `google-genai` SDK.
- **gog CLI** (`brew install steipete/tap/gogcli`): Optional. Fetches Google Calendar events. Pipeline continues without it.
- **GitHub Pages**: `index.html` at repo root redirects to today's newspaper.

### Feedback Server

`feedback_server.py` serves dual purpose:
- **First run** (no `profile/identity.yaml`): Launches onboarding wizard at `localhost:9847` with CV upload, website scrape, and preference form.
- **Normal run**: Serves feedback form embedded in each newspaper. Ratings saved to `memory/feedback.jsonl`. PID file at `/tmp/pm_feedback_server.pid`.

## Session Notes

_This section is updated automatically after each session._
