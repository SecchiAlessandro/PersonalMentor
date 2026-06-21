#!/usr/bin/env python3
"""Fetch job listings from configured job boards."""

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Missing dependencies. Run: pip install requests beautifulsoup4")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

# Use OS certificate store (fixes corporate proxy SSL errors on Windows)
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Pure software-engineering titles to de-prioritize — the user targets
# management / commercial / strategy / AI lanes, not deep SWE. Matched
# whole-word against the title only, so phrases like "software engineer"
# never catch "AI engineer" / "ML engineer".
# Stored in normalized form (hyphens -> spaces); the title is normalized the
# same way before matching, so "Full-Stack" matches "full stack".
SWE_TITLE_TERMS = [
    "software engineer", "software developer", "backend", "back end",
    "frontend", "front end", "full stack", "fullstack", "devops",
    "embedded", "firmware", "qa engineer", "test engineer", "android",
    "ios developer", "web developer", "mobile developer",
    # Dev-stack signals (strong deep-SWE markers; none collide with the
    # target lanes like "business developer").
    "react", "react native", "angular", "vue", "java", "javascript",
    "typescript", "golang", "kotlin", "c++", ".net",
]
SWE_PENALTY = 0.3

# Prioritization weights for preferred employers in the Zürich area. The user
# wants jobs at Google / Microsoft / Hitachi and other AI/energy tech firms near
# Zürich to rank first, so a preferred-company match is a strong signal and gets
# an extra bonus when the role is also in the Zürich area.
PREFERRED_COMPANY_WEIGHT = 0.3
ZURICH_COMBO_BONUS = 0.3
ZURICH_AREA_TERMS = [
    "zurich", "zürich", "zuerich", "baden", "zug", "winterthur",
    "oerlikon", "glattbrugg", "wallisellen", "dietikon", "schlieren",
]


def _word_match(term, text):
    """True if term appears as a whole word in text (case-insensitive).

    Word-boundary matching avoids false positives like 'ai' inside
    'available'/'training' or a 'Google Cloud' mention tagging the employer.
    """
    term = str(term).strip().lower()
    if not term:
        return False
    return re.search(r"\b" + re.escape(term) + r"\b", text) is not None


def compute_match_score(job_title, job_text, interests, company=""):
    """Compute a relevance score based on keyword matching against the profile.

    Weights: role 0.4 + topic 0.3 + location 0.2 + preferred-company 0.3, plus a
    +0.3 bonus when a preferred company is also in the Zürich area — so jobs at
    Google / Microsoft / Hitachi and other AI/energy tech firms near Zürich rank
    first. A job is only considered relevant if it matches at least one signal
    (there is no unconditional base score). The score is intentionally uncapped
    so these priority jobs sort above the generic 1.0-ceiling matches; the report
    caps the displayed percentage at 100%.

    The preferred company is matched against the title + employer field only
    (not the free-text description), so a job that merely lists 'AWS' or 'Google
    Cloud' as a required skill is not tagged as being *at* that employer.
    """
    job_search = interests.get("job_search", {})
    target_roles = job_search.get("target_roles", [])
    target_locations = job_search.get("target_locations", [])
    preferred_companies = job_search.get("preferred_companies", [])
    professional = interests.get("professional", []) or []

    combined = f"{job_title} {job_text}".lower()
    employer_text = f"{job_title} {company}".lower()

    score = 0.0
    match_reasons = []

    for role in target_roles:
        if _word_match(role, combined):
            score += 0.4
            match_reasons.append(f"role: {role}")
            break

    for t in professional:
        topic = str(t.get("topic", ""))
        if _word_match(topic, combined):
            score += 0.3
            match_reasons.append(f"topic: {topic.lower()}")
            break

    for loc in target_locations:
        if _word_match(loc, combined):
            score += 0.2
            match_reasons.append(f"location: {loc}")
            break

    # Preferred employer (Google / Microsoft / Hitachi / other AI+energy tech).
    # Matched against the title + employer field only, so a description that just
    # lists 'AWS'/'Google Cloud' as a skill doesn't get tagged as that employer.
    matched_company = None
    for pref in preferred_companies:
        if _word_match(pref, employer_text):
            score += PREFERRED_COMPANY_WEIGHT
            match_reasons.append(f"company: {pref}")
            matched_company = pref
            break

    # Strong bonus for a preferred employer in the Zürich area — the user's
    # priority lane — so e.g. "Google Zürich" outranks "Google remote".
    if matched_company and any(_word_match(t, combined) for t in ZURICH_AREA_TERMS):
        score += ZURICH_COMBO_BONUS
        match_reasons.append("priority: preferred company in Zürich area")

    # De-prioritize pure software-engineering roles. This only lowers the rank
    # of jobs that already matched some signal — it never adds a match_reason,
    # so it cannot make an otherwise-irrelevant job pass the relevance filter.
    title_norm = job_title.lower().replace("-", " ")
    if any(_word_match(t, title_norm) for t in SWE_TITLE_TERMS):
        score = max(0.0, score - SWE_PENALTY)

    return round(score, 4), match_reasons


def is_link_live(url):
    """Check a job posting link is reachable (proxy for 'still accepting applications').

    Returns True only for URLs that resolve with an HTTP status < 400.
    Expired postings on most boards return 404/410, so this filters stale links.
    """
    if not url or not url.startswith("http"):
        return False
    try:
        resp = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        # Some servers reject HEAD (405) or mishandle it — fall back to GET.
        if resp.status_code >= 400:
            resp = requests.get(
                url, headers=HEADERS, timeout=15, allow_redirects=True, stream=True
            )
        return resp.status_code < 400
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Site-specific scrapers
# ---------------------------------------------------------------------------

def fetch_datacareer(url, interests):
    """Scrape datacareer.ch job listings."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            jobs = []
            for art in soup.select("article.listing-item"):
                title_el = art.select_one(".listing-item__title a.link")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    link = urljoin(url, link)

                company_el = art.select_one(".listing-item__info--item-company")
                company = company_el.get_text(strip=True) if company_el else ""

                location_el = art.select_one(".listing-item__info--item-location")
                location = location_el.get_text(strip=True) if location_el else ""

                text = f"{title} {company} {location}"
                score, reasons = compute_match_score(title, text, interests, company=company)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": link,
                    "source": "datacareer.ch",
                    "description": "",
                    "match_score": round(score, 2),
                    "match_reasons": reasons,
                })
            return jobs
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch datacareer {url}: {e}", file=sys.stderr)
                return []


def fetch_linkedin(url, interests):
    """Scrape LinkedIn guest jobs API HTML fragments."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            jobs = []
            for card in soup.select("li"):
                title_el = card.select_one(".base-search-card__title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                link_el = card.select_one("a.base-card__full-link, a.base-search-card__full-link")
                link = link_el.get("href", "").split("?")[0] if link_el else ""

                company_el = card.select_one(".base-search-card__subtitle a, .base-search-card__subtitle")
                company = company_el.get_text(strip=True) if company_el else ""

                location_el = card.select_one(".job-search-card__location")
                location = location_el.get_text(strip=True) if location_el else ""

                text = f"{title} {company} {location}"
                score, reasons = compute_match_score(title, text, interests, company=company)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": link,
                    "source": "LinkedIn",
                    "description": "",
                    "match_score": round(score, 2),
                    "match_reasons": reasons,
                })
            return jobs
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch LinkedIn {url}: {e}", file=sys.stderr)
                return []


def fetch_rss_jobs(url, filter_keywords, interests):
    """Fetch jobs from an RSS feed, filtering by keywords."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")

            jobs = []
            for item in soup.find_all("item"):
                title = item.find("title").get_text(strip=True) if item.find("title") else ""
                link = item.find("link").get_text(strip=True) if item.find("link") else ""
                desc = item.find("description").get_text(strip=True) if item.find("description") else ""
                desc = re.sub(r"<[^>]+>", "", desc)

                if not title:
                    continue

                # Filter by keywords if provided
                if filter_keywords:
                    combined_lower = f"{title} {desc}".lower()
                    if not any(kw.lower() in combined_lower for kw in filter_keywords):
                        continue

                text = f"{title} {desc}"
                score, reasons = compute_match_score(title, text, interests)

                jobs.append({
                    "title": title,
                    "company": "",
                    "location": "",
                    "url": link,
                    "source": "SwissDevJobs",
                    "description": desc,
                    "match_score": round(score, 2),
                    "match_reasons": reasons,
                })
            return jobs
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch RSS {url}: {e}", file=sys.stderr)
                return []


def fetch_board_generic(url, search_terms, interests):
    """Fallback: fetch job listings via generic HTML scraping."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            jobs = []
            for selector in [
                ".listing-item", ".job-listing", ".job-card", ".posting",
                "li.result", "article", "[data-job]",
            ]:
                elements = soup.select(selector)
                if elements:
                    for el in elements[:20]:
                        title_el = el.find(["h2", "h3", "a", "h4"])
                        title = title_el.get_text(strip=True) if title_el else ""
                        link = ""
                        if title_el and title_el.name == "a":
                            link = title_el.get("href", "")
                        elif title_el:
                            a = title_el.find("a")
                            if a:
                                link = a.get("href", "")

                        if not title:
                            continue

                        if link and not link.startswith("http"):
                            link = urljoin(url, link)

                        text = el.get_text(" ", strip=True)
                        score, reasons = compute_match_score(title, text, interests)

                        jobs.append({
                            "title": title,
                            "company": "",
                            "location": "",
                            "url": link,
                            "source": url,
                            "description": "",
                            "match_score": round(score, 2),
                            "match_reasons": reasons,
                        })
                    break

            return jobs
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch {url}: {e}", file=sys.stderr)
                return []


# ---------------------------------------------------------------------------
# Router: pick the right scraper based on board config
# ---------------------------------------------------------------------------

SITE_SCRAPERS = {
    "datacareer": fetch_datacareer,
    "linkedin": fetch_linkedin,
}


def fetch_jobs_for_board(board, interests):
    """Route a board config to the right scraper."""
    url = board.get("url", "")
    board_type = board.get("type", "html")
    search_terms = board.get("search_terms", [])
    filter_keywords = board.get("filter_keywords", [])
    site = board.get("site", "")

    # Auto-detect site from URL
    if not site:
        if "datacareer.ch" in url:
            site = "datacareer"
        elif "linkedin.com" in url:
            site = "linkedin"

    if board_type == "rss":
        return fetch_rss_jobs(url, filter_keywords, interests)
    elif site in SITE_SCRAPERS:
        return SITE_SCRAPERS[site](url, interests)
    else:
        return fetch_board_generic(url, search_terms, interests)


def main():
    parser = argparse.ArgumentParser(description="Fetch job listings from configured boards")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("--interests", required=True, help="Path to interests.yaml")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        sources = yaml.safe_load(f) or {}
    with open(args.interests, "r", encoding="utf-8") as f:
        interests = yaml.safe_load(f) or {}

    job_boards = sources.get("job_boards") or []
    if not job_boards:
        print("No job boards configured in sources.yaml")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(board):
        url = board.get("url", "")
        location_filter = board.get("location_filter", "")
        if not url:
            return []
        board_type = board.get("type", "html")
        print(f"Fetching jobs ({board_type}): {url}")
        jobs = fetch_jobs_for_board(board, interests)
        print(f"  Found {len(jobs)} listings")
        if location_filter and jobs:
            filter_lower = location_filter.lower()
            before = len(jobs)
            jobs = [
                j for j in jobs
                if filter_lower in j.get("location", "").lower()
                or filter_lower in j.get("title", "").lower()
                or filter_lower in j.get("company", "").lower()
            ]
            print(f"  Location filter '{location_filter}': {before} -> {len(jobs)} jobs")
        return jobs

    all_jobs = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_one, b): b for b in job_boards}
        for fut in as_completed(futures):
            try:
                all_jobs.extend(fut.result())
            except Exception as e:
                print(f"WARNING: board fetch error: {e}", file=sys.stderr)

    # Deduplicate by title (keep highest score)
    seen = {}
    for job in all_jobs:
        key = re.sub(r'\s+', ' ', job["title"].lower().strip())
        if key not in seen or job["match_score"] > seen[key]["match_score"]:
            seen[key] = job
    all_jobs = list(seen.values())

    # Keep only jobs genuinely relevant to the profile (matched a role or topic)
    before = len(all_jobs)
    all_jobs = [j for j in all_jobs if j.get("match_reasons")]
    print(f"Relevance filter: {before} -> {len(all_jobs)} jobs")

    # Sort by match score (highest first)
    all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    # Validate links for the top candidates so the report only shows postings
    # that are still reachable (a proxy for "still accepting applications").
    VALIDATE_TOP = 25
    head = all_jobs[:VALIDATE_TOP]
    tail = all_jobs[VALIDATE_TOP:]
    with ThreadPoolExecutor(max_workers=8) as pool:
        live_flags = list(pool.map(lambda j: is_link_live(j.get("url", "")), head))
    live_jobs = [j for j, live in zip(head, live_flags) if live]
    dropped = len(head) - len(live_jobs)
    print(f"Link validation: checked {len(head)}, dropped {dropped} dead/missing links")
    all_jobs = live_jobs + tail

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2)

    print(f"Fetched {len(all_jobs)} relevant jobs from {len(job_boards)} boards → {args.output}")


if __name__ == "__main__":
    main()
