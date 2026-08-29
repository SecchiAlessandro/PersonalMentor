#!/usr/bin/env python3
"""Ingest feedback submitted as GitHub Issues and append to feedback.jsonl.

When the local feedback server is unreachable (e.g. GitHub Pages), the
newspaper template falls back to opening a pre-filled GitHub Issue with
the `feedback` label.  This script fetches those issues, parses the
structured body back into feedback.jsonl entries, and closes them.
"""

import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
FEEDBACK_FILE = os.path.join(PROJECT_ROOT, "memory", "feedback.jsonl")
LOG_ACTION = os.path.join(PROJECT_ROOT, "skills", "memory-manager", "scripts", "log_action.py")
REPO = "SecchiAlessandro/PersonalMentor"


def gh_available():
    """Check if the gh CLI is installed and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def fetch_open_feedback_issues():
    """Return a list of open feedback issues (by label OR title prefix)."""
    # Fetch by label
    by_label = subprocess.run(
        [
            "gh", "issue", "list",
            "--repo", REPO,
            "--label", "feedback",
            "--state", "open",
            "--json", "number,title,body,createdAt",
        ],
        capture_output=True, text=True, timeout=30,
    )
    # Fetch by title search
    by_title = subprocess.run(
        [
            "gh", "issue", "list",
            "--repo", REPO,
            "--search", "Feedback: in:title",
            "--state", "open",
            "--json", "number,title,body,createdAt",
        ],
        capture_output=True, text=True, timeout=30,
    )
    # Merge and deduplicate by issue number
    seen = {}
    for result in (by_label, by_title):
        if result.returncode != 0:
            continue
        for issue in json.loads(result.stdout):
            seen[issue["number"]] = issue
    if not seen and by_label.returncode != 0 and by_title.returncode != 0:
        print(f"  WARNING: gh issue list failed: {by_label.stderr.strip()}")
    return list(seen.values())


# Placeholder the newspaper writes when the reader submitted votes but no text.
NO_COMMENT = "(no comment)"

# One voted item: "- like | news | energy | canarymedia.com | Headline text"
VOTE_LINE_RE = re.compile(
    r"-\s*(like|dislike)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|(.*)"
)


def split_sections(body):
    """Split an issue body into {heading: text} for its '### ' headings.

    Splitting on the headings is more robust than one regex per field: the body
    gained an "Item votes" section after "Comment", and a greedy comment regex
    would otherwise swallow it whole.
    """
    sections = {}
    current = None
    for line in body.splitlines():
        heading = re.match(r"###\s+(.*?)\s*$", line)
        if heading:
            current = heading.group(1).lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def parse_issue(issue):
    """Parse a GitHub Issue body into a feedback.jsonl entry.

    Expected body format (from template.html):
        ## Daily Newspaper Feedback

        **Date:** YYYY-MM-DD

        ### Comment
        Free-form text (or "(no comment)" when only items were voted on)

        ### Item votes
        - like | news | energy | canarymedia.com | Headline text
        - dislike | events | ai | meetup.com | Event title

    Older issues also carried "**Overall rating:** N/5" and a "Section ratings"
    list; those are still parsed so historical issues keep ingesting cleanly.
    """
    body = issue.get("body", "")
    title = issue.get("title", "")
    sections = split_sections(body)

    # Extract date from title "Feedback: YYYY-MM-DD"
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    date = date_match.group(1) if date_match else None

    # Extract overall rating (legacy issues only)
    rating_match = re.search(r"\*\*Overall rating:\*\*\s*(\d+)/5", body)
    rating = int(rating_match.group(1)) if rating_match else None

    # Extract section ratings (legacy issues only)
    section_ratings = {}
    for m in re.finditer(r"-\s*\*\*(\w+):\*\*\s*(\d+)/5", body):
        section_ratings[m.group(1)] = int(m.group(2))

    comment = sections.get("comment", "")
    if comment == NO_COMMENT:
        comment = ""

    # Extract per-item 👍/👎 votes
    item_votes = []
    for line in sections.get("item votes", "").splitlines():
        m = VOTE_LINE_RE.match(line.strip())
        if not m:
            continue
        item_votes.append({
            "vote": m.group(1),
            "section": m.group(2).strip(),
            "track": m.group(3).strip(),
            "source": m.group(4).strip(),
            "title": m.group(5).strip(),
        })

    # Validate minimum fields — an entry needs something to learn from.
    if date is None and rating is None and not comment and not item_votes:
        return None

    return {
        "timestamp": issue.get("createdAt", ""),
        "date": date or "",
        "rating": rating,
        "section_ratings": section_ratings,
        "comment": comment,
        "item_votes": item_votes,
    }


def append_entry(entry):
    """Append a feedback entry to feedback.jsonl."""
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    with open(FEEDBACK_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def close_issue(number):
    """Close a processed GitHub Issue."""
    subprocess.run(
        ["gh", "issue", "close", str(number), "--repo", REPO],
        capture_output=True, timeout=15,
    )


def log_action(detail):
    """Log via log_action.py (best-effort)."""
    try:
        subprocess.run(
            [sys.executable, LOG_ACTION, "--action", "feedback_received", "--detail", detail],
            capture_output=True, timeout=5,
        )
    except Exception:
        pass


def main():
    if not gh_available():
        print("  gh CLI not available or not authenticated — skipping GitHub feedback ingestion.")
        return

    issues = fetch_open_feedback_issues()
    if not issues:
        print("  No open feedback issues found.")
        return

    ingested = 0
    for issue in issues:
        number = issue["number"]
        entry = parse_issue(issue)
        if entry is None:
            print(f"  WARNING: Skipping malformed issue #{number}")
            continue

        append_entry(entry)
        close_issue(number)
        ingested += 1

        votes = entry["item_votes"]
        parts = []
        if entry["comment"]:
            parts.append("comment")
        if votes:
            likes = sum(1 for v in votes if v["vote"] == "like")
            parts.append(f"{likes} like / {len(votes) - likes} dislike")
        summary = ", ".join(parts) or "no content"
        print(f"  Ingested issue #{number}: {summary} for {entry['date']}")
        log_action(f"GitHub issue #{number}: {summary} for {entry['date']}")

    print(f"  Ingested {ingested} feedback issue(s).")


if __name__ == "__main__":
    main()
