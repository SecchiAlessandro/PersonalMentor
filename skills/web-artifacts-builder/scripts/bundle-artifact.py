#!/usr/bin/env python3
"""Bundle a React app into a single HTML artifact (cross-platform).

Drop-in replacement for bundle-artifact.sh that works on macOS, Linux, and Windows.

Usage:
    python skills/web-artifacts-builder/scripts/bundle-artifact.py
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    print("Bundling React app to single HTML artifact...")

    if not Path("package.json").is_file():
        print("Error: No package.json found. Run this script from your project root.")
        sys.exit(1)

    if not Path("index.html").is_file():
        print("Error: No index.html found in project root.")
        print("  This script requires an index.html entry point.")
        sys.exit(1)

    # Install bundling dependencies
    print("Installing bundling dependencies...")
    subprocess.run(
        ["pnpm", "add", "-D", "parcel", "@parcel/config-default",
         "parcel-resolver-tspaths", "html-inline"],
        check=True,
    )

    # Create Parcel config with tspaths resolver
    parcelrc = Path(".parcelrc")
    if not parcelrc.is_file():
        print("Creating Parcel configuration with path alias support...")
        parcelrc.write_text(
            '{\n'
            '  "extends": "@parcel/config-default",\n'
            '  "resolvers": ["parcel-resolver-tspaths", "..."]\n'
            '}\n'
        )

    # Clean previous build
    print("Cleaning previous build...")
    shutil.rmtree("dist", ignore_errors=True)
    Path("bundle.html").unlink(missing_ok=True)

    # Build with Parcel
    print("Building with Parcel...")
    subprocess.run(
        ["pnpm", "exec", "parcel", "build", "index.html",
         "--dist-dir", "dist", "--no-source-maps"],
        check=True,
    )

    # Inline everything into single HTML
    print("Inlining all assets into single HTML file...")
    result = subprocess.run(
        ["pnpm", "exec", "html-inline", "dist/index.html"],
        capture_output=True, text=True, check=True,
    )
    Path("bundle.html").write_text(result.stdout)

    # Get file size
    size_bytes = Path("bundle.html").stat().st_size
    if size_bytes >= 1_048_576:
        file_size = f"{size_bytes / 1_048_576:.1f}M"
    elif size_bytes >= 1024:
        file_size = f"{size_bytes / 1024:.0f}K"
    else:
        file_size = f"{size_bytes}B"

    print()
    print("Bundle complete!")
    print(f"Output: bundle.html ({file_size})")
    print()
    print("You can now use this single HTML file as an artifact in Claude conversations.")
    print("To test locally: open bundle.html in your browser")


if __name__ == "__main__":
    main()
