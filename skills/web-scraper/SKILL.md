---
name: web-scraper
description: Fetch and extract structured content from the web for PersonalMentor. Use when scraping RSS feeds for news articles, fetching job listings from boards, extracting events from platforms, or parsing any web page for structured data. Outputs clean JSON for downstream processing.
---

# Web Scraper

Fetch content from web sources and output structured JSON. Used by the daily-newspaper pipeline and profile-manager (website parsing).

## Dependencies

```bash
pip install feedparser beautifulsoup4 requests pyyaml
```

## Operations

### 1. Fetch RSS Feeds

Parse RSS/Atom feeds and extract articles:

```bash
python3 scripts/fetch_rss.py --config profile/sources.yaml --output /tmp/rss_results.json
```

Reads `rss_feeds[]` from `profile/sources.yaml`, fetches each feed, and outputs:

```json
[
  {
    "title": "Article Title",
    "url": "https://...",
    "source": "Feed Name",
    "category": "tech",
    "published": "2026-02-13T10:00:00Z",
    "summary": "First 200 chars of content..."
  }
]
```

### 2. Fetch Job Listings

Scrape job board pages for matching positions:

```bash
python3 scripts/fetch_jobs.py --config profile/sources.yaml --interests profile/interests.yaml --output /tmp/jobs_results.json
```

Reads `job_boards[]` from sources.yaml and `job_search` from interests.yaml. Outputs:

```json
[
  {
    "title": "Job Title",
    "company": "Company Name",
    "location": "City, Country",
    "url": "https://...",
    "source": "Board Name",
    "match_score": 0.85,
    "match_reasons": ["skill: Python", "role: Senior Engineer"]
  }
]
```

### 3. Fetch Events

Scrape event platforms for relevant events:

```bash
python3 scripts/fetch_events.py --config profile/sources.yaml --output /tmp/events_results.json
```

Outputs:

```json
[
  {
    "title": "Event Name",
    "date": "2026-02-20",
    "location": "City or Online",
    "url": "https://...",
    "source": "Platform Name",
    "type": "conference"
  }
]
```

### 4. Parse Web Page

Extract structured content from any URL (used for website parsing in profile-manager):

```bash
python3 scripts/parse_page.py --url "https://example.com" --output /tmp/page_data.json
```

Outputs:

```json
{
  "title": "Page Title",
  "description": "Meta description",
  "headings": ["H1 text", "H2 text"],
  "paragraphs": ["Main text content..."],
  "links": [{"text": "Link text", "href": "https://..."}],
  "images": [{"alt": "Image alt", "src": "https://..."}]
}
```

## Error Handling

- Network failures: retry up to 3 times with 2-second backoff
- Malformed feeds: skip and log warning, continue with remaining feeds
- Rate limiting: respect Retry-After headers, default 5-second delay between requests
- Timeout: 30 seconds per request

## Usage in Daily Pipeline

The daily-newspaper skill calls the web-scraper scripts during content collection:

```
1. fetch_rss.py → news articles for Top Stories, Industry Pulse, Reading List
2. fetch_jobs.py → positions for Jobs For You
3. fetch_events.py → events for Events Near You
4. gog calendar/contacts → Calendar, Birthdays (handled by gog skill directly)
```
