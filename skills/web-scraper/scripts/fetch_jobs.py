#!/usr/bin/env python3
"""Fetch job listings from configured job boards."""

import argparse
import json
import os
import sys
import time

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
    "User-Agent": "PersonalMentor/1.0 (job-aggregator)"
}


def compute_match_score(job_title, job_text, interests):
    """Compute a simple relevance score based on keyword matching."""
    target_roles = interests.get("job_search", {}).get("target_roles", [])
    skills = []

    # Combine all text for matching
    combined = f"{job_title} {job_text}".lower()

    score = 0.0
    match_reasons = []

    # Check role match
    for role in target_roles:
        if role.lower() in combined:
            score += 0.4
            match_reasons.append(f"role: {role}")
            break

    # Check location match
    target_locations = interests.get("job_search", {}).get("target_locations", [])
    for loc in target_locations:
        if loc.lower() in combined:
            score += 0.2
            match_reasons.append(f"location: {loc}")
            break

    # Base score for existing on a monitored board
    score += 0.3

    return min(score, 1.0), match_reasons


def fetch_board(url, search_terms, interests):
    """Fetch job listings from a single board URL."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Generic extraction: look for common job listing patterns
            jobs = []
            # Try common selectors
            for selector in ["article", ".job-listing", ".job-card", ".posting", "li.result"]:
                elements = soup.select(selector)
                if elements:
                    for el in elements[:20]:
                        title_el = el.find(["h2", "h3", "a"])
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

                        text = el.get_text(" ", strip=True)
                        score, reasons = compute_match_score(title, text, interests)

                        jobs.append({
                            "title": title,
                            "company": "",
                            "location": "",
                            "url": link if link.startswith("http") else "",
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

    all_jobs = []
    for board in job_boards:
        url = board.get("url", "")
        search_terms = board.get("search_terms", [])
        if not url:
            continue

        print(f"Fetching jobs: {url}")
        jobs = fetch_board(url, search_terms, interests)
        all_jobs.extend(jobs)
        time.sleep(2)  # Rate limiting

    # Sort by match score (highest first)
    all_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_jobs, f, indent=2)

    print(f"Fetched {len(all_jobs)} jobs from {len(job_boards)} boards → {args.output}")


if __name__ == "__main__":
    main()
