---
name: profile-manager
description: Manage the PersonalMentor user profile. Use when the user wants to onboard (import CV, parse personal website, run interview), update their profile, or modify their preferences and content sources. Handles all CRUD operations on profile/*.yaml files.
---

# Profile Manager

Manage the user profile stored in `profile/` YAML files. The profile drives all PersonalMentor personalization — daily newspaper content, job matching, theme selection, and tone.

## Profile Files

| File | Contents |
|---|---|
| `profile/identity.yaml` | Name, title, bio, location, contact info |
| `profile/experience.yaml` | Work history, education, projects, skills |
| `profile/interests.yaml` | Professional topics, industries, personal hobbies, job search |
| `profile/preferences.yaml` | Design theme, writing tone, language, daily artifact config |
| `profile/sources.yaml` | RSS feeds, job boards, event sources to monitor |

## Onboarding Process

Run onboarding when the profile is empty (fields are blank). Three complementary methods:

### 1. Import CV

Parse the user's CV to extract structured data:

```
1. Ask user for CV file path (PDF or DOCX)
2. Read the CV using the pdf or docx skill
3. Extract: name, title, skills, work history, education, projects
4. Write extracted data to identity.yaml and experience.yaml
5. Infer professional interests from experience → write to interests.yaml
```

**Extraction targets:**
- `identity.yaml`: name, title, bio (from summary/objective), contact info
- `experience.yaml`: work_history, education, projects, skills (technical, languages, tools)
- `interests.yaml`: professional topics inferred from skills and experience

### 2. Parse Personal Website

Scrape the user's website to enrich the profile:

```
1. Ask user for their website URL
2. Fetch the page content
3. Extract: bio, projects, blog topics, interests, writing style
4. Merge with existing profile data (don't overwrite CV-sourced data)
5. Update identity.yaml (bio), interests.yaml (topics from blog/projects)
```

### 3. Interactive Interview

Ask focused questions to fill remaining gaps. Run the interview script:

```bash
python3 scripts/interview.py
```

The script prints questions to stdout. Ask each question, collect answers, then update the profile YAML files accordingly.

See `references/interview-questions.md` for the full question set and which YAML fields each answer maps to.

## Updating the Profile

After onboarding, the profile can be updated at any time:

- **Add experience**: Append to `experience.yaml` work_history or projects
- **Change preferences**: Edit `preferences.yaml` (theme, tone, sections)
- **Add sources**: Append RSS feeds, job boards, or event sources to `sources.yaml`
- **Toggle job search**: Set `interests.yaml` → `job_search.active` to true/false

Always validate YAML syntax after writing. Use the `scripts/validate_profile.py` script:

```bash
python3 scripts/validate_profile.py
```

## Updating CLAUDE.md

After any profile change, update `CLAUDE.md` to reflect the current state:
- User identity section: name, title, location, key facts
- Preferences section: theme, tone, language
- Active goals: based on job_search status and interests
