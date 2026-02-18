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

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def compute_match_score(job_title, job_text, interests):
    """Compute a simple relevance score based on keyword matching.

    Weights: role 0.3 + location 0.2 + company 0.2 + base 0.3 = max 1.0
    """
    job_search = interests.get("job_search", {})
    target_roles = job_search.get("target_roles", [])
    target_locations = job_search.get("target_locations", [])
    preferred_companies = job_search.get("preferred_companies", [])

    combined = f"{job_title} {job_text}".lower()

    score = 0.0
    match_reasons = []

    for role in target_roles:
        if role.lower() in combined:
            score += 0.3
            match_reasons.append(f"role: {role}")
            break

    for loc in target_locations:
        if loc.lower() in combined:
            score += 0.2
            match_reasons.append(f"location: {loc}")
            break

    for company in preferred_companies:
        if company.lower() in combined:
            score += 0.2
            match_reasons.append(f"company: {company}")
            break

    score += 0.3
    return min(score, 1.0), match_reasons


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
                score, reasons = compute_match_score(title, text, interests)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": link,
                    "source": "datacareer.ch",
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
                score, reasons = compute_match_score(title, text, interests)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": link,
                    "source": "LinkedIn",
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

    with open(args.config, "r") as f:
        sources = yaml.safe_load(f) or {}
    with open(args.interests, "r") as f:
        interests = yaml.safe_load(f) or {}

    job_boards = sources.get("job_boards") or []
    if not job_boards:
        print("No job boards configured in sources.yaml")
        with open(args.output, "w") as f:
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

    # Sort by match score (highest first)
    all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_jobs, f, indent=2)

    print(f"Fetched {len(all_jobs)} unique jobs from {len(job_boards)} boards → {args.output}")


if __name__ == "__main__":
    main()
