#!/usr/bin/env python3
"""Generate a German Sentence of the Day using Gemini API.

Produces a JSON file with a German sentence, English translation,
and an AI-generated illustration (base64-encoded).

Requires: GEMINI_API_KEY environment variable.
"""

import argparse
import base64
import io
import json
import os
import sys
from datetime import date

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: google-genai not installed. Run: pip install google-genai", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow", file=sys.stderr)
    sys.exit(1)

MODEL = "gemini-2.0-flash"
IMAGE_MODEL = "gemini-2.5-flash-image"


def build_client():
    """Build a Gemini API client from environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def generate_sentence(client, today_str):
    """Generate a German sentence with translation and image prompt."""
    prompt = f"""Today is {today_str}. Generate a useful German sentence for a language learner (A1-B1 level).

Requirements:
- The sentence should be practical for daily life (greetings, ordering food, asking directions, small talk, workplace phrases, idioms, etc.)
- Vary the topic each day — use the date as inspiration for variety
- Keep it natural and commonly used by native speakers

Respond in EXACTLY this JSON format (no markdown, no code fences):
{{"german": "Die deutsche Satz hier", "english": "The English translation here", "image_prompt": "A short visual description of the sentence's meaning, suitable for generating an illustration (e.g. 'a person greeting a friend at a cafe')"}}"""

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT"],
            temperature=1.0,
        ),
    )

    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

    return json.loads(text)


def generate_image(client, image_prompt):
    """Generate an illustration from the image prompt. Returns (base64, mime_type) or (None, None)."""
    prompt = f"Generate a simple, friendly, colorful illustration: {image_prompt}. Style: flat design, warm colors, minimal detail, no text."

    try:
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for part in response.parts:
            if part.inline_data is not None:
                b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                mime = part.inline_data.mime_type or "image/png"
                return b64, mime

    except Exception as e:
        print(f"WARNING: Image generation failed: {e}", file=sys.stderr)

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Generate German Sentence of the Day")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--date", default=None, help="Date override (YYYY-MM-DD)")
    args = parser.parse_args()

    today_str = args.date or date.today().isoformat()
    client = build_client()

    print(f"Generating German sentence for {today_str}...")

    # Step 1: Generate sentence + translation + image prompt
    sentence_data = generate_sentence(client, today_str)
    print(f"  Sentence: {sentence_data['german']}")
    print(f"  Translation: {sentence_data['english']}")

    # Step 2: Generate illustration
    print("  Generating illustration...")
    image_b64, image_mime = generate_image(client, sentence_data.get("image_prompt", ""))

    if image_b64:
        print("  Image generated successfully.")
    else:
        print("  Image generation skipped (will render text-only).")

    # Step 3: Write output
    result = {
        "german": sentence_data["german"],
        "english": sentence_data["english"],
        "image_base64": image_b64,
        "image_mime": image_mime,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
