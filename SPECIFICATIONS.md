# PersonalMentor — Specifications

> **Core idea:** A fully autonomous agent that knows who you are — from your CV,
> interests, and personal website — and publishes a beautiful daily HTML
> artifact at 07:00 with curated news and events, tailored to you and reshaped
> every day by your feedback.

> **Status:** this document describes the system as built. Where the original
> design was abandoned, the reason is recorded rather than the intent deleted —
> see §12.

---

## 1. Vision

PersonalMentor is a **fully autonomous personal productivity agent** that:

- **Knows you** — imports your CV, parses your personal website, and interviews you to build a rich profile
- **Works daily** — at 07:00 every day, generates a single self-contained HTML page with everything worth knowing
- **Learns your preferences** — distills your written feedback and your per-item 👍/👎 into topic and source weights that reshape tomorrow's edition
- **Publishes itself** — commits and pushes to GitHub Pages, so the edition is readable anywhere without the laptop being on
- **Runs without asking** — fully autonomous, no approval needed for daily operations

---

## 2. The Daily Artifact

A single, self-contained HTML file generated every day at 07:00, published to
`output/daily/YYYY-MM-DD.html` and served from GitHub Pages.

The page has two top-level tabs:

1. **News · Events** — the daily pipeline's output (this document's subject)
2. **Personal Coach** — a React/Vite energy check-in sub-app under `coach/`, built to `output/web/coach/` and embedded via an `<iframe>`. Not part of the daily pipeline; rebuilt only when its source changes.

### Content Sections

Two sections. Each is split by keyword classification into an **⚡ Energy** and
an **🤖 AI & Tech** track, showing `MAX_ITEMS` (3) items apiece — 12 items per
edition.

| Section | Source | Description |
|---|---|---|
| **News ⚡ Energy** | RSS feeds (`sources.yaml`) | Grid, power markets, storage, energy transition |
| **News 🤖 AI & Tech** | RSS feeds (`sources.yaml`) | AI labs, research, applied ML, broad tech |
| **Events ⚡ Energy** | Event sources (`sources.yaml`) | Zürich-area energy events |
| **Events 🤖 AI & Tech** | Event sources (`sources.yaml`) | Zürich-area AI and tech events |
| **Today's Feedback** | — | Free-text comment box + the batched item votes |

### Design Requirements

- Single self-contained HTML file (inline CSS, no external dependencies)
- Responsive (mobile + desktop)
- Uses the user's preferred theme from `theme-factory`, applied as CSS variables at render time
- Clean typography, generous whitespace, scannable layout
- Every item has: title, source, one-sentence summary, link, relevance tag, and a 👍/👎 control
- Header: "Good morning, [Name] — [Day, Date]"
- Archive navigation to browse past issues

### Page Layout

```
┌─────────────────────────────────────────┐
│  [ News · Events ]  [ Personal Coach ]  │  ← tabs
├─────────────────────────────────────────┤
│  PersonalMentor Daily — [Date]          │
│  "Good morning, [Name]"                 │
├─────────────────────────────────────────┤
│  NEWS                                   │
│    ⚡ Energy        3 items      👍 👎   │
│    🤖 AI & Tech     3 items      👍 👎   │
├─────────────────────────────────────────┤
│  EVENTS                                 │
│    ⚡ Energy        3 items      👍 👎   │
│    🤖 AI & Tech     3 items      👍 👎   │
├─────────────────────────────────────────┤
│  TODAY'S FEEDBACK                       │
│  Comment box + pending vote count       │
│  [ Send Feedback ]                      │
└─────────────────────────────────────────┘
```

---

## 3. User Profile System

### 3.1 How the Profile is Built

Three complementary methods, run during onboarding:

1. **Import CV** — Parse the user's CV (PDF/DOCX) using `pdf` or `docx` skills to extract name, title, skills, experience, education
2. **Parse personal website** — Scrape the user's website to extract bio, projects, interests, writing style
3. **Interactive interview** — Ask focused questions to fill gaps: preferred topics, design taste, content sources, location

### 3.2 Profile Structure

```
profile/
├── identity.yaml          # Name, title, bio, contact info
├── experience.yaml        # Work history, education, projects, skills
├── interests.yaml         # Professional topics, industries, target roles
├── preferences.yaml       # Design theme, writing tone, content preferences
└── sources.yaml           # RSS feeds and event sources to monitor
```

**interests.yaml** — read by `relevance_score()` when ranking news and events.
`job_search.target_roles` is still live even though the Jobs section was retired:
a target-role match scores **+3** on an article or event.

```yaml
professional:
  - topic: ""
    weight: 1-10             # Added to the score on a whole-word match
industries: []               # +2 each
relevance_keywords: []       # bare string (+2) or {term, weight}
job_search:
  target_roles: []           # +3 each
  target_locations: []
```

**preferences.yaml**
```yaml
design:
  theme: ""                  # theme-factory theme name
writing:
  tone: ""                   # formal, conversational, technical
  language: ""               # en, it, de, etc.
daily_artifact:
  delivery_time: "07:00"
```

**sources.yaml**
```yaml
rss_feeds:
  - url: ""
    category: ""             # ai | energy | tech | news → picks the track
    type: html               # omit for real RSS/Atom; "html" scrapes the page
event_sources:
  - url: ""
    type: ""                 # html | api | eth_api | playwright
    location_filter: ""      # substring match; '' = no filter
# job_boards: retired — see §12
```

Prefer real RSS over `type: html`. HTML scrapes carry no publication date, which
degrades the day-over-day novelty ranking and tends to pick up site navigation
as "articles".

---

## 4. Memory System

All memory is local and file-based. Everything except `seen-items.json` is
committed, because the pipeline also runs in GitHub Actions on a fresh checkout.

### 4.1 Storage Layout

```
memory/
├── session-log.jsonl          # Append-only log of every action (gitignored)
├── artifacts.yaml             # Registry of generated artifacts
├── feedback.jsonl             # One entry per submitted feedback issue
├── learned-preferences.yaml   # Preferences distilled from feedback
└── seen-items.json            # Day-over-day novelty history (machine-local)
```

### 4.2 How Memory Works

```
Reader clicks 👍/👎 and/or writes a comment
       │
       ▼
  Batched in browser localStorage (pm_votes_<DATE>)
       │
       ▼
  "Send Feedback" → one GitHub issue per day
       │
       ▼
  ingest_github_feedback.py → feedback.jsonl, issue closed
       │
       ▼
  analyze_feedback.py → Gemini distillation
       │
       ▼
  learned-preferences.yaml
    liked_topics / disliked_topics / preferred_sources / ignored_sources
       │
       ▼
  render_newspaper.py reweights tomorrow's ranking
```

### 4.3 CLAUDE.md as Working Memory

`CLAUDE.md` is the agent's always-loaded context: who the user is, top
preferences, architecture and key design decisions, and the commands to run
each part of the pipeline. Manually editable by the user.

---

## 5. Architecture

```
PersonalMentor/
├── SPECIFICATIONS.md          # This document
├── CLAUDE.md                  # Active memory / user context
├── index.html                 # Redirects to the newest edition
├── .github/workflows/
│   ├── daily-newspaper.yml    # Runs the pipeline at 05:00 & 06:00 UTC
│   └── pages-deploy.yml       # Publishes the repo to GitHub Pages
├── profile/                   # User profile (YAML)
├── memory/                    # Feedback, artifact registry, learned prefs
├── coach/                     # Personal Coach sub-app (React/Vite source)
├── output/
│   ├── daily/                 # Daily newspaper HTML files
│   └── web/coach/             # Built Personal Coach (committed)
└── skills/
    ├── daily-newspaper/       # Pipeline orchestrator + renderer + feedback
    ├── profile-manager/       # CV parsing, website scrape, onboarding
    ├── web-scraper/           # RSS and event fetching
    ├── memory-manager/        # Logging, artifact registry, preferences
    └── ...                    # Supporting skills (docx, pdf, theme-factory, …)
```

---

## 6. Skills

### 6.1 Four Core Skills

| Skill | Entry Point | Purpose |
|---|---|---|
| `daily-newspaper` | `scripts/run_daily.py` | Pipeline orchestrator, HTML renderer, German generator, feedback system |
| `web-scraper` | `scripts/fetch_*.py` | RSS and event content fetching |
| `profile-manager` | `scripts/` | CV parsing (PDF/DOCX), website scraping, onboarding interview |
| `memory-manager` | `scripts/` | Append-only logging, artifact registry, preference learning |

### 6.2 Supporting Skills

| Category | Skill | Used By Daily Artifact? |
|---|---|---|
| **Documents** | `docx`, `pdf`, `xlsx`, `pptx` | CV updates |
| **Visual** | `theme-factory`, `algorithmic-art`, `nano-banana-pro`, `frontend-design` | Theme + design |
| **Web** | `web-artifacts-builder`, `webapp-testing` | HTML rendering |
| **Integration** | `gog` | Calendar (optional — pipeline continues without it) |

### 6.3 Not Built

`job-tracker`, `email-digest`, and `calendar-planner` were scoped in the
original design and never built. `job-tracker` is now out of scope — see §12.

---

## 7. Daily Artifact Pipeline

```
[07:00 local — launchd / Task Scheduler / cron]
[05:00 & 06:00 UTC — GitHub Actions, gated on "already published today"]
      │
      ▼
  1. Load user profile (profile/*.yaml)
      │
      ▼
  2. Fetch content in parallel (web-scraper)
     ├── fetch_rss.py    → rss.json
     └── fetch_events.py → events.json
      │
      ▼
  3. Ingest + analyze feedback (daily-newspaper)
     ├── ingest_github_feedback.py → feedback.jsonl, close issues
     └── analyze_feedback.py       → learned-preferences.yaml (Gemini)
      │
      ▼
  4. Rank & filter (render_newspaper.py)
     ├── Deduplicate by title
     ├── Keep events to the Zürich area
     ├── Score by profile relevance ± learned preferences
     ├── Split into Energy / AI & Tech tracks
     ├── Diversify by source
     ├── Push day-over-day repeats to the back (novelty)
     └── Take the top 3 per track
      │
      ▼
  5. Render HTML (theme applied as CSS variables, all inline)
      │
      ▼
  6. Save to output/daily/YYYY-MM-DD.html
      │
      ▼
  7. Log to memory + git commit & push → GitHub Pages
```

### 7.1 Ranking Rules

| Signal | Effect on score |
|---|---|
| `interests.professional[].topic` match | + its `weight` |
| `interests.industries` match | +2 |
| `job_search.target_roles` match | +3 |
| `relevance_keywords` match | +2 (or its `weight`) |
| `learned.liked_topics` match | +2 |
| `learned.disliked_topics` match | −3 |
| `learned.preferred_sources` match | +1 |
| `learned.ignored_sources` match | −2 |

Items scoring 0 or less are dropped — **unless nothing scores above 0**, in
which case the full relevance-ranked list is used, so a section is never blank.
A 👎 therefore *demotes*; it never blocks a URL outright.

### 7.2 Other Rules

- **Novelty** — items shown on a previous day within `NOVELTY_WINDOW_DAYS` (7) are pushed to the back. Items shown *today* are not penalised, so a same-day re-run reproduces the edition. History is pruned after `SEEN_RETENTION_DAYS` (45).
- **Zürich filter** — an event is kept unless its title or location names a clearly non-Zürich locality. A positive "contains zurich" rule was tried and dropped: event locations are messy ("WestHive", "TBD") and it removed most legitimate local events.
- **Energy event floor** — an event needs `MIN_ENERGY_TERMS_FOR_EVENT` (1) distinct energy terms for the energy track. Set to 2 originally to block wellness noise ("CEO Energy Break"), relaxed to 1 because no Zürich energy event on a typical day mentions two, leaving the track empty. The occasional false positive is accepted.

---

## 8. Feedback Model

Two inputs, one submission, one issue per day.

| Input | Collected by | Sent as |
|---|---|---|
| Per-item 👍/👎 | Control on every news/event card; batched in `localStorage` | `### Item votes` block, `vote \| section \| track \| source \| title` rows |
| Free-text comment | Card at the bottom of the page | `### Comment` block |

Submission POSTs directly to the GitHub Issues API when a fine-grained PAT
(Issues: R/W, this repo only) is in the browser's `localStorage`; otherwise it
opens a pre-filled issue the reader submits with one click. The token lives only
in the browser — never in the HTML or in git.

`analyze_feedback.py` hands voted titles to Gemini as **examples of the kind of
item** wanted more or less of, never as a blocklist. A source is only added to
`ignored_sources` when several disliked items came from it. A skip-hash over
comments *and* votes avoids re-calling the model when nothing changed.

There is no star rating: it was removed because the written comment and the item
votes carry strictly more information.

---

## 9. Autonomy Model

| Action | Level | Details |
|---|---|---|
| Daily newspaper generation | **Fully autonomous** | Runs at 07:00, no approval |
| Commit + push of the edition | **Fully autonomous** | Straight to `main`; Pages deploys from it |
| Feedback ingestion + issue closing | **Fully autonomous** | Silent, background |
| Preference learning | **Fully autonomous** | Silent, background |
| Profile updates from new data | **Fully autonomous** | New experience → update profile |
| CV regeneration | **Semi-autonomous** | Generates draft, user reviews |
| Sending emails | **User-triggered only** | Never sends without explicit request |
| Deleting files/data | **Always confirm** | Destructive actions require approval |

---

## 10. Technical Stack

| Layer | Technology |
|---|---|
| Runtime | Claude Code CLI (Claude Opus) |
| Scheduling | GitHub Actions (primary), launchd / Task Scheduler / cron (local) |
| Hosting | GitHub Pages |
| Languages | Python 3.11+, Node.js 18+, Bash |
| Documents | pypdf, reportlab, python-docx, openpyxl |
| Web rendering | HTML + inline CSS (self-contained) |
| Scraping | BeautifulSoup, requests, feedparser, Playwright (JS-rendered pages) |
| LLM | Gemini via `google-genai` (fallback: 2.5-flash → 2.0-flash → 2.5-flash-lite) |
| Google integration | `gog` CLI (optional) |
| Sub-app | React + Vite (Personal Coach) |
| Storage | Local filesystem (YAML, JSON, JSONL) |
| Themes | `theme-factory` (10 built-in themes) |

---

## 11. Implementation Status

### Phase 1: Foundation — done
- [x] Skill library, theme system, directory structure, initial `CLAUDE.md`

### Phase 2: Profile & Memory — done
- [x] `profile-manager` and `memory-manager` skills
- [x] Onboarding (CV + website + interview) via `feedback_server.py`

### Phase 3: Daily Newspaper — done
- [x] `web-scraper` and `daily-newspaper` skills
- [x] Themed HTML template, content sources configured
- [x] Scheduled delivery (GitHub Actions + local launchd)
- [x] Publishing to GitHub Pages

### Phase 4: Polish & Expand
- [x] Feedback loop — written comments distilled into topic/source weights
- [x] Per-item 👍/👎 feedback
- [x] Day-over-day novelty so editions differ
- [x] Archive browser for past issues (`index.html` + archive link)
- [x] Personal Coach sub-app
- [ ] Artifact auto-update (CV stays current)
- [ ] Additional integrations (Notion, Slack)

---

## 12. Retired Scope

Decisions that reversed part of the original design. Kept here so the reasoning
survives.

| Dropped | When | Why |
|---|---|---|
| **Jobs For You** section | Aug 2026 | Not acted on by the reader. `fetch_jobs.py` and the `job_boards:` block in `sources.yaml` are kept on disk (the latter commented out) so it can be switched back on; nothing in the pipeline reads them. `interests.yaml`'s `job_search:` stays live — it feeds news/event ranking. |
| **`job-tracker` skill** | Aug 2026 | Followed the Jobs section out of scope. |
| **Birthdays** | — | `gog` contacts integration never built; calendar is optional as it is. |
| **Skill Spotlight, Industry Pulse, Reading List** | — | Never built. Four thin sections read worse than two well-ranked ones; the Energy / AI & Tech split covers the same ground. |
| **Star ratings** | Jul 2026 | Replaced by the free-text comment, then by per-item votes — both carry more signal than a 1-5 number. |
| **20:00 delivery** | — | Moved to 07:00; the edition is a morning read. |

---

## 13. Success Criteria

PersonalMentor is successful when:

1. **The daily artifact is useful** — the user opens it every morning and finds content worth reading
2. **Both tracks stay full** — 3 energy and 3 AI items in each section, without padding from irrelevant sources
3. **Editions differ** — the same story does not lead two days running
4. **It learns** — after 2 weeks of 👍/👎, the content is noticeably better than day 1
5. **Zero effort** — the user doesn't configure anything after onboarding; it just works
