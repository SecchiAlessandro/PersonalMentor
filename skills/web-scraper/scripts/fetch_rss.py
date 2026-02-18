#!/usr/bin/env python3
"""Fetch and parse RSS/Atom feeds from configured sources."""

import argparse
import json
import os
import sys
import time

try:
    import feedparser
except ImportError:
    print("ERROR: feedparser not installed. Run: pip install feedparser")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_SUMMARY_LENGTH = 200


def fetch_feed(url, category="general"):
    """Fetch a single RSS feed with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                raise Exception(f"Feed parse error: {feed.bozo_exception}")
            articles = []
            for entry in feed.entries:
                summary = entry.get("summary", entry.get("description", ""))
                # Strip HTML tags from summary
                if summary:
                    import re
                    summary = re.sub(r"<[^>]+>", "", summary)
                    summary = summary[:MAX_SUMMARY_LENGTH].strip()

                articles.append({
                    "title": entry.get("title", "Untitled"),
                    "url": entry.get("link", ""),
                    "source": feed.feed.get("title", url),
                    "category": category,
                    "published": entry.get("published", ""),
                    "summary": summary,
                })
            return articles
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch {url}: {e}", file=sys.stderr)
                return []


def main():
    parser = argparse.ArgumentParser(description="Fetch RSS feeds from configured sources")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--max-per-feed", type=int, default=10, help="Max articles per feed")
    args = parser.parse_args()

    # Load sources config
    with open(args.config, "r") as f:
        sources = yaml.safe_load(f) or {}

    rss_feeds = sources.get("rss_feeds") or []
    if not rss_feeds:
        print("No RSS feeds configured in sources.yaml")
        with open(args.output, "w") as f:
            json.dump([], f)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(feed_config):
        url = feed_config.get("url", "")
        category = feed_config.get("category", "general")
        if not url:
            return []
        print(f"Fetching: {url} ({category})")
        return fetch_feed(url, category)[:args.max_per_feed]

    all_articles = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_one, fc): fc for fc in rss_feeds}
        for fut in as_completed(futures):
            try:
                all_articles.extend(fut.result())
            except Exception as e:
                print(f"WARNING: feed fetch error: {e}", file=sys.stderr)

    # Sort by published date (newest first)
    all_articles.sort(key=lambda x: x.get("published", ""), reverse=True)

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(all_articles, f, indent=2)

    print(f"Fetched {len(all_articles)} articles from {len(rss_feeds)} feeds → {args.output}")


if __name__ == "__main__":
    main()
