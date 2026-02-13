#!/usr/bin/env python3
"""Interactive interview script for PersonalMentor onboarding.

Prints questions to stdout grouped by category.
The agent should ask each question, collect the user's answer,
and map it to the corresponding profile YAML field.
"""

QUESTIONS = [
    {
        "category": "Identity & Basics",
        "questions": [
            {
                "q": "What is your full name?",
                "maps_to": "identity.yaml → name",
            },
            {
                "q": "What is your current professional title or role?",
                "maps_to": "identity.yaml → title",
            },
            {
                "q": "Where are you based? (city, country)",
                "maps_to": "identity.yaml → location",
            },
            {
                "q": "Write a short bio about yourself (2-3 sentences).",
                "maps_to": "identity.yaml → bio",
            },
        ],
    },
    {
        "category": "Professional Interests",
        "questions": [
            {
                "q": "What professional topics are you most interested in? (list up to 5, with priority 1-10)",
                "maps_to": "interests.yaml → professional",
            },
            {
                "q": "Which industries do you follow or work in?",
                "maps_to": "interests.yaml → industries",
            },
            {
                "q": "Any personal interests or hobbies you'd like covered in your daily brief?",
                "maps_to": "interests.yaml → personal",
            },
        ],
    },
    {
        "category": "Job Search",
        "questions": [
            {
                "q": "Are you currently looking for a new role? (yes/no)",
                "maps_to": "interests.yaml → job_search.active",
            },
            {
                "q": "If yes: What roles are you targeting? (list titles)",
                "maps_to": "interests.yaml → job_search.target_roles",
            },
            {
                "q": "If yes: What locations are you considering? (remote/cities)",
                "maps_to": "interests.yaml → job_search.target_locations",
            },
            {
                "q": "If yes: What is your target salary range?",
                "maps_to": "interests.yaml → job_search.salary_range",
            },
        ],
    },
    {
        "category": "Design & Style Preferences",
        "questions": [
            {
                "q": "Pick a theme for your daily newspaper (or say 'show me options'): Ocean Depths, Sunset Boulevard, Forest Canopy, Modern Minimalist, Golden Hour, Arctic Frost, Desert Rose, Tech Innovation, Botanical Garden, Midnight Galaxy",
                "maps_to": "preferences.yaml → design.theme",
            },
            {
                "q": "What writing tone do you prefer? (formal / conversational / technical)",
                "maps_to": "preferences.yaml → writing.tone",
            },
            {
                "q": "Do you prefer concise summaries or detailed writeups? (concise / detailed)",
                "maps_to": "preferences.yaml → writing.length",
            },
            {
                "q": "What language should your daily newspaper be in? (e.g., en, it, de, fr)",
                "maps_to": "preferences.yaml → writing.language",
            },
        ],
    },
    {
        "category": "Content Sources",
        "questions": [
            {
                "q": "Do you have any favorite RSS feeds, blogs, or news sites? (list URLs)",
                "maps_to": "sources.yaml → rss_feeds",
            },
            {
                "q": "Which job boards should I monitor for you? (e.g., LinkedIn Jobs URL, specific company career pages)",
                "maps_to": "sources.yaml → job_boards",
            },
            {
                "q": "Any event platforms or meetup pages to watch? (e.g., Meetup.com groups, Eventbrite URLs)",
                "maps_to": "sources.yaml → event_sources",
            },
        ],
    },
    {
        "category": "Daily Newspaper Configuration",
        "questions": [
            {
                "q": "Which sections do you want in your daily newspaper? (all enabled by default): Top Stories, Jobs For You, Today's Calendar, Birthdays, Events Near You, Skill Spotlight, Industry Pulse, Reading List",
                "maps_to": "preferences.yaml → daily_artifact.sections_enabled",
            },
            {
                "q": "What time should I deliver your daily newspaper? (default: 20:00)",
                "maps_to": "preferences.yaml → daily_artifact.delivery_time",
            },
        ],
    },
]


def main():
    print("=" * 60)
    print("  PersonalMentor — Onboarding Interview")
    print("=" * 60)
    print()
    print("Ask the following questions to build the user profile.")
    print("Each answer maps to a specific YAML field.\n")

    for section in QUESTIONS:
        print(f"\n--- {section['category']} ---\n")
        for item in section["questions"]:
            print(f"  Q: {item['q']}")
            print(f"     → {item['maps_to']}")
            print()

    print("=" * 60)
    print("After collecting all answers, update the profile YAML files")
    print("and run validate_profile.py to verify the changes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
