# PersonalMentor — Specifications

> **Core idea:** A fully autonomous agent that knows who you are — from your CV, interests, and personal website — and delivers a beautiful daily HTML artifact at 8 PM with curated news, job offers, events, calendar reminders, and birthdays, all tailored to you.

---

## 1. Vision

PersonalMentor is a **fully autonomous personal productivity agent** that:

- **Knows you** — imports your CV, parses your personal website, and interviews you to build a rich profile
- **Works daily** — at 8 PM every day, generates a single self-contained HTML page with everything you need to know
- **Learns your preferences** — remembers your design style, topics of interest, and feedback to improve over time
- **Uses existing skills** — leverages the 16 skills already built (theme-factory, frontend-design, web-artifacts-builder, gog, etc.) to produce high-quality output
- **Runs without asking** — fully autonomous, no approval needed for daily operations

---

## 2. The Daily Artifact

A single, beautiful HTML file generated every day at 8 PM containing:

### Content Sections

| Section | Source | Description |
|---|---|---|
| **Top Stories** | RSS feeds, web scraping | 3-5 news articles relevant to your industry and interests |
| **Jobs For You** | Job boards, scraped listings | Open positions matching your profile, with a fit score |
| **Today's Calendar** | Google Calendar via `gog` | Upcoming meetings, deadlines, and reminders |
| **Birthdays** | Google Contacts via `gog` | Contacts with birthdays today or this week |
| **Events Near You** | Event platforms, meetup sites | Conferences, meetups, webinars relevant to your field |
| **Skill Spotlight** | Learning platforms | Trending skills in your domain + courses/resources |
| **Industry Pulse** | News, funding trackers | Market trends, startup launches, funding rounds |
| **Reading List** | Curated suggestions | Long-form articles and papers worth your time |

### Design Requirements

- Single self-contained HTML file (inline CSS, no external dependencies)
- Responsive (mobile + desktop)
- Uses the user's preferred theme from `theme-factory`
- Clean typography, generous whitespace, scannable layout
- Every item has: title, source, 1-2 sentence summary, link, relevance tag
- Header: "Good evening, [Name] — [Day, Date]"
- Archive navigation to browse past issues

### Page Layout

```
┌─────────────────────────────────────────┐
│  PersonalMentor Daily — [Date]          │
│  "Good evening, [Name]"                 │
├─────────────────────────────────────────┤
│  TOP STORIES (3-5 articles)             │
│  Curated by relevance to your profile   │
├──────────────────┬──────────────────────┤
│  JOBS FOR YOU    │  CALENDAR & BIRTHDAYS│
│  Matching roles  │  Today's schedule    │
│  with fit score  │  Upcoming birthdays  │
├──────────────────┴──────────────────────┤
│  EVENTS NEAR YOU                        │
│  Conferences, meetups, webinars         │
├─────────────────────────────────────────┤
│  SKILL SPOTLIGHT                        │
│  Trending skills + learning resources   │
├─────────────────────────────────────────┤
│  INDUSTRY PULSE                         │
│  Market trends, funding, launches       │
├─────────────────────────────────────────┤
│  READING LIST                           │
│  Long-form articles worth your time     │
└─────────────────────────────────────────┘
```

---

## 3. User Profile System

### 3.1 How the Profile is Built

Three complementary methods, run during onboarding:

1. **Import CV** — Parse the user's CV (PDF/DOCX) using `pdf` or `docx` skills to extract name, title, skills, experience, education
2. **Parse personal website** — Scrape the user's website to extract bio, projects, interests, writing style
3. **Interactive interview** — Ask focused questions to fill gaps: preferred topics, job search status, design taste, content sources, location

### 3.2 Profile Structure

```
profile/
├── identity.yaml          # Name, title, bio, contact info
├── experience.yaml        # Work history, education, projects, skills
├── interests.yaml         # Professional topics, industries, personal hobbies
├── preferences.yaml       # Design theme, writing tone, content preferences
└── sources.yaml           # RSS feeds, job boards, news sites to monitor
```

**identity.yaml**
```yaml
name: ""
title: ""
location: ""
bio: ""
contact:
  email: ""
  linkedin: ""
  website: ""
  github: ""
```

**interests.yaml**
```yaml
professional:
  - topic: ""
    weight: 1-10             # Relevance priority
industries: []
personal: []
job_search:
  active: true/false
  target_roles: []
  target_locations: []
  salary_range: ""
```

**preferences.yaml**
```yaml
design:
  theme: ""                  # theme-factory theme name
  colors: []
writing:
  tone: ""                   # formal, conversational, technical
  length: ""                 # concise, detailed
  language: ""               # en, it, de, etc.
daily_artifact:
  delivery_time: "20:00"
  sections_enabled: []       # Which sections to include
  max_items_per_section: 5
```

**sources.yaml**
```yaml
rss_feeds:
  - url: ""
    category: ""             # news, tech, industry, etc.
job_boards:
  - url: ""
    search_terms: []
event_sources:
  - url: ""
    location_filter: ""
```

---

## 4. Memory System

All memory is local, file-based, and private.

### 4.1 Storage Layout

```
memory/
├── session-log.jsonl          # Append-only log of every action
├── artifacts.yaml             # Registry of generated artifacts
└── learned-preferences.yaml   # Preferences inferred from usage
```

### 4.2 How Memory Works

```
User interacts with PersonalMentor
       │
       ▼
  Log action → session-log.jsonl
       │
       ▼
  If artifact produced → update artifacts.yaml
       │
       ▼
  Analyze patterns in session-log
       │
       ▼
  Update learned-preferences.yaml
       │
       ▼
  Distill key insights into CLAUDE.md
```

### 4.3 CLAUDE.md as Working Memory

`CLAUDE.md` is the agent's always-loaded context. It contains a distilled summary of:

- Who the user is (name, role, key facts)
- Top preferences (theme, tone, format)
- Recent artifacts and their status
- Active goals
- Known strong opinions or quirks

Updated automatically after each session. Manually editable by the user.

---

## 5. Architecture

```
PersonalMentor/
├── SPECIFICATIONS.md          # This document
├── CLAUDE.md                  # Active memory / user context
├── profile/                   # User profile (YAML)
├── memory/                    # Session logs, artifact registry, learned prefs
├── output/
│   ├── daily/                 # Daily newspaper HTML files
│   │   ├── 2026-02-13.html
│   │   └── ...
│   ├── cv/                    # Generated CVs
│   ├── documents/             # Reports, letters, proposals
│   └── web/                   # Websites, dashboards
├── skills/                    # 16 existing + new skills
│   ├── daily-newspaper/       # NEW: generate the daily artifact
│   ├── profile-manager/       # NEW: ingest and manage user profile
│   ├── web-scraper/           # NEW: fetch RSS, news, job listings
│   ├── memory-manager/        # NEW: read/write persistent memory
│   └── ... (16 existing skills)
└── workflows/                 # Multi-step workflow YAML files
```

---

## 6. Skills

### 6.1 Existing Skills (16)

| Category | Skill | Used By Daily Artifact? |
|---|---|---|
| **Documents** | `docx`, `pdf`, `xlsx`, `pptx`, `Jinja2-cv` | CV updates |
| **Visual** | `theme-factory`, `canvas-design`, `algorithmic-art`, `nano-banana-pro`, `frontend-design` | Theme + design |
| **Web** | `web-artifacts-builder`, `webapp-testing` | HTML rendering |
| **Integration** | `gog` | Calendar + birthdays + contacts |
| **Orchestration** | `workflow-mapper`, `agent-factory`, `skill-creator` | Workflow coordination |

### 6.2 New Skills Needed

| Skill | Priority | Purpose |
|---|---|---|
| `profile-manager` | **P0** | Ingest CV/website, run interview, maintain profile YAML |
| `web-scraper` | **P0** | Fetch RSS feeds, scrape job boards, extract structured content |
| `daily-newspaper` | **P0** | Orchestrate content collection, ranking, and HTML generation |
| `memory-manager` | **P0** | Log actions, track artifacts, update learned preferences |
| `job-tracker` | P1 | Monitor job boards, track applications, tailor CVs per role |
| `email-digest` | P2 | Summarize inbox, surface important threads |
| `calendar-planner` | P2 | Proactive scheduling suggestions |

---

## 7. Daily Artifact Pipeline

The end-to-end flow for generating the daily HTML:

```
[8 PM trigger]
      │
      ▼
  1. Load user profile (profile/*.yaml)
      │
      ▼
  2. Fetch content (web-scraper skill)
     ├── RSS feeds → news articles
     ├── Job boards → matching positions
     ├── Event platforms → upcoming events
     └── Google Calendar/Contacts (gog) → schedule + birthdays
      │
      ▼
  3. Rank & filter (daily-newspaper skill)
     ├── Score each item by relevance to profile
     ├── Deduplicate
     ├── Select top items per section
     └── Generate 1-2 sentence summaries
      │
      ▼
  4. Render HTML (frontend-design + theme-factory)
     ├── Apply user's preferred theme
     ├── Build responsive layout
     ├── Inline all CSS
     └── Add archive navigation
      │
      ▼
  5. Save to output/daily/YYYY-MM-DD.html
      │
      ▼
  6. Log to memory (memory-manager skill)
     └── Record what was generated, sources used, item count
```

---

## 8. Autonomy Model

| Action | Level | Details |
|---|---|---|
| Daily newspaper generation | **Fully autonomous** | Runs at 8 PM, no approval |
| Profile updates from new data | **Fully autonomous** | New experience → update profile |
| Preference learning | **Fully autonomous** | Silent, background |
| CV regeneration | **Semi-autonomous** | Generates draft, user reviews |
| Sending emails | **User-triggered only** | Never sends without explicit request |
| Deleting files/data | **Always confirm** | Destructive actions require approval |

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Runtime | Claude Code CLI (Claude Opus) |
| Scheduling | cron / launchd (macOS) |
| Languages | Python 3.11+, Node.js 18+, Bash |
| Documents | pypdf, reportlab, python-docx, openpyxl |
| Web rendering | HTML + inline CSS (self-contained) |
| Scraping | BeautifulSoup, requests, feedparser (RSS) |
| Google integration | `gog` CLI |
| Storage | Local filesystem (YAML, JSON, JSONL) |
| Themes | `theme-factory` (10 built-in themes) |

---

## 10. Implementation Roadmap

### Phase 1: Foundation
- [x] 16 working skills
- [x] Theme system
- [x] Workflow mapper + agent factory
- [ ] Create directory structure (`profile/`, `memory/`, `output/`)
- [ ] Write initial `CLAUDE.md`

### Phase 2: Profile & Memory
- [ ] Build `profile-manager` skill
- [ ] Build `memory-manager` skill
- [ ] Run first onboarding (import CV + website + interview)
- [ ] Auto-populate `CLAUDE.md` from profile

### Phase 3: Daily Newspaper
- [ ] Build `web-scraper` skill
- [ ] Build `daily-newspaper` skill
- [ ] Design HTML template with `theme-factory`
- [ ] Configure content sources in `sources.yaml`
- [ ] Set up 8 PM cron job
- [ ] Test with real data for 1 week

### Phase 4: Polish & Expand
- [ ] Feedback loop (mark articles as relevant/irrelevant)
- [ ] Artifact auto-update (CV stays current)
- [ ] `job-tracker` skill
- [ ] Archive browser for past daily issues
- [ ] Additional integrations (Notion, Slack)

---

## 11. Success Criteria

PersonalMentor is successful when:

1. **The daily artifact is useful** — the user opens it every evening and finds content worth reading
2. **Jobs are relevant** — at least 3 out of 5 job suggestions match what the user would actually apply for
3. **Calendar/birthdays are accurate** — no missed events, no stale data
4. **It learns** — after 2 weeks, the content quality is noticeably better than day 1
5. **Zero effort** — the user doesn't configure anything after onboarding; it just works
