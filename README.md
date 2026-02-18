# PersonalMentor

A fully autonomous personal productivity agent that delivers a beautiful daily newspaper — curated news, job offers, events, calendar reminders, and a German sentence of the day — all tailored to your profile.

**Live daily newspaper:** [alessandrosecchi.com/PersonalMentor](http://alessandrosecchi.com/PersonalMentor/)

---

## How It Works

Every day at 07:00, PersonalMentor runs a pipeline that:

1. **Fetches content** — RSS feeds, job boards, event platforms, Google Calendar
2. **Scores & ranks** — matches jobs to your profile (role, location, preferred companies), ranks articles by interest
3. **Generates a German sentence** — daily A1-B1 sentence with AI-generated illustration (via Gemini)
4. **Renders a single HTML page** — self-contained, responsive, themed newspaper
5. **Pushes to GitHub** — auto-commits the newspaper so it's viewable via GitHub Pages

```
[07:00 trigger via launchd]
      │
      ├── Fetch RSS feeds (10 sources)
      ├── Scrape job boards (8 boards, LinkedIn + datacareer + SwissDevJobs)
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

```bash
git clone https://github.com/SecchiAlessandro/PersonalMentor.git
cd PersonalMentor
python3 -m venv .venv && source .venv/bin/activate
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
bash skills/daily-newspaper/scripts/run_daily.sh
```

This opens the **Welcome Page** in your browser at `http://localhost:9847/` where you can:

- Upload your CV (PDF or DOCX) — auto-extracts name, skills, experience
- Provide your personal website URL — scrapes bio and projects
- Fill in a short form: topics, job preferences, preferred companies, design theme
- All data is saved locally as YAML files in `profile/`

After onboarding, re-run the script to generate your first newspaper.

### 4. Generate manually

```bash
bash skills/daily-newspaper/scripts/run_daily.sh
```

Output: `output/daily/YYYY-MM-DD.html`

### 5. Set up automatic daily runs (macOS)

The pipeline is scheduled via `launchd`. The plist is at:

```
~/Library/LaunchAgents/com.personalmentor.daily.plist
```

To load/unload:

```bash
launchctl load ~/Library/LaunchAgents/com.personalmentor.daily.plist
launchctl unload ~/Library/LaunchAgents/com.personalmentor.daily.plist
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

The `run_daily.sh` pipeline auto-commits and pushes each day's HTML after generation.

---

## Newspaper Sections

| Section | Source | Description |
|---------|--------|-------------|
| **Top Stories** | 10 RSS feeds | AI, energy, tech, Swiss news — ranked by your interests |
| **Jobs For You** | 8 job boards | LinkedIn, datacareer.ch, SwissDevJobs — scored by role, location, and preferred company match |
| **Calendar Events** | Google Calendar (gog) | Today's meetings and events |
| **German Sentence** | Gemini API | Daily A1-B1 sentence with translation and AI illustration |
| **Events Near You** | WikiCFP | Upcoming conferences in AI and energy |

### Job Scoring

Jobs are scored 0.0–1.0 based on:

- **Role match** (+0.3) — matches target roles from your profile
- **Location match** (+0.2) — matches target locations
- **Company match** (+0.2) — matches preferred companies (e.g., Hitachi, Google, Microsoft)
- **Base score** (+0.3) — every job gets a baseline

### Feedback System

After reading your newspaper, rate sections via the built-in feedback widget (bottom of the page). Ratings are analyzed on the next run to adjust section sizes and item counts.

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
│   ├── interests.yaml         # Topics, job search, preferred companies
│   ├── preferences.yaml       # Theme, tone, delivery time
│   └── sources.yaml           # RSS feeds, job boards, event sources
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
│   │       ├── run_daily.sh          # Main pipeline script
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
│   │       ├── fetch_jobs.py         # Job board scraper + scoring
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
| **web-scraper** | Fetch RSS feeds, scrape job boards, extract structured content |
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
| Scheduling | launchd (macOS) |
| Languages | Python 3.11+, Bash |
| Scraping | BeautifulSoup, requests, feedparser |
| Google integration | `gog` CLI |
| Hosting | GitHub Pages |
| Storage | Local filesystem (YAML, JSON, JSONL) |
