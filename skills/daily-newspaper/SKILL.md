---
name: daily-newspaper
description: Generate the PersonalMentor daily newspaper — a single self-contained HTML artifact delivered at 8 PM with curated news, job offers, events, calendar, birthdays, skills, industry pulse, and reading list. Use when generating the daily artifact, testing the newspaper pipeline, or customizing the newspaper layout and content.
---

# Daily Newspaper

Orchestrate the full pipeline: fetch content, rank by relevance, render HTML, save to `output/daily/`.

## Pipeline Overview

```
1. Load profile  →  profile/*.yaml
2. Fetch content  →  web-scraper scripts + gog
3. Rank & filter  →  score by profile relevance
4. Render HTML   →  apply theme, build layout
5. Save output   →  output/daily/YYYY-MM-DD.html
6. Log to memory →  memory-manager scripts
```

## Step-by-Step

### 1. Load User Profile

Read all profile YAML files to understand the user:

```python
# Read these files:
# profile/identity.yaml   → name, title, location
# profile/interests.yaml  → topics, industries, job_search
# profile/preferences.yaml → theme, tone, sections_enabled
# profile/sources.yaml    → RSS feeds, job boards, event sources
```

### 2. Fetch Content

Run web-scraper scripts to collect raw content. Use `/tmp/pm_daily/` as working directory:

```bash
mkdir -p /tmp/pm_daily

# RSS feeds → news articles
python3 skills/web-scraper/scripts/fetch_rss.py \
  --config profile/sources.yaml \
  --output /tmp/pm_daily/rss.json

# Job listings
python3 skills/web-scraper/scripts/fetch_jobs.py \
  --config profile/sources.yaml \
  --interests profile/interests.yaml \
  --output /tmp/pm_daily/jobs.json

# Events
python3 skills/web-scraper/scripts/fetch_events.py \
  --config profile/sources.yaml \
  --output /tmp/pm_daily/events.json
```

For calendar and birthdays, use the `gog` skill:

```bash
# Today's calendar events
gog calendar events primary --from "$(date -I)T00:00:00" --to "$(date -I)T23:59:59" --json

# Contacts with birthdays (check contacts list)
gog contacts list --max 100 --json
```

### 3. Rank & Filter

For each content section, score items by relevance to the user profile:

- **Match professional interests** — topics in `interests.yaml → professional[]`
- **Match industries** — `interests.yaml → industries[]`
- **Deduplicate** — by URL or title similarity
- **Select top N** — per `preferences.yaml → daily_artifact.max_items_per_section`

### 4. Render HTML

Generate a self-contained HTML file using the template. Run:

```bash
python3 scripts/render_newspaper.py \
  --profile-dir profile/ \
  --content-dir /tmp/pm_daily/ \
  --output output/daily/$(date +%Y-%m-%d).html
```

The script uses the HTML template in `assets/template.html` and applies the user's theme from theme-factory.

**Design requirements:**
- Single self-contained HTML file (all CSS inline)
- Responsive layout (mobile + desktop)
- User's preferred theme from theme-factory
- Clean typography, generous whitespace, scannable layout
- Every item: title, source, 1-2 sentence summary, link, relevance tag
- Header: "Good evening, [Name] — [Day, Date]"

### 5. Save & Log

After rendering, register the artifact:

```bash
python3 skills/memory-manager/scripts/register_artifact.py \
  --type daily-newspaper \
  --path "output/daily/$(date +%Y-%m-%d).html" \
  --sections "top-stories,jobs,calendar,birthdays,events,skills,pulse,reading" \
  --item-count <total_items> \
  --sources "<comma-separated-sources>"

python3 skills/memory-manager/scripts/log_action.py \
  --action artifact_generated \
  --detail "Daily newspaper for $(date +%Y-%m-%d)"
```

## Scheduling

Set up an 8 PM daily cron job:

```bash
# Add to crontab:
0 20 * * * cd /path/to/PersonalMentor && claude --skill daily-newspaper --run "Generate today's daily newspaper"
```

Or use `scripts/run_daily.sh` which wraps the full pipeline.

## Sections Reference

| Section | Source Data | Content |
|---|---|---|
| Top Stories | rss.json | 3-5 news articles by relevance |
| Jobs For You | jobs.json | Matching positions with fit score |
| Today's Calendar | gog calendar | Meetings, deadlines, reminders |
| Birthdays | gog contacts | Contacts with birthdays today/this week |
| Events Near You | events.json | Conferences, meetups, webinars |
| Skill Spotlight | rss.json (filtered) | Trending skills + learning resources |
| Industry Pulse | rss.json (filtered) | Market trends, funding, launches |
| Reading List | rss.json (filtered) | Long-form articles worth reading |
