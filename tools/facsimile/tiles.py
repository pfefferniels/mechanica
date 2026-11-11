"""Cuts a SUPRA roll scan into WebP tiles for the analysis page, rotated so the roll runs left to right, bass at the bottom.

Level 0 is half the scan resolution; every further level halves again. A tile at any level spans TILE_PX pixels
along the roll, so a level-n tile covers 2**n level-0 tiles.

Usage: python3 -I tiles.py <meta.json> <druid> <tile-dir> <manifest-dir>
"""
import io
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

IIIF = "https://stacks.stanford.edu/image/iiif/{druid}/{druid}_0001/0,{row},{width},{rows}/{size},/0/default.jpg"
LEVEL0_SCALE = 0.5
TILE_PX = 4096
CHUNK_ROWS = int(TILE_PX / LEVEL0_SCALE)
LEVELS = 4
QUALITY = 60
LEADER_BEFORE_STRAP = 500


RAW = Path(__file__).resolve().parents[2] / "build" / "facsimile" / "raw"


def decodes(body):
    try:
        Image.open(io.BytesIO(body)).load()
        return True
    except OSError:
        return False


def download(url, attempts=4):
    command = ["curl", "-sfL", "--retry", "8", "--retry-all-errors", "--retry-delay", "5", url]
    body = subprocess.run(command, capture_output=True, check=True).stdout
    if decodes(body) or attempts <= 1:
        return body
    return download(url, attempts - 1)


def fetch(url, cache):
    if cache.exists():
        return cache.read_bytes()
    body = download(url)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(body)
    return body


def row_span(geometry):
    first = max(0, int(geometry["PRELEADER_ROW"]) - LEADER_BEFORE_STRAP)
    last = int(min(geometry["IMAGE_LENGTH"], geometry["LAST_HOLE"] + geometry["END_MARGIN"]))
    return first, last


def level0_tile(druid, geometry, row, last):
    rows = min(CHUNK_ROWS, last - row)
    width = int(geometry["IMAGE_WIDTH"])
    url = IIIF.format(druid=druid, row=row, width=width, rows=rows, size=int(width * LEVEL0_SCALE))
    body = fetch(url, RAW / druid / f"{row:06d}.jpg")
    return Image.open(io.BytesIO(body)).convert("RGB").rotate(90, expand=True)


def joined(tiles):
    height = tiles[0].height
    canvas = Image.new("RGB", (sum(tile.width for tile in tiles), height))
    offsets = [sum(tile.width for tile in tiles[:index]) for index in range(len(tiles))]
    [canvas.paste(tile, (x, 0)) for tile, x in zip(tiles, offsets)]
    return canvas


def shrunk(image):
    return image.resize((max(1, image.width // 2), image.height // 2), Image.LANCZOS)


def halved(tiles):
    return [shrunk(joined(tiles[index:index + 2])) for index in range(0, len(tiles), 2)]


def pyramid(level0):
    return [level0] if LEVELS == 1 else [level0, *pyramid_from(halved(level0), LEVELS - 1)]


def pyramid_from(tiles, remaining):
    return [tiles] if remaining == 1 else [tiles, *pyramid_from(halved(tiles), remaining - 1)]


def save(levels, out):
    out.mkdir(parents=True, exist_ok=True)
    names = [[f"L{level}_{index:03d}.webp" for index in range(len(tiles))] for level, tiles in enumerate(levels)]
    [tile.save(out / name, "WEBP", quality=QUALITY, method=6)
     for tiles, level_names in zip(levels, names) for tile, name in zip(tiles, level_names)]
    return names


def main(meta_path, druid, out_dir, manifest_dir):
    geometry = json.loads(Path(meta_path).read_text())[druid]
    first, last = row_span(geometry)
    level0 = [level0_tile(druid, geometry, row, last) for row in range(first, last, CHUNK_ROWS)]
    levels = pyramid(level0)
    names = save(levels, Path(out_dir) / druid)
    manifest = {
        "rowStart": first,
        "rowEnd": last,
        "imageWidth": int(geometry["IMAGE_WIDTH"]),
        "levels": [
            {"scale": LEVEL0_SCALE / 2 ** level, "tileRows": CHUNK_ROWS * 2 ** level, "files": level_names}
            for level, level_names in enumerate(names)
        ],
    }
    Path(manifest_dir).mkdir(parents=True, exist_ok=True)
    (Path(manifest_dir) / f"{druid}.json").write_text(json.dumps(manifest))
    print(druid, len(level0), "level-0 tiles")


if __name__ == "__main__":
    main(*sys.argv[1:5])
