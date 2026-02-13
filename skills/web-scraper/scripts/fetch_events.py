#!/usr/bin/env python3
"""Fetch events from configured event sources."""

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
    "User-Agent": "PersonalMentor/1.0 (event-aggregator)"
}


def fetch_event_source(url, location_filter=""):
    """Fetch events from a single source URL."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            events = []
            # Try common event page selectors
            for selector in [".event-card", ".event", "article", ".listing", "[data-event]"]:
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
                            link = a_tag.get("href", "")

                        # Try to find date
                        date_el = el.find(["time", ".date", ".event-date"])
                        date_str = ""
                        if date_el:
                            date_str = date_el.get("datetime", date_el.get_text(strip=True))

                        # Try to find location
                        loc_el = el.find([".location", ".venue", "address"])
                        location = loc_el.get_text(strip=True) if loc_el else ""

                        events.append({
                            "title": title,
                            "date": date_str,
                            "location": location or "TBD",
                            "url": link if link.startswith("http") else "",
                            "source": url,
                            "type": "event",
                        })
                    break

            return events
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

    all_events = []
    for source in event_sources:
        url = source.get("url", "")
        location_filter = source.get("location_filter", "")
        if not url:
            continue

        print(f"Fetching events: {url}")
        events = fetch_event_source(url, location_filter)
        all_events.extend(events)
        time.sleep(2)  # Rate limiting

    # Sort by date
    all_events.sort(key=lambda x: x.get("date", ""))

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_events, f, indent=2)

    print(f"Fetched {len(all_events)} events from {len(event_sources)} sources → {args.output}")


if __name__ == "__main__":
    main()
