# PersonalMentor — Agent Memory

> This file is the agent's working memory. It is loaded at the start of every session.
> Updated automatically after each session. Manually editable by the user.

## User Identity

- **Name:** (not yet configured — run onboarding)
- **Title:** —
- **Location:** —
- **Key facts:** —

## Preferences

- **Theme:** Modern Minimalist (default)
- **Tone:** conversational
- **Language:** en
- **Delivery time:** 20:00

## Recent Artifacts

_No artifacts generated yet._

## Active Goals

- Complete onboarding (import CV, parse website, run interview)
- Generate first daily newspaper

## Known Opinions / Quirks

_None recorded yet._

## Session Notes

_This section is updated automatically after each session._

---

## How to Get Started

1. Run the **profile-manager** skill to complete onboarding:
   - Import your CV (PDF or DOCX)
   - Provide your personal website URL
   - Answer a short interview to fill in preferences
2. Configure your content sources in `profile/sources.yaml`
3. The daily newspaper will be generated automatically at 8 PM

## Project Structure

```
PersonalMentor/
├── CLAUDE.md              ← You are here (agent working memory)
├── SPECIFICATIONS.md      ← Full project specification
├── profile/               ← User profile YAML files
├── memory/                ← Session logs, artifact registry, learned prefs
├── output/
│   ├── daily/             ← Daily newspaper HTML files
│   ├── cv/                ← Generated CVs
│   ├── documents/         ← Reports, letters, proposals
│   └── web/               ← Websites, dashboards
├── skills/                ← All skills (16 existing + 4 new)
└── workflows/             ← Multi-step workflow YAML files
```

## Skills Available

### Core Skills (new)
- **profile-manager** — Ingest CV/website, run interview, maintain profile YAML
- **memory-manager** — Log actions, track artifacts, update learned preferences
- **web-scraper** — Fetch RSS feeds, scrape job boards, extract structured content
- **daily-newspaper** — Orchestrate content collection, ranking, and HTML generation

### Existing Skills (16)
docx, pdf, xlsx, pptx, Jinja2-cv, theme-factory, canvas-design, algorithmic-art,
nano-banana-pro, frontend-design, web-artifacts-builder, webapp-testing, gog,
workflow-mapper, agent-factory, skill-creator
