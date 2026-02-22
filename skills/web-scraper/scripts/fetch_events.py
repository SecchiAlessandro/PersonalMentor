#!/usr/bin/env python3
"""Fetch events from configured event sources."""

import argparse
import json
import os
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
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def extract_jsonld_events(soup, source_url):
    """Extract events from JSON-LD structured data (schema.org Event type)."""
    events = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if data.get("@type") == "Event":
                items = [data]
            elif "@graph" in data:
                items = data["@graph"]
            elif "itemListElement" in data:
                items = [e.get("item", e) for e in data["itemListElement"]]

        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if item_type != "Event" and "Event" not in str(item_type):
                continue

            title = item.get("name", "")
            if not title:
                continue

            start = item.get("startDate", "")
            loc = item.get("location", {})
            if isinstance(loc, dict):
                location = loc.get("name", loc.get("address", ""))
                if isinstance(location, dict):
                    location = location.get("addressLocality", "")
            elif isinstance(loc, str):
                location = loc
            else:
                location = ""

            url = item.get("url", source_url)

            events.append({
                "title": title,
                "date": start[:10] if start else "",
                "location": location or "TBD",
                "url": url,
                "source": source_url,
                "type": "conference",
            })

    return events


def extract_wikicfp_events(soup, source_url):
    """Extract events from WikiCFP table format (pairs of rows)."""
    events = []
    # Find the table with Event/When/Where/Deadline headers
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        # Look for header row
        header_found = False
        for i, row in enumerate(rows):
            cells = row.find_all(["td", "th"])
            texts = [c.get_text(strip=True) for c in cells]
            if "Event" in texts and "When" in texts:
                header_found = True
                continue
            if not header_found:
                continue

            # WikiCFP alternates: name row, then date/location row
            if len(cells) >= 2:
                a_tag = row.find("a")
                if a_tag and a_tag.get("href", "").startswith("/cfp/"):
                    # This is a name row
                    title = cells[0].get_text(strip=True)
                    full_title = cells[1].get_text(strip=True) if len(cells) > 1 else title
                    link = urljoin(source_url, a_tag.get("href", ""))

                    # Next row should have When/Where/Deadline
                    if i + 1 < len(rows):
                        next_cells = rows[i + 1].find_all("td")
                        when = next_cells[0].get_text(strip=True) if len(next_cells) > 0 else ""
                        where = next_cells[1].get_text(strip=True) if len(next_cells) > 1 else ""

                        if when == "N/A" and where == "N/A":
                            continue  # Skip journals

                        events.append({
                            "title": f"{title} — {full_title}" if full_title != title else title,
                            "date": when,
                            "location": where or "TBD",
                            "url": link,
                            "source": source_url,
                            "type": "conference",
                        })
        if events:
            break

    return events


def extract_html_events(soup, source_url):
    """Extract events from HTML using CSS selectors."""
    # Try WikiCFP table format first
    if "wikicfp.com" in source_url:
        events = extract_wikicfp_events(soup, source_url)
        if events:
            return events

    events = []
    selectors = [
        ".event-card", ".event-name", ".event",
        ".border-primary", ".listing-item", ".listing",
        "article", "[data-event]",
    ]
    for selector in selectors:
        elements = soup.select(selector)
        if elements:
            for el in elements[:20]:
                title_el = el.find(["h2", "h3", "a", "h4"])
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                link = ""
                a_tag = el.find("a")
                if a_tag:
                    href = a_tag.get("href", "")
                    link = href if href.startswith("http") else urljoin(source_url, href)

                date_str = ""
                for date_sel in ["time", ".date", ".event-date", "[class*='date']"]:
                    date_el = el.select_one(date_sel)
                    if date_el:
                        date_str = date_el.get("datetime", date_el.get_text(strip=True))
                        break

                location = ""
                for loc_sel in [".location", ".venue", "address", "[class*='location']"]:
                    loc_el = el.select_one(loc_sel)
                    if loc_el:
                        location = loc_el.get_text(strip=True)
                        break

                events.append({
                    "title": title,
                    "date": date_str,
                    "location": location or "TBD",
                    "url": link,
                    "source": source_url,
                    "type": "conference",
                })
            break

    return events


def fetch_api_events(url, location_filter=""):
    """Fetch events from a JSON API (e.g. Luma, custom APIs)."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            raw = data if isinstance(data, list) else data.get("events", data.get("data", []))
            events = []
            for item in raw:
                title = item.get("name", item.get("title", ""))
                if not title:
                    continue
                events.append({
                    "title": title,
                    "date": item.get("start_at", item.get("date", ""))[:10],
                    "location": item.get("geo_address_info", {}).get("city", item.get("location", "TBD")),
                    "url": item.get("url", ""),
                    "source": url,
                    "type": "event",
                })
            return events
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch API {url}: {e}", file=sys.stderr)
                return []


def fetch_event_source(url, location_filter=""):
    """Fetch events from a single source URL (HTML + JSON-LD)."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Try JSON-LD first (works even on JS-rendered pages)
            events = extract_jsonld_events(soup, url)
            if events:
                return events

            # Fall back to HTML scraping
            return extract_html_events(soup, url)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch {url}: {e}", file=sys.stderr)
                return []


def main():
    parser = argparse.ArgumentParser(description="Fetch events from configured sources")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        sources = yaml.safe_load(f) or {}

    event_sources = sources.get("event_sources") or []
    if not event_sources:
        print("No event sources configured in sources.yaml")
        with open(args.output, "w") as f:
            json.dump([], f)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(source):
        url = source.get("url", "")
        location_filter = source.get("location_filter", "")
        source_type = source.get("type", "html")
        if not url:
            return []
        print(f"Fetching events ({source_type}): {url}")
        if source_type == "api":
            return fetch_api_events(url, location_filter)
        else:
            return fetch_event_source(url, location_filter)

    all_events = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_one, s): s for s in event_sources}
        for fut in as_completed(futures):
            source = futures[fut]
            location_filter = source.get("location_filter", "").strip().lower()
            try:
                events = fut.result()
                if location_filter:
                    before = len(events)
                    events = [
                        e for e in events
                        if location_filter in e.get("location", "").lower()
                    ]
                    print(f"  Location filter '{location_filter}': {before} → {len(events)} events")
                all_events.extend(events)
            except Exception as e:
                print(f"WARNING: event fetch error: {e}", file=sys.stderr)

    # Sort by date
    all_events.sort(key=lambda x: x.get("date", ""))

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_events, f, indent=2)

    print(f"Fetched {len(all_events)} events from {len(event_sources)} sources → {args.output}")


if __name__ == "__main__":
    main()
