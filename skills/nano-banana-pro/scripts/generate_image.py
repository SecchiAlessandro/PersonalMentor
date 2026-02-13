#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "Pillow>=10.0.0",
# ]
# ///
"""
Nano Banana Pro – Generate or edit images via the Gemini API.

Usage:
    # Text-to-image
    uv run generate_image.py --prompt "a cat on the moon" --filename "cat_moon.png"

    # Image editing (single image)
    uv run generate_image.py --prompt "make the sky purple" --filename "edited.png" -i photo.png

    # Multi-image composition
    uv run generate_image.py --prompt "merge these" --filename "merged.png" -i a.png -i b.png
"""

import argparse
import os
import sys
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image


DEFAULT_MODEL = "gemini-3-pro-image-preview"


def build_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return genai.Client(api_key=api_key)


def load_image(path: str) -> Image.Image:
    p = Path(path)
    if not p.exists():
        print(f"Error: input image not found: {path}", file=sys.stderr)
        sys.exit(1)
    return Image.open(p)


def main():
    parser = argparse.ArgumentParser(description="Generate or edit images via Gemini API")
    parser.add_argument("--prompt", required=True, help="Text prompt for generation or editing")
    parser.add_argument("--filename", required=True, help="Output filename (e.g. output.png)")
    parser.add_argument("-i", "--input", action="append", dest="inputs", default=[], help="Input image path (repeat for multiple)")
    parser.add_argument("--output-dir", default="results", help="Output directory (default: results)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    client = build_client()

    # Build contents: prompt text + optional input images
    contents = []
    for img_path in args.inputs:
        contents.append(load_image(img_path))
    contents.append(args.prompt)

    config = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
    )

    print(f"Generating image with model {args.model}...")
    response = client.models.generate_content(
        model=args.model,
        contents=contents,
        config=config,
    )

    # Ensure output directory exists
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    image_saved = False
    for part in response.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = part.as_image()
            image.save(str(out_path))
            image_saved = True

    if image_saved:
        print(f"MEDIA: {out_path.resolve()}")
    else:
        print("Error: No image was returned by the model.", file=sys.stderr)
        if response.text:
            print(f"Model response: {response.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
