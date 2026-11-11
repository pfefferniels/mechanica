"""Removes the speaker notes (<aside>) from slide files, for the public copy of the deck.

The notes stay in the Slides artifact and in the full snapshot under build/.

Usage: python3 tools/site/strip_notes.py <slide-file> […]
"""
import re
import sys
from pathlib import Path

NOTES = re.compile(r"\s*<aside\b.*?</aside>", re.DOTALL)


def strip(path):
    text = path.read_text(encoding="utf-8")
    stripped = NOTES.sub("", text)
    path.write_text(stripped, encoding="utf-8")
    return stripped != text


def main(paths):
    changed = [path.name for path in map(Path, paths) if strip(path)]
    print(f"notes removed from {len(changed)} of {len(paths)} slides")


if __name__ == "__main__":
    main(sys.argv[1:])
