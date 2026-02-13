# Interview Questions Reference

Complete mapping of interview questions to profile YAML fields.

## Identity & Basics

| Question | Target File | Target Field |
|---|---|---|
| What is your full name? | identity.yaml | name |
| What is your current professional title or role? | identity.yaml | title |
| Where are you based? (city, country) | identity.yaml | location |
| Write a short bio (2-3 sentences) | identity.yaml | bio |

## Professional Interests

| Question | Target File | Target Field |
|---|---|---|
| Professional topics (up to 5, priority 1-10) | interests.yaml | professional[] |
| Industries you follow or work in | interests.yaml | industries[] |
| Personal interests/hobbies for daily brief | interests.yaml | personal[] |

## Job Search

| Question | Target File | Target Field |
|---|---|---|
| Currently looking for a new role? | interests.yaml | job_search.active |
| Target roles (list titles) | interests.yaml | job_search.target_roles[] |
| Target locations (remote/cities) | interests.yaml | job_search.target_locations[] |
| Target salary range | interests.yaml | job_search.salary_range |

## Design & Style

| Question | Target File | Target Field |
|---|---|---|
| Theme choice (from 10 options) | preferences.yaml | design.theme |
| Writing tone (formal/conversational/technical) | preferences.yaml | writing.tone |
| Summary length (concise/detailed) | preferences.yaml | writing.length |
| Language (en, it, de, fr, etc.) | preferences.yaml | writing.language |

## Content Sources

| Question | Target File | Target Field |
|---|---|---|
| Favorite RSS feeds/blogs/news sites | sources.yaml | rss_feeds[] |
| Job boards to monitor | sources.yaml | job_boards[] |
| Event platforms/meetup pages | sources.yaml | event_sources[] |

## Daily Newspaper Config

| Question | Target File | Target Field |
|---|---|---|
| Sections to include (default: all) | preferences.yaml | daily_artifact.sections_enabled[] |
| Delivery time (default: 20:00) | preferences.yaml | daily_artifact.delivery_time |
