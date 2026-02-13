---
name: memory-manager
description: Manage PersonalMentor persistent memory. Use when logging actions to the session log, registering generated artifacts, updating learned preferences, or refreshing CLAUDE.md working memory. Handles all read/write operations on memory/ files.
---

# Memory Manager

Manage the persistent memory system stored in `memory/`. All memory is local, file-based, and private.

## Memory Files

| File | Format | Purpose |
|---|---|---|
| `memory/session-log.jsonl` | JSONL (append-only) | Log of every action taken |
| `memory/artifacts.yaml` | YAML | Registry of all generated artifacts |
| `memory/learned-preferences.yaml` | YAML | Preferences inferred from usage |

## Operations

### 1. Log an Action

Append a JSON line to `memory/session-log.jsonl` using the log script:

```bash
python3 scripts/log_action.py --action "<action_type>" --detail "<description>"
```

Action types: `onboarding`, `profile_update`, `artifact_generated`, `preference_learned`, `source_added`, `feedback_received`

Each log entry contains:
```json
{"timestamp": "ISO-8601", "action": "type", "detail": "description", "session_id": "uuid"}
```

### 2. Register an Artifact

After generating any artifact (daily newspaper, CV, document), register it:

```bash
python3 scripts/register_artifact.py \
  --type "daily-newspaper" \
  --path "output/daily/2026-02-13.html" \
  --sections "top-stories,jobs,calendar" \
  --item-count 25 \
  --sources "rss:techcrunch,rss:hackernews,gog:calendar"
```

This appends to `memory/artifacts.yaml` → `artifacts[]`.

### 3. Update Learned Preferences

After analyzing session logs, update `memory/learned-preferences.yaml`:

```bash
python3 scripts/update_preferences.py
```

The script reads `session-log.jsonl`, identifies patterns (liked/disliked topics, preferred sources), and writes updates to `learned-preferences.yaml`.

### 4. Refresh CLAUDE.md

After any session that modifies the profile or generates artifacts, refresh `CLAUDE.md`:

1. Read current profile from `profile/*.yaml`
2. Read recent artifacts from `memory/artifacts.yaml`
3. Read learned preferences from `memory/learned-preferences.yaml`
4. Rewrite the relevant sections of `CLAUDE.md`

Key sections to update:
- **User Identity**: name, title, location, key facts from profile
- **Preferences**: theme, tone, language from preferences.yaml
- **Recent Artifacts**: last 5 artifacts with dates and types
- **Active Goals**: derived from job_search status and interests
- **Known Opinions**: from learned-preferences.yaml

## Memory Flow

```
Action occurs (artifact generated, profile updated, etc.)
    ↓
Log to session-log.jsonl (always)
    ↓
If artifact → register in artifacts.yaml
    ↓
Periodically → analyze logs → update learned-preferences.yaml
    ↓
End of session → refresh CLAUDE.md
```
