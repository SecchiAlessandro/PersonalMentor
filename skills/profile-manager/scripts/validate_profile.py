#!/usr/bin/env python3
"""Validate all profile YAML files for correct structure and syntax."""

import sys
import os

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

PROFILE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "profile")

REQUIRED_FILES = {
    "identity.yaml": {
        "required_keys": ["name", "title", "location", "bio", "contact"],
        "contact_keys": ["email", "linkedin", "website", "github"],
    },
    "experience.yaml": {
        "required_keys": ["work_history", "education", "projects", "skills"],
    },
    "interests.yaml": {
        "required_keys": ["professional", "industries", "personal", "job_search"],
    },
    "preferences.yaml": {
        "required_keys": ["design", "writing", "daily_artifact"],
    },
    "sources.yaml": {
        "required_keys": ["rss_feeds", "job_boards", "event_sources"],
    },
}


def validate_file(filename, schema):
    filepath = os.path.join(PROFILE_DIR, filename)
    if not os.path.exists(filepath):
        return [f"MISSING: {filename} does not exist"]

    errors = []
    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML SYNTAX ERROR in {filename}: {e}"]

    if data is None:
        return [f"EMPTY: {filename} is empty or contains only comments"]

    for key in schema.get("required_keys", []):
        if key not in data:
            errors.append(f"{filename}: missing required key '{key}'")

    if "contact_keys" in schema and "contact" in data and isinstance(data["contact"], dict):
        for key in schema["contact_keys"]:
            if key not in data["contact"]:
                errors.append(f"{filename}: missing contact key '{key}'")

    return errors


def main():
    print("Validating PersonalMentor profile...")
    print(f"Profile directory: {os.path.abspath(PROFILE_DIR)}")
    print()

    all_errors = []
    for filename, schema in REQUIRED_FILES.items():
        errors = validate_file(filename, schema)
        if errors:
            all_errors.extend(errors)
            print(f"  FAIL  {filename}")
            for err in errors:
                print(f"        {err}")
        else:
            print(f"  OK    {filename}")

    print()
    if all_errors:
        print(f"Validation failed with {len(all_errors)} error(s).")
        sys.exit(1)
    else:
        print("All profile files are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
