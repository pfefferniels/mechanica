"""Build stages of a diss figure: the figure up to a boundary, the empty frame after it.

The frame is one column of the figure that holds only the horizontal rules, repeated
to the right edge. Usage: python3 tools/stages.py <out-dir>
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

FIGURES = Path(__file__).resolve().parents[1] / "build" / "diss"


@dataclass(frozen=True)
class Staged:
    name: str
    clean_column: int
    boundaries: tuple


STAGED = [
    Staged("abb-05", clean_column=3315, boundaries=(583, 820, 1077, 2656, 2765, 2880)),
    Staged("abb-06", clean_column=335, boundaries=(810, 1180, 1772, 2022)),
    Staged("abb-gruene-rolle", clean_column=3315, boundaries=(1029, 2154, 2746)),
]


def stage(figure: Image.Image, clean_column: int, boundary: int) -> Image.Image:
    width, height = figure.size
    column = figure.crop((clean_column, 0, clean_column + 1, height))
    frame = column.resize((width - boundary, height), Image.NEAREST)
    out = figure.copy()
    out.paste(frame, (boundary, 0))
    return out


def write_stages(staged: Staged, out_dir: Path):
    figure = Image.open(FIGURES / f"{staged.name}.png").convert("RGB")
    images = [stage(figure, staged.clean_column, b) for b in staged.boundaries] + [figure]
    [image.save(out_dir / f"{staged.name}-{index + 1}.png", optimize=True) for index, image in enumerate(images)]
    print(staged.name, len(images), "stages")


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    [write_stages(staged, out_dir) for staged in STAGED]


if __name__ == "__main__":
    main()
