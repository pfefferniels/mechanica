"""Fits the tracker grid of a SUPRA scan: image column of each MIDI key, and the image row of mm 0."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

SEPARATION_FALLBACK = 37.72


def blobs(image_path, row0, scale):
    gray = np.asarray(Image.open(image_path).convert("L"), dtype=np.float32)
    paper = gray < 200
    columns = np.where(paper.mean(axis=0) > 0.5)[0]
    left, right = columns.min() + 4, columns.max() - 4
    bright = gray > 200
    bright[:, :left] = False
    bright[:, right:] = False
    labels, count = ndimage.label(bright)
    boxes = ndimage.find_objects(labels)
    return [
        {"col": (b[1].start + b[1].stop) / 2 / scale, "top": row0 + b[0].start / scale, "w": (b[1].stop - b[1].start) / scale}
        for b in boxes
        if (b[1].stop - b[1].start) > 6 * scale
    ]


def main(image_path, data_path, row0, scale, first_hole, separation):
    data = json.loads(Path(data_path).read_text())
    rows_per_mm = data["rowsPerMm"]
    holes = [(key, first_hole + on * rows_per_mm) for key, on, _ in data["holes"]]
    found = blobs(image_path, row0, scale)
    pairs = [
        (blob, key)
        for blob in found
        for key, top in holes
        if abs(top - blob["top"]) < 6
    ]
    offsets = np.array([blob["col"] - separation * key for blob, key in pairs])
    histogram, edges = np.histogram(offsets, bins=np.arange(offsets.min(), offsets.max() + 2, 2))
    peak = edges[histogram.argmax()] + 1
    near = offsets[np.abs(offsets - peak) < 8]
    print(json.dumps({"blobs": len(found), "pairs": len(pairs), "offset": float(np.median(near)), "inliers": int(near.size),
                      "mean_width": float(np.mean([b["w"] for b in found]))}))


if __name__ == "__main__":
    image, data, row0, scale, first_hole = sys.argv[1:6]
    separation = float(sys.argv[6]) if len(sys.argv) > 6 else SEPARATION_FALLBACK
    main(image, data, float(row0), float(scale), float(first_hole), separation)
