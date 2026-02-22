#!/usr/bin/env python3
"""Generate a German Sentence of the Day using Gemini API.

Produces a JSON file with a German sentence, English translation,
and an AI-generated illustration (base64-encoded).

Requires: GEMINI_API_KEY environment variable.
"""

import argparse
import base64
import concurrent.futures
import io
import json
import os
import sys
from datetime import date

API_TIMEOUT = 60  # seconds per API call

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

TEXT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-2.5-flash"]


def build_client():
    """Build a Gemini API client from environment variable."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def generate_sentence(client, today_str):
    """Generate a German sentence with translation and image prompt.

    Tries each model in TEXT_MODELS until one succeeds.
    """
    prompt = f"""Today is {today_str}. Generate a useful German sentence for a language learner (B2 level).

Requirements:
- Use more complex grammar: subordinate clauses, Konjunktiv II, passive voice, or idiomatic expressions
- Topics: professional communication, news/current events, abstract concepts, Swiss/German culture, nuanced opinions
- Vary the topic each day — use the date as inspiration for variety
- Keep it natural and commonly used by educated native speakers

Respond in EXACTLY this JSON format (no markdown, no code fences):
{{"german": "Die deutsche Satz hier", "english": "The English translation here", "image_prompt": "A short visual description of the sentence's meaning, suitable for generating an illustration (e.g. 'a person greeting a friend at a cafe')"}}"""

    last_error = None
    for model in TEXT_MODELS:
        try:
            print(f"  Trying model: {model}")
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    temperature=1.0,
                ),
            )
            try:
                response = future.result(timeout=API_TIMEOUT)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3].strip()

            return json.loads(text)
        except concurrent.futures.TimeoutError:
            last_error = TimeoutError(f"API call timed out after {API_TIMEOUT}s")
            print(f"  WARNING: {model} timed out after {API_TIMEOUT}s", file=sys.stderr)
            continue
        except Exception as e:
            last_error = e
            print(f"  WARNING: {model} failed: {e}", file=sys.stderr)
            continue

    raise RuntimeError(f"All text models failed. Last error: {last_error}")


def generate_image(client, image_prompt):
    """Generate an illustration from the image prompt. Returns (base64, mime_type) or (None, None).

    Tries each model in IMAGE_MODELS until one succeeds.
    """
    prompt = f"Generate a simple, friendly, colorful illustration: {image_prompt}. Style: flat design, warm colors, minimal detail, no text."

    for model in IMAGE_MODELS:
        try:
            print(f"  Trying image model: {model}")
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            try:
                response = future.result(timeout=API_TIMEOUT)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            for part in response.parts:
                if part.inline_data is not None:
                    b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                    mime = part.inline_data.mime_type or "image/png"
                    return b64, mime

        except concurrent.futures.TimeoutError:
            print(f"  WARNING: {model} image generation timed out after {API_TIMEOUT}s", file=sys.stderr)
            continue
        except Exception as e:
            print(f"  WARNING: {model} image generation failed: {e}", file=sys.stderr)
            continue

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
    try:
        sentence_data = generate_sentence(client, today_str)
    except Exception as e:
        print(f"  ERROR: German sentence generation failed: {e}", file=sys.stderr)
        # Write empty result so pipeline can continue without this section
        result = {"german": "", "english": "", "image_base64": None, "image_mime": None}
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Output (empty): {args.output}")
        return

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
