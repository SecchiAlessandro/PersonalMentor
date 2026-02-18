#!/usr/bin/env python3
"""Analyze accumulated feedback and update learned-preferences.yaml.

Reads memory/feedback.jsonl, computes per-section averages and overall rating,
then writes adjustments to memory/learned-preferences.yaml so the next newspaper
render reflects user preferences.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
FEEDBACK_FILE = os.path.join(PROJECT_ROOT, "memory", "feedback.jsonl")
PREFS_FILE = os.path.join(PROJECT_ROOT, "memory", "learned-preferences.yaml")

# Default item counts per section
DEFAULT_ITEM_COUNT = 3
MIN_ITEM_COUNT = 2
MAX_ITEM_COUNT = 7

# Thresholds
HIGH_RATING_THRESHOLD = 4.0  # sections rated >= this get more items
LOW_RATING_THRESHOLD = 2.0   # sections rated <= this get fewer items

ALL_SECTIONS = ["news", "jobs", "events", "calendar", "german"]


def load_feedback():
    """Load all feedback entries from JSONL file."""
    entries = []
    if not os.path.exists(FEEDBACK_FILE):
        return entries
    with open(FEEDBACK_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def load_prefs():
    """Load existing learned-preferences.yaml."""
    if not os.path.exists(PREFS_FILE):
        return {}
    with open(PREFS_FILE, "r") as f:
        return yaml.safe_load(f) or {}


def compute_averages(entries):
    """Compute per-section and overall averages from feedback entries."""
    section_totals = defaultdict(list)
    overall_ratings = []

    for entry in entries:
        rating = entry.get("rating")
        if rating is not None:
            overall_ratings.append(float(rating))

        section_ratings = entry.get("section_ratings", {})
        for section, value in section_ratings.items():
            if value is not None:
                section_totals[section].append(float(value))

    section_avgs = {}
    for section, values in section_totals.items():
        section_avgs[section] = round(sum(values) / len(values), 2)

    overall_avg = round(sum(overall_ratings) / len(overall_ratings), 2) if overall_ratings else None

    return overall_avg, section_avgs


def determine_item_counts(section_avgs):
    """Determine per-section item counts based on average ratings."""
    counts = {}
    for section in ALL_SECTIONS:
        avg = section_avgs.get(section)
        if avg is None:
            counts[section] = DEFAULT_ITEM_COUNT
        elif avg >= HIGH_RATING_THRESHOLD:
            # Scale: 4.0 -> 4 items, 5.0 -> 5 items
            counts[section] = min(MAX_ITEM_COUNT, DEFAULT_ITEM_COUNT + int(avg - 3))
        elif avg <= LOW_RATING_THRESHOLD:
            # Scale: 2.0 -> 2 items, 1.0 -> 1 item
            counts[section] = max(MIN_ITEM_COUNT, int(avg))
        else:
            counts[section] = DEFAULT_ITEM_COUNT
    return counts


def determine_section_preferences(section_avgs):
    """Determine preferred and skipped sections."""
    preferred = []
    skipped = []
    for section, avg in section_avgs.items():
        if avg >= HIGH_RATING_THRESHOLD:
            preferred.append(section)
        elif avg <= LOW_RATING_THRESHOLD:
            skipped.append(section)
    return sorted(preferred), sorted(skipped)


def update_preferences(entries, overall_avg, section_avgs):
    """Update learned-preferences.yaml with computed values."""
    prefs = load_prefs()

    item_counts = determine_item_counts(section_avgs)
    preferred, skipped = determine_section_preferences(section_avgs)

    # Update content_preferences (preserve existing liked/disliked topics)
    if "content_preferences" not in prefs:
        prefs["content_preferences"] = {}
    cp = prefs["content_preferences"]
    cp.setdefault("liked_topics", [])
    cp.setdefault("disliked_topics", [])
    cp.setdefault("preferred_sources", [])
    cp.setdefault("ignored_sources", [])

    # Update reading_patterns
    if "reading_patterns" not in prefs:
        prefs["reading_patterns"] = {}
    rp = prefs["reading_patterns"]
    rp["preferred_sections"] = preferred
    rp["skipped_sections"] = skipped
    rp["section_item_counts"] = item_counts

    # Update feedback stats
    if overall_avg is not None:
        prefs["overall_avg_rating"] = overall_avg
    prefs["total_feedback_count"] = len(entries)
    prefs["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Write back
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
    with open(PREFS_FILE, "w") as f:
        yaml.dump(prefs, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return prefs


def main():
    entries = load_feedback()

    if not entries:
        print("No feedback entries found. Nothing to analyze.")
        return

    overall_avg, section_avgs = compute_averages(entries)

    print(f"Analyzing {len(entries)} feedback entries...")
    if overall_avg is not None:
        print(f"  Overall average rating: {overall_avg}/5")
    for section, avg in sorted(section_avgs.items()):
        print(f"  {section}: {avg}/5")

    prefs = update_preferences(entries, overall_avg, section_avgs)

    item_counts = prefs.get("reading_patterns", {}).get("section_item_counts", {})
    print(f"\nUpdated {PREFS_FILE}")
    print(f"  Section item counts: {item_counts}")
    print(f"  Preferred sections: {prefs.get('reading_patterns', {}).get('preferred_sections', [])}")
    print(f"  Skipped sections: {prefs.get('reading_patterns', {}).get('skipped_sections', [])}")


if __name__ == "__main__":
    main()
