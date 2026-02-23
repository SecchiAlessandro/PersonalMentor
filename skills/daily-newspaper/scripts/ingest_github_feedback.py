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
    """Return a list of open issues with the 'feedback' label."""
    result = subprocess.run(
        [
            "gh", "issue", "list",
            "--repo", REPO,
            "--label", "feedback",
            "--state", "open",
            "--json", "number,title,body,createdAt",
        ],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"  WARNING: gh issue list failed: {result.stderr.strip()}")
        return []
    return json.loads(result.stdout)


def parse_issue(issue):
    """Parse a GitHub Issue body into a feedback.jsonl entry.

    Expected body format (from template.html):
        ## Daily Newspaper Feedback

        **Date:** YYYY-MM-DD
        **Overall rating:** N/5

        ### Section ratings
        - **news:** N/5
        - **jobs:** N/5
        ...

        ### Comment
        Free-form text
    """
    body = issue.get("body", "")
    title = issue.get("title", "")

    # Extract date from title "Feedback: YYYY-MM-DD"
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", title)
    date = date_match.group(1) if date_match else None

    # Extract overall rating
    rating_match = re.search(r"\*\*Overall rating:\*\*\s*(\d+)/5", body)
    rating = int(rating_match.group(1)) if rating_match else None

    # Extract section ratings
    section_ratings = {}
    for m in re.finditer(r"-\s*\*\*(\w+):\*\*\s*(\d+)/5", body):
        section_ratings[m.group(1)] = int(m.group(2))

    # Extract comment (everything after "### Comment")
    comment = ""
    comment_match = re.search(r"###\s*Comment\s*\n(.*)", body, re.DOTALL)
    if comment_match:
        comment = comment_match.group(1).strip()

    # Validate minimum fields
    if date is None and rating is None:
        return None

    return {
        "timestamp": issue.get("createdAt", ""),
        "date": date or "",
        "rating": rating,
        "section_ratings": section_ratings,
        "comment": comment,
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

        rating_str = f"{entry['rating']}/5" if entry['rating'] else "no rating"
        print(f"  Ingested issue #{number}: {rating_str} for {entry['date']}")
        log_action(f"GitHub issue #{number}: {rating_str} for {entry['date']}")

    print(f"  Ingested {ingested} feedback issue(s).")


if __name__ == "__main__":
    main()
