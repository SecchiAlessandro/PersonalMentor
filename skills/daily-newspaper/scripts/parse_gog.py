#!/usr/bin/env python3
"""Parse gog CLI JSON output into the format render_newspaper.py expects.

Calendar events  -> [{time, title}]
Contacts/birthdays -> [{name, note}]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta


def parse_calendar(input_path, output_path):
    """Convert gog calendar JSON to [{time, title}]."""
    if not os.path.exists(input_path):
        print(f"No calendar file at {input_path}, skipping.")
        return

    with open(input_path, "r") as f:
        raw = json.load(f)

    events = []
    items = raw if isinstance(raw, list) else raw.get("events", raw.get("items", []))
    for item in items:
        # Skip cancelled events
        if item.get("status") == "cancelled":
            continue

        # gog outputs start.dateTime or start.date
        start = item.get("start", {})
        date_time = start.get("dateTime", "")
        date_only = start.get("date", "")

        if date_time and "T" in date_time:
            try:
                dt = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
                time_str = dt.strftime("%a %d %b %H:%M")
            except ValueError:
                time_str = date_time
        elif date_only:
            try:
                dt = datetime.strptime(date_only, "%Y-%m-%d")
                time_str = dt.strftime("%a %d %b")
            except ValueError:
                time_str = date_only
        else:
            time_str = ""

        title = item.get("summary", item.get("title", "Untitled"))
        events.append({"time": time_str, "title": title})

    # Sort by time
    events.sort(key=lambda e: e["time"])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(events, f, indent=2)
    print(f"Parsed {len(events)} calendar events -> {output_path}")


def parse_contacts(input_path, output_path, calendar_path=""):
    """Extract birthdays from calendar events and contacts."""
    birthdays = []

    # Method 1: Extract birthday events from the calendar JSON (most reliable)
    if calendar_path and os.path.exists(calendar_path):
        with open(calendar_path, "r") as f:
            cal_raw = json.load(f)
        cal_items = cal_raw if isinstance(cal_raw, list) else cal_raw.get("events", cal_raw.get("items", []))
        today = datetime.now().strftime("%Y-%m-%d")
        for item in cal_items:
            if item.get("eventType") == "birthday":
                summary = item.get("summary", "")
                start_date = item.get("start", {}).get("date", "")
                if start_date == today and summary:
                    birthdays.append({"name": summary, "note": "Happy birthday!"})

    # Method 2: Check contacts for today's birthdays
    if not birthdays and os.path.exists(input_path):
        with open(input_path, "r") as f:
            raw = json.load(f)

        today = datetime.now().strftime("%m-%d")
        items = raw if isinstance(raw, list) else raw.get("connections", raw.get("items", []))

        for person in items:
            name = ""
            names = person.get("names", [])
            if names:
                name = names[0].get("displayName", "")
            if not name:
                name = person.get("name", person.get("displayName", ""))

            bdays = person.get("birthdays", [])
            for bd in bdays:
                date_info = bd.get("date", {})
                month = date_info.get("month", 0)
                day = date_info.get("day", 0)
                if month and day:
                    bd_str = f"{month:02d}-{day:02d}"
                    if bd_str == today:
                        birthdays.append({"name": name, "note": "Happy birthday!"})

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(birthdays, f, indent=2)
    print(f"Found {len(birthdays)} birthday(s) today -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Parse gog CLI output for PersonalMentor")
    parser.add_argument("--calendar-in", default="", help="gog calendar JSON input")
    parser.add_argument("--calendar-out", default="", help="Parsed calendar JSON output")
    parser.add_argument("--contacts-in", default="", help="gog contacts JSON input")
    parser.add_argument("--birthdays-out", default="", help="Parsed birthdays JSON output")
    args = parser.parse_args()

    if args.calendar_in and args.calendar_out:
        parse_calendar(args.calendar_in, args.calendar_out)

    if args.contacts_in and args.birthdays_out:
        parse_contacts(args.contacts_in, args.birthdays_out, args.calendar_in)


if __name__ == "__main__":
    main()
