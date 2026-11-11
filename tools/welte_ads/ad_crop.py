"""Crop a Welte ad to the union of its TEI zones, from the local facsimile or the IIIF image."""

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ADS = Path.home() / "Projects/welte-ads"
MARGIN = 0.015


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int

    def padded(self, width: int, height: int) -> "Box":
        dx, dy = round(self.w * MARGIN), round(self.h * MARGIN)
        x, y = max(0, self.x - dx), max(0, self.y - dy)
        return Box(x, y, min(width, self.x + self.w + dx) - x, min(height, self.y + self.h + dy) - y)


def zones_bbox(tei: str) -> Box:
    points = [tuple(map(float, p.split(","))) for z in re.findall(r'<zone points="([^"]+)"', tei) for p in z.split()]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return Box(round(min(xs)), round(min(ys)), round(max(xs) - min(xs)), round(max(ys) - min(ys)))


def first_graphic(tei: str) -> tuple[int, int]:
    m = re.search(r'<graphic url="[^"]+" width="(\d+)px" height="(\d+)px"', tei)
    return int(m.group(1)), int(m.group(2))


def iiif_region_url(tei: str, box: Box, size: tuple[int, int]) -> str | None:
    m = re.search(r'<graphic type="IIIF" url="([^"]+)" width="(\d+)px" height="(\d+)px"', tei)
    if not m or (int(m.group(2)), int(m.group(3))) != size:
        return None
    base, version_size = re.match(r"(.+)/full/(full|max)/0/default\.\w+$", m.group(1)).groups()
    return f"{base}/{box.x},{box.y},{box.w},{box.h}/{version_size}/0/default.jpg"


def crop(ad: str, out: Path) -> str:
    tei = (ADS / "tei" / f"{ad}.xml").read_text(encoding="utf-8")
    size = first_graphic(tei)
    box = zones_bbox(tei).padded(*size)
    local = ADS / "frontend/public/facs" / f"{ad}-0.png"
    if local.exists():
        subprocess.run(["magick", str(local), "-crop", f"{box.w}x{box.h}+{box.x}+{box.y}", "+repage", str(out)], check=True)
        return f"local {local.name}"
    url = iiif_region_url(tei, box, size)
    if url is None:
        raise SystemExit(f"{ad}: no local facsimile and no IIIF image in the zones' coordinate system")
    subprocess.run(["curl", "-sfL", "-m", "120", "-A", "Mozilla/5.0", "-o", str(out), url], check=True)
    return f"iiif {url}"


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    for ad in sys.argv[2:]:
        print(ad, crop(ad, out_dir / f"{ad}.jpg"))
