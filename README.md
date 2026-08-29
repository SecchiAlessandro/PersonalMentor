# PersonalMentor

A fully autonomous personal productivity agent that delivers a beautiful daily newspaper — curated news, events, calendar reminders, and a German sentence of the day — all tailored to your profile.

**Live daily newspaper:** [alessandrosecchi.com/PersonalMentor](http://alessandrosecchi.com/PersonalMentor/)

---

## How It Works

Every day at 07:00, PersonalMentor runs a pipeline that:

1. **Fetches content** — RSS feeds, event platforms, Google Calendar
2. **Scores & ranks** — ranks articles and events by profile relevance, split into an Energy and an AI & Tech track
3. **Generates a German sentence** — daily A1-B1 sentence with AI-generated illustration (via Gemini)
4. **Renders a single HTML page** — self-contained, responsive, themed newspaper
5. **Pushes to GitHub** — auto-commits the newspaper so it's viewable via GitHub Pages

```
[07:00 trigger — launchd (macOS) / Task Scheduler (Windows) / cron (Linux)]
      │
      ├── Fetch RSS feeds (10 sources)
      ├── Fetch events (WikiCFP)
      │        ↓ (parallel)
      ├── Fetch Google Calendar (via gog CLI)
      ├── Generate German sentence + illustration (Gemini API)
      ├── Analyze past feedback (learned preferences)
      │        ↓
      ├── Render HTML newspaper (themed, responsive)
      ├── Register artifact in memory
      └── git commit + push to GitHub
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- [gog CLI](https://github.com/steipete/gogcli) (optional, for Google Calendar)
- A [Gemini API key](https://ai.google.dev/) with billing enabled

### 1. Clone & install

**macOS / Linux:**
```bash
git clone https://github.com/SecchiAlessandro/PersonalMentor.git
cd PersonalMentor
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/SecchiAlessandro/PersonalMentor.git
cd PersonalMentor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Set up environment

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Onboarding (new users)

Run the pipeline — if no profile exists, it launches the welcome wizard:

```bash
python skills/daily-newspaper/scripts/run_daily.py
```

This opens the **Welcome Page** in your browser at `http://localhost:9847/` where you can:

- Upload your CV (PDF or DOCX) — auto-extracts name, skills, experience
- Provide your personal website URL — scrapes bio and projects
- Fill in a short form: topics, preferred companies, design theme
- All data is saved locally as YAML files in `profile/`

After onboarding, re-run the script to generate your first newspaper.

### 4. Generate manually

**Cross-platform (recommended):**
```bash
python skills/daily-newspaper/scripts/run_daily.py
```

**macOS / Linux (legacy shell script, still works):**
```bash
bash skills/daily-newspaper/scripts/run_daily.sh
```

Output: `output/daily/YYYY-MM-DD.html`

### 5. Set up automatic daily runs

**macOS (launchd):**

The pipeline is scheduled via `launchd`. The plist is at:

```
~/Library/LaunchAgents/com.personalmentor.daily.plist
```

To load/unload:

```bash
launchctl load ~/Library/LaunchAgents/com.personalmentor.daily.plist
launchctl unload ~/Library/LaunchAgents/com.personalmentor.daily.plist
```

**Windows (Task Scheduler):**

```powershell
# Create a daily task at 07:00 (run in PowerShell as Administrator)
schtasks /create /tn "PersonalMentor Daily" /tr "python \path\to\PersonalMentor\skills\daily-newspaper\scripts\run_daily.py" /sc daily /st 07:00
schtasks /run /tn "PersonalMentor Daily"     # Manual trigger
schtasks /delete /tn "PersonalMentor Daily"  # Remove
```

---

## GitHub Pages Setup

The daily newspaper is automatically pushed to GitHub and served via GitHub Pages.

### Enable GitHub Pages

1. Go to **Settings > Pages** in your GitHub repo
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/ (root)**
4. Click **Save**

Once enabled, visit your site root — it auto-redirects to today's newspaper:

```
https://your-username.github.io/PersonalMentor/
```

Or access any specific day directly:

```
https://your-username.github.io/PersonalMentor/output/daily/2026-02-18.html
```

The `run_daily.py` pipeline auto-commits and pushes each day's HTML after generation.

---

## Newspaper Sections

The edition has two sections, each split into an **⚡ Energy** and an
**🤖 AI & Tech** track showing 3 items apiece — 12 items in total.

| Section | Source | Description |
|---------|--------|-------------|
| **News** | RSS feeds in `profile/sources.yaml` | Ranked by profile relevance, then split Energy / AI & Tech |
| **Events** | Event sources in `profile/sources.yaml` | Zürich-area events, split Energy / AI & Tech |
| **Calendar Events** | Google Calendar (gog) | Today's meetings and events |
| **German Sentence** | Gemini API | Daily A1-B1 sentence with translation and AI illustration |

### Retired: Jobs

The **Jobs For You** section was removed from the newspaper. `fetch_jobs.py` and
the `job_boards:` block in `profile/sources.yaml` are kept on disk (the latter
commented out) so the section can be switched back on; nothing in the pipeline
reads them today.

### Feedback System

Two ways to steer the next edition:

- **👍 / 👎 on any item.** Every news article and event carries a thumbs pair in its top-right corner. Clicks are remembered in your browser and ride along with the feedback card below — they are not sent one at a time.
- **A written comment** in the feedback card at the bottom of the page (no star rating).

On the next pipeline run, both are analyzed by Gemini into topic and source preferences that reweight what news and events get picked. A 👎 tells the system *less of this kind of item* — it lowers that topic's and source's score rather than blocking the URL, so a disliked item can still appear if it is genuinely the most relevant thing that day.

Feedback is delivered as a GitHub issue on this repo (label `feedback`), which the pipeline ingests and closes automatically.

**Enable auto-submit (recommended, one-time per browser):** by default, sending feedback opens a pre-filled GitHub issue you still have to submit by hand. To make it fully automatic:

1. Create a fine-grained personal access token at <https://github.com/settings/personal-access-tokens/new>:
   - **Repository access:** only this repository
   - **Permissions:** Issues → Read and write (nothing else)
2. In the newspaper's feedback card, click **Enable auto-submit** and paste the token.

The token is stored only in that browser's `localStorage` — it never appears in the page HTML, the repository, or git history. If it expires or is revoked, the card silently falls back to the manual pre-filled-issue flow.

---

## Project Structure

```
PersonalMentor/
├── CLAUDE.md                  # Agent working memory (loaded every session)
├── SPECIFICATIONS.md          # Full project specification
├── index.html                 # Redirects to today's newspaper (GitHub Pages)
├── requirements.txt           # Python dependencies
│
├── profile/                   # User profile (YAML, local only)
│   ├── identity.yaml          # Name, title, bio, contact
│   ├── experience.yaml        # Work history, education, skills
│   ├── interests.yaml         # Topics, target roles, preferred companies
│   ├── preferences.yaml       # Theme, tone, delivery time
│   └── sources.yaml           # RSS feeds, event sources (job boards retired)
│
├── memory/                    # Runtime data (local only)
│   ├── artifacts.yaml         # Registry of generated artifacts
│   ├── learned-preferences.yaml  # Preferences inferred from feedback
│   └── feedback.jsonl         # Raw feedback entries
│
├── output/
│   ├── daily/                 # Daily newspaper HTML files (pushed to GitHub)
│   ├── cv/                    # Generated CVs
│   ├── documents/             # Reports, letters, proposals
│   └── welcome.html           # Onboarding wizard page
│
├── skills/
│   ├── daily-newspaper/       # Pipeline orchestration + rendering
│   │   └── scripts/
│   │       ├── run_daily.py           # Main pipeline script (cross-platform)
│   │       ├── run_daily.sh          # Legacy pipeline script (macOS/Linux)
│   │       ├── render_newspaper.py   # HTML renderer
│   │       ├── generate_german.py    # German sentence + image via Gemini
│   │       ├── parse_gog.py          # Google Calendar JSON parser
│   │       ├── analyze_feedback.py   # Feedback → learned preferences
│   │       ├── feedback_server.py    # HTTP server for feedback + onboarding
│   │       └── onboard_handler.py    # Welcome wizard form handler
│   │
│   ├── web-scraper/           # Content fetching
│   │   └── scripts/
│   │       ├── fetch_rss.py          # RSS feed fetcher
│   │       ├── fetch_jobs.py         # Job board scraper (retired, not run)
│   │       └── fetch_events.py       # Event scraper
│   │
│   ├── profile-manager/       # Profile ingestion
│   │   └── scripts/
│   │       └── extract_cv.py         # CV parser (PDF/DOCX)
│   │
│   ├── memory-manager/        # Logging + artifact tracking
│   └── ... (16 existing skills)
│
└── workflows/                 # Multi-step workflow YAML files
```

---

## Skills

### Core Skills

| Skill | Purpose |
|-------|---------|
| **daily-newspaper** | Orchestrate content collection, ranking, and HTML generation |
| **profile-manager** | Ingest CV/website, run onboarding interview, maintain profile |
| **web-scraper** | Fetch RSS feeds and events, extract structured content |
| **memory-manager** | Log actions, track artifacts, update learned preferences |

### Existing Skills (16)

| Category | Skills |
|----------|--------|
| Documents | `docx`, `pdf`, `xlsx`, `pptx`, `Jinja2-cv` |
| Visual | `theme-factory`, `canvas-design`, `algorithmic-art`, `nano-banana-pro`, `frontend-design` |
| Web | `web-artifacts-builder`, `webapp-testing` |
| Integration | `gog` (Google Calendar + Contacts) |
| Orchestration | `workflow-mapper`, `agent-factory`, `skill-creator` |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Claude Code CLI (Claude Opus) |
| AI | Gemini API (text: `gemini-2.5-flash`, image: `gemini-2.5-flash-image`) |
| Scheduling | launchd (macOS), Task Scheduler (Windows), cron (Linux) |
| Languages | Python 3.11+ |
| Scraping | BeautifulSoup, requests, feedparser |
| Google integration | `gog` CLI |
| Hosting | GitHub Pages |
| Storage | Local filesystem (YAML, JSON, JSONL) |
