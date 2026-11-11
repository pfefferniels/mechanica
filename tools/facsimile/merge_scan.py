"""Adds the scan geometry and tile list to each roll's data file of the analysis page.

Usage: python3 -I merge_scan.py <app-dir> <manifest-dir> <meta.json> <calibration.json>
"""
import json
import sys
from pathlib import Path


def scan_entry(druid, manifest, geometry, column_offset):
    return {
        "firstHole": geometry["FIRST_HOLE"],
        "rowStart": manifest["rowStart"],
        "rowEnd": manifest["rowEnd"],
        "imageWidth": manifest["imageWidth"],
        "columnOffset": column_offset,
        "separation": geometry["HOLE_SEPARATION"],
        "holeWidthPx": geometry["AVG_HOLE_WIDTH"],
        "levels": manifest["levels"],
    }


def merge(public, manifests, meta, calibration, druid):
    manifest_path = manifests / f"{druid}.json"
    data_path = public / "data" / f"{druid}.json"
    data = json.loads(data_path.read_text())
    data["scan"] = scan_entry(druid, json.loads(manifest_path.read_text()), meta[druid], calibration[druid])
    data_path.write_text(json.dumps(data))
    return druid


def main(public_dir, manifest_dir, meta_path, calibration_path):
    public = Path(public_dir)
    manifests = Path(manifest_dir)
    meta = json.loads(Path(meta_path).read_text())
    calibration = json.loads(Path(calibration_path).read_text())
    druids = [roll["druid"] for roll in json.loads((public / "rolls.json").read_text())]
    print(*[merge(public, manifests, meta, calibration, druid) for druid in druids])


if __name__ == "__main__":
    main(*sys.argv[1:5])
