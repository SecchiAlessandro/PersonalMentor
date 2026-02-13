#!/usr/bin/env python3
"""Analyze session logs and update learned preferences."""

import json
import os
from collections import Counter
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    exit(1)

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memory")
SESSION_LOG = os.path.join(MEMORY_DIR, "session-log.jsonl")
LEARNED_PREFS = os.path.join(MEMORY_DIR, "learned-preferences.yaml")


def load_session_log():
    """Read all entries from session-log.jsonl."""
    entries = []
    if not os.path.exists(SESSION_LOG):
        return entries
    with open(SESSION_LOG, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def analyze_logs(entries):
    """Extract preference signals from log entries."""
    action_counts = Counter()
    feedback_entries = []

    for entry in entries:
        action_counts[entry.get("action", "unknown")] += 1
        if entry.get("action") == "feedback_received":
            feedback_entries.append(entry.get("detail", ""))

    return {
        "action_counts": dict(action_counts),
        "feedback_entries": feedback_entries,
        "total_sessions": len(set(e.get("session_id", "") for e in entries)),
        "total_artifacts": action_counts.get("artifact_generated", 0),
    }


def main():
    entries = load_session_log()
    if not entries:
        print("No session log entries found. Nothing to analyze.")
        return

    analysis = analyze_logs(entries)

    # Load existing preferences
    if os.path.exists(LEARNED_PREFS):
        with open(LEARNED_PREFS, "r") as f:
            prefs = yaml.safe_load(f) or {}
    else:
        prefs = {}

    # Ensure structure exists
    prefs.setdefault("content_preferences", {})
    prefs.setdefault("design_preferences", {})
    prefs.setdefault("reading_patterns", {})

    # Update with analysis
    prefs["reading_patterns"]["total_artifacts"] = analysis["total_artifacts"]
    prefs["reading_patterns"]["total_sessions"] = analysis["total_sessions"]
    prefs["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Write back
    with open(LEARNED_PREFS, "w") as f:
        yaml.dump(prefs, f, default_flow_style=False, sort_keys=False)

    print(f"Updated learned preferences from {len(entries)} log entries.")
    print(f"  Sessions: {analysis['total_sessions']}")
    print(f"  Artifacts generated: {analysis['total_artifacts']}")
    print(f"  Feedback entries: {len(analysis['feedback_entries'])}")


if __name__ == "__main__":
    main()
