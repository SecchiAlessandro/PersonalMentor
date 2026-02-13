#!/usr/bin/env python3
"""Append an action to the PersonalMentor session log."""

import argparse
import json
import os
import uuid
from datetime import datetime, timezone

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memory")
SESSION_LOG = os.path.join(MEMORY_DIR, "session-log.jsonl")

VALID_ACTIONS = [
    "onboarding",
    "profile_update",
    "artifact_generated",
    "preference_learned",
    "source_added",
    "feedback_received",
]


def main():
    parser = argparse.ArgumentParser(description="Log an action to session-log.jsonl")
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS, help="Action type")
    parser.add_argument("--detail", required=True, help="Description of the action")
    parser.add_argument("--session-id", default=None, help="Session UUID (auto-generated if omitted)")
    args = parser.parse_args()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": args.action,
        "detail": args.detail,
        "session_id": args.session_id or str(uuid.uuid4())[:8],
    }

    os.makedirs(os.path.dirname(SESSION_LOG), exist_ok=True)
    with open(SESSION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Logged: {entry['action']} — {entry['detail']}")


if __name__ == "__main__":
    main()
