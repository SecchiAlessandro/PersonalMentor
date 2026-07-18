# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> This file also serves as the agent's working memory, loaded at the start of every session.

## User Identity

- **Name:** Alessandro Secchi
- **Title:** Project Manager Engineering & AI Specialist at Hitachi Energy (AI Point of Contact / SME for the AINexus transformation program)
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

**macOS / Linux:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run the full daily pipeline

**Cross-platform (recommended):**
```bash
python skills/daily-newspaper/scripts/run_daily.py
```

**macOS / Linux (legacy shell script, still works):**
```bash
bash skills/daily-newspaper/scripts/run_daily.sh
```

This runs all steps: fetch content, generate German sentence, analyze feedback, render HTML, start feedback server, register artifact, git push. Output goes to `output/daily/YYYY-MM-DD.html`.

### Run individual pipeline steps
```bash
# RSS feeds
python3 skills/web-scraper/scripts/fetch_rss.py --config profile/sources.yaml --output rss.json

# Job boards (scored against profile)
python3 skills/web-scraper/scripts/fetch_jobs.py --config profile/sources.yaml --interests profile/interests.yaml --output jobs.json

# Events
python3 skills/web-scraper/scripts/fetch_events.py --config profile/sources.yaml --output events.json

# German sentence (requires GEMINI_API_KEY in .env)
python3 skills/daily-newspaper/scripts/generate_german.py --output german.json --date "2026-02-18"

# Google Calendar (requires gog CLI + OAuth)
gog calendar events primary --from 2026-02-18T00:00:00Z --to 2026-02-19T23:59:59Z --json

# Render HTML from collected content
python3 skills/daily-newspaper/scripts/render_newspaper.py --profile-dir profile/ --content-dir /tmp/pm_daily_2026-02-18 --output output/daily/2026-02-18.html

# Feedback analysis
python3 skills/daily-newspaper/scripts/analyze_feedback.py
```

### Build the Personal Coach sub-app

The newspaper has two sections shown as top tabs: **News · Events · Jobs** (the
daily pipeline above) and **Personal Coach** (an embedded energy check-in app).
The coach is a React/Vite app under `coach/`; its build is committed to
`output/web/coach/` and the newspaper embeds it via an `<iframe>`. It is **not**
part of the daily pipeline — rebuild only when `coach/` source changes:

```bash
cd coach
npm install        # first time only
npm run build      # → output/web/coach/
```

See `coach/README.md` for details. The coach is a trim of `LifeCoach/web` with the
on-device AI coach removed (coaching is always deterministic and rule-based) and no
mock-data seeding (starts empty).

### Scheduling

**macOS (launchd):**
```bash
launchctl load ~/Library/LaunchAgents/com.personalmentor.daily.plist    # Enable
launchctl unload ~/Library/LaunchAgents/com.personalmentor.daily.plist  # Disable
launchctl start com.personalmentor.daily                                # Manual trigger
```
Plist at `~/Library/LaunchAgents/com.personalmentor.daily.plist`. Runs daily at 07:00. Logs to `~/Library/Logs/personalmentor-daily.log`.

**Important (macOS TCC):** the project lives under `~/Desktop/`, which is a privacy-protected folder. A launchd agent runs without the Full Disk Access that Terminal/IDE inherit, so it fails with `EX_CONFIG` (exit 78) if it must `chdir` into or write logs under `~/Desktop/`. The working setup therefore: (1) the plist's log paths point to `~/Library/Logs/` (not protected), (2) the plist has **no** `WorkingDirectory` key (`run_daily.sh` resolves its own root via `BASH_SOURCE`), and (3) `/bin/bash` is granted **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access) so the script can read/write the project at runtime. Verify a run with `launchctl kickstart -k gui/$(id -u)/com.personalmentor.daily` then check the log; `launchctl print gui/$(id -u)/com.personalmentor.daily | grep "last exit"` should show `0`.

**Windows (Task Scheduler):**
```powershell
# Create a daily task at 07:00 (run in PowerShell as Administrator)
schtasks /create /tn "PersonalMentor Daily" /tr "python \path\to\PersonalMentor\skills\daily-newspaper\scripts\run_daily.py" /sc daily /st 07:00
schtasks /run /tn "PersonalMentor Daily"     # Manual trigger
schtasks /delete /tn "PersonalMentor Daily"  # Remove
```

## Architecture

PersonalMentor is an autonomous agent that generates a daily HTML newspaper tailored to the user's profile. It runs unattended via macOS launchd or Windows Task Scheduler, fetches content from RSS/job boards/calendar, and publishes to GitHub Pages. The pipeline is cross-platform (macOS, Linux, Windows).

The newspaper is split into two top-tab sections: **News · Events · Jobs** (the daily pipeline) and **Personal Coach** (a React/Vite energy check-in sub-app under `coach/`, built to `output/web/coach/` and embedded via an `<iframe>` — see the build command above and `coach/README.md`). The tab shell lives in `skills/daily-newspaper/assets/template.html`; the `{{coach_url}}` placeholder is filled by `render_newspaper.py`.

### Daily Pipeline (run_daily.py / run_daily.sh)

```
Scheduler trigger (07:00) — launchd (macOS) / Task Scheduler (Windows) / cron (Linux)
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
- **Adaptive content**: `analyze_feedback.py` reads `memory/feedback.jsonl` and (1) adjusts per-section item counts (range 2-7) from the overall **rating**, and (2) distills free-text **comments** via Gemini (same model fallback chain) into `liked_topics` / `disliked_topics` / `preferred_sources` / `ignored_sources`, which `render_newspaper.py` uses to reweight news/event ranking (+2 liked, −3 disliked topics; +1/−2 sources). A `comments_hash` skips the Gemini call when comments haven't changed. Stored in `memory/learned-preferences.yaml`.
- **Feedback submission**: the newspaper's feedback card (1–5 stars + comment) POSTs directly to the GitHub Issues API when a fine-grained PAT (Issues: R/W, this repo only) is stored in the browser's localStorage (`pm_github_token`, one-time setup via the card's "Enable auto-submit" link — never in the HTML or git). Without a token it falls back to opening a pre-filled issue. `ingest_github_feedback.py` reads issues into `feedback.jsonl` on the next pipeline run and closes them.
- **Day-over-day novelty** (`render_newspaper.py`): news/event items shown on a previous day within `NOVELTY_WINDOW_DAYS` (7) are pushed to the back via `prioritize_unseen`, so each edition differs from recent ones; repeats only fill a track when there aren't enough fresh items (never blanks). Displayed items are recorded in `memory/seen-items.json` (machine-local, gitignored, pruned after `SEEN_RETENTION_DAYS`). Same-day re-runs reproduce the edition (items shown *today* aren't penalised). Jobs are not subject to novelty (match quality matters more there).
- **Gemini model fallback chain**: gemini-2.5-flash → gemini-2.0-flash → gemini-2.5-flash-lite (for German sentence generation).
- **10 color themes** in `skills/theme-factory/themes/`. Current theme: golden-hour. Applied via CSS variables at render time.

### Four Core Skills

| Skill | Entry Point | Purpose |
|---|---|---|
| `daily-newspaper` | `skills/daily-newspaper/scripts/run_daily.py` | Pipeline orchestrator + HTML renderer + German generator + feedback system |
| `web-scraper` | `skills/web-scraper/scripts/fetch_*.py` | RSS, job board, and event content fetching |
| `profile-manager` | `skills/profile-manager/scripts/` | CV parsing (PDF/DOCX), website scraping, onboarding interview |
| `memory-manager` | `skills/memory-manager/scripts/` | Append-only logging, artifact registry, preference learning |

### Data Flow

- **Profile** (`profile/*.yaml`): User identity, interests, preferences, content sources. Read by pipeline scripts.
- **Memory** (`memory/`): `artifacts.yaml` (artifact registry), `learned-preferences.yaml` (adaptive section weights), `feedback.jsonl` (raw user ratings), `session-log.jsonl` (action log).
- **Output** (`output/daily/`): Generated HTML newspapers, committed and pushed to GitHub for hosting at `alessandrosecchi.com/PersonalMentor/`.

### External Dependencies

- **GEMINI_API_KEY** (in `.env`): Required for German sentence generation via `google-genai` SDK.
- **gog CLI**: Optional. Fetches Google Calendar events. Pipeline continues without it. Install: `brew install steipete/tap/gogcli` (macOS) or see [gogcli releases](https://github.com/steipete/gogcli) (Windows/Linux).
- **GitHub Pages**: `index.html` at repo root redirects to today's newspaper.

### Feedback Server

`feedback_server.py` serves dual purpose:
- **First run** (no `profile/identity.yaml`): Launches onboarding wizard at `localhost:9847` with CV upload, website scrape, and preference form.
- **Normal run**: Serves feedback form embedded in each newspaper. Ratings saved to `memory/feedback.jsonl`. PID file at `<tempdir>/pm_feedback_server.pid` (platform temp directory).

## Session Notes

_This section is updated automatically after each session._
