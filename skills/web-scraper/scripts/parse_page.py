#!/usr/bin/env python3
"""Parse a web page and extract structured content."""

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

MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

HEADERS = {
    "User-Agent": "PersonalMentor/1.0 (profile-builder)"
}


def parse_page(url):
    """Fetch and parse a web page into structured data."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)

            # Extract meta description
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Extract headings
            headings = []
            for tag in ["h1", "h2", "h3"]:
                for el in soup.find_all(tag):
                    text = el.get_text(strip=True)
                    if text:
                        headings.append(text)

            # Extract paragraphs
            paragraphs = []
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    paragraphs.append(text)

            # Extract links
            links = []
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                href = a["href"]
                if text and href.startswith("http"):
                    links.append({"text": text, "href": href})

            # Extract images
            images = []
            for img in soup.find_all("img"):
                alt = img.get("alt", "")
                src = img.get("src", "")
                if src:
                    images.append({"alt": alt, "src": src})

            return {
                "url": url,
                "title": title,
                "description": description,
                "headings": headings,
                "paragraphs": paragraphs[:50],
                "links": links[:30],
                "images": images[:20],
            }

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                print(f"ERROR: Failed to fetch {url}: {e}", file=sys.stderr)
                return {"url": url, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Parse a web page into structured data")
    parser.add_argument("--url", required=True, help="URL to parse")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    print(f"Parsing: {args.url}")
    data = parse_page(args.url)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Extracted: {len(data.get('headings', []))} headings, "
          f"{len(data.get('paragraphs', []))} paragraphs, "
          f"{len(data.get('links', []))} links → {args.output}")


if __name__ == "__main__":
    main()
