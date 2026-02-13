#!/usr/bin/env python3
"""Register a generated artifact in the PersonalMentor artifact registry."""

import argparse
import os
import uuid
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    exit(1)

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "memory")
ARTIFACTS_FILE = os.path.join(MEMORY_DIR, "artifacts.yaml")


def main():
    parser = argparse.ArgumentParser(description="Register a generated artifact")
    parser.add_argument("--type", required=True, help="Artifact type (daily-newspaper, cv, document, web)")
    parser.add_argument("--path", required=True, help="Output file path relative to project root")
    parser.add_argument("--sections", default="", help="Comma-separated list of sections included")
    parser.add_argument("--item-count", type=int, default=0, help="Number of content items")
    parser.add_argument("--sources", default="", help="Comma-separated list of sources used")
    args = parser.parse_args()

    # Load existing registry
    if os.path.exists(ARTIFACTS_FILE):
        with open(ARTIFACTS_FILE, "r") as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    if "artifacts" not in data or data["artifacts"] is None:
        data["artifacts"] = []

    # Create new artifact entry
    artifact = {
        "id": str(uuid.uuid4())[:8],
        "type": args.type,
        "path": args.path,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sections": [s.strip() for s in args.sections.split(",") if s.strip()],
        "item_count": args.item_count,
        "sources_used": [s.strip() for s in args.sources.split(",") if s.strip()],
    }

    data["artifacts"].append(artifact)

    # Write back
    with open(ARTIFACTS_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    print(f"Registered artifact: {artifact['id']} ({artifact['type']}) → {artifact['path']}")


if __name__ == "__main__":
    main()
