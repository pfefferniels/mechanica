"""Inline SVGs for the slides: the T-100 tracker bar and the split keyboard.

Usage: python3 tools/svg.py <out-dir>
"""

import sys
from pathlib import Path

BASS = "#1d4ed8"
BASS_LIGHT = "#dbe4fb"
TREBLE = "#c2410c"
TREBLE_LIGHT = "#fde3d6"
INK = "#111827"
BRASS = "#b8975a"

LOWEST, HIGHEST = 24, 103
LAST_BASS = 66
BLACK_PITCH_CLASSES = {1, 3, 6, 8, 10}


def tracker_bar(width=1664, height=120, holes=100, edge=10) -> str:
    pitch = (width - 64) / holes
    bar = f'<rect x="0" y="20" width="{width}" height="{height - 40}" rx="40" fill="{BRASS}"/>'

    def color(index):
        if index < edge:
            return BASS
        if index >= holes - edge:
            return TREBLE
        return INK

    circles = "".join(
        f'<circle cx="{32 + pitch * (i + 0.5):.1f}" cy="{height / 2}" r="5.5" fill="{color(i)}"/>' for i in range(holes)
    )
    return f'<svg aria-label="Gleitblock mit 100 Öffnungen: je 10 am Rand für die Dynamik, 80 für die Töne" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{bar}{circles}</svg>'


def is_black(pitch: int) -> bool:
    return pitch % 12 in BLACK_PITCH_CLASSES


def keyboard(width=1664, height=260, pressed=None) -> str:
    """`pressed`: pitch → dot radius."""
    pressed = pressed or {}
    whites = [p for p in range(LOWEST, HIGHEST + 1) if not is_black(p)]
    key = width / len(whites)
    left_of = {p: i * key for i, p in enumerate(whites)}

    def white(p):
        fill = BASS_LIGHT if p <= LAST_BASS else TREBLE_LIGHT
        return f'<rect x="{left_of[p]:.1f}" y="0" width="{key:.1f}" height="{height}" fill="{fill}" stroke="#ffffff" stroke-width="2"/>'

    def black_x(p):
        return left_of[p - 1] + key * 0.68

    def black(p):
        fill = BASS if p <= LAST_BASS else TREBLE
        return f'<rect x="{black_x(p):.1f}" y="0" width="{key * 0.64:.1f}" height="{height * 0.62:.1f}" rx="3" fill="{fill}"/>'

    def dot(p, radius):
        x = black_x(p) + key * 0.32 if is_black(p) else left_of[p] + key / 2
        y = height * 0.45 if is_black(p) else height * 0.82
        fill = "#ffffff" if is_black(p) else (BASS if p <= LAST_BASS else TREBLE)
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}"/>'

    split = left_of[LAST_BASS + 1]
    body = (
        "".join(white(p) for p in whites)
        + "".join(black(p) for p in range(LOWEST, HIGHEST + 1) if is_black(p))
        + f'<rect x="{split - 3:.1f}" y="0" width="6" height="{height}" fill="{INK}"/>'
        + "".join(dot(p, r) for p, r in pressed.items())
    )
    return f'<svg aria-label="Klaviatur C1 bis G7, geteilt zwischen fis\' und g\'" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{body}</svg>', split


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "gleitblock.svg").write_text(tracker_bar())
    svg, split = keyboard()
    (out / "klaviatur.svg").write_text(svg)
    chord = {51: 14, 55: 14, 58: 14, 63: 14, 79: 22}
    svg_pressed, _ = keyboard(pressed=chord)
    (out / "klaviatur-akkord.svg").write_text(svg_pressed)
    print("split at", round(split, 1))


if __name__ == "__main__":
    main()
