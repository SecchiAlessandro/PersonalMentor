#!/usr/bin/env python3
"""Fetch and parse RSS/Atom feeds (and HTML news pages) from configured sources."""

import argparse
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

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

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

# Use OS certificate store (fixes corporate proxy SSL errors on Windows)
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

MAX_RETRIES = 3
RETRY_DELAY = 2
MAX_SUMMARY_LENGTH = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


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


def fetch_html_articles(url, category="general"):
    """Scrape news/article links from an HTML page with retries."""
    if requests is None or BeautifulSoup is None:
        print("WARNING: requests/beautifulsoup4 not installed, skipping HTML source", file=sys.stderr)
        return []

    for attempt in range(MAX_RETRIES):
        try:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
            except requests.exceptions.SSLError:
                # Retry without SSL verification (corporate proxies, etc.)
                resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Derive a human-friendly source name from the domain
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            source_name = domain.split(".")[0].title()

            articles = []
            seen_urls = set()

            # Strategy 1: JSON-LD structured data (NewsArticle, Article, etc.)
            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string)
                except (json.JSONDecodeError, TypeError):
                    continue
                items = data if isinstance(data, list) else [data]
                if isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    itype = str(item.get("@type", ""))
                    if "Article" not in itype and "News" not in itype:
                        continue
                    title = item.get("headline", item.get("name", ""))
                    link = item.get("url", "")
                    if title and link and link not in seen_urls:
                        seen_urls.add(link)
                        summary = item.get("description", "")
                        if summary:
                            summary = re.sub(r"<[^>]+>", "", summary)[:MAX_SUMMARY_LENGTH].strip()
                        articles.append({
                            "title": title,
                            "url": link,
                            "source": source_name,
                            "category": category,
                            "published": item.get("datePublished", ""),
                            "summary": summary,
                        })

            if articles:
                return articles

            # Strategy 2: <article> elements or common card patterns
            containers = soup.select("article, .story, .card, .teaser, .news-item, .post, .entry")
            for el in containers:
                a_tag = el.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag["href"]
                link = href if href.startswith("http") else urljoin(url, href)
                if link in seen_urls:
                    continue

                title_el = el.find(["h1", "h2", "h3", "h4"])
                title = title_el.get_text(strip=True) if title_el else a_tag.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                seen_urls.add(link)
                summary = ""
                p = el.find("p")
                if p:
                    summary = re.sub(r"<[^>]+>", "", p.get_text(strip=True))[:MAX_SUMMARY_LENGTH]

                date_el = el.find("time")
                published = date_el.get("datetime", date_el.get_text(strip=True)) if date_el else ""

                articles.append({
                    "title": title,
                    "url": link,
                    "source": source_name,
                    "category": category,
                    "published": published,
                    "summary": summary,
                })

            if articles:
                return articles

            # Strategy 3: fallback — collect prominent <a> links with long text
            for a_tag in soup.find_all("a", href=True):
                text = a_tag.get_text(strip=True)
                href = a_tag["href"]
                if len(text) < 15 or not href:
                    continue
                link = href if href.startswith("http") else urljoin(url, href)
                if link in seen_urls or link == url:
                    continue
                # Skip navigation/footer links
                if any(skip in text.lower() for skip in ["sign in", "subscribe", "log in", "cookie", "privacy"]):
                    continue
                seen_urls.add(link)
                articles.append({
                    "title": text[:120],
                    "url": link,
                    "source": source_name,
                    "category": category,
                    "published": "",
                    "summary": "",
                })

            return articles
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"WARNING: Failed to fetch HTML {url}: {e}", file=sys.stderr)
                return []


def main():
    parser = argparse.ArgumentParser(description="Fetch RSS feeds from configured sources")
    parser.add_argument("--config", required=True, help="Path to sources.yaml")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--max-per-feed", type=int, default=10, help="Max articles per feed")
    args = parser.parse_args()

    # Load sources config
    with open(args.config, "r", encoding="utf-8") as f:
        sources = yaml.safe_load(f) or {}

    rss_feeds = sources.get("rss_feeds") or []
    if not rss_feeds:
        print("No RSS feeds configured in sources.yaml")
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump([], f)
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _fetch_one(feed_config):
        url = feed_config.get("url", "")
        category = feed_config.get("category", "general")
        feed_type = feed_config.get("type", "rss")
        if not url:
            return []
        print(f"Fetching ({feed_type}): {url} ({category})")
        if feed_type == "html":
            return fetch_html_articles(url, category)[:args.max_per_feed]
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
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, indent=2)

    print(f"Fetched {len(all_articles)} articles from {len(rss_feeds)} feeds → {args.output}")


if __name__ == "__main__":
    main()
