"""Animate Gottschewski's Hauptgraphiken: a playhead, and for verified cases the sounding bar, over his Hörbeispiele.

His graphics run on the time axis of his Hörbeispiele: horizontal seconds keep a constant ratio (about 2.8) to the
vertical „Dauer in Sekunden“ scale in all three graphics that can be checked. Beat times in Hörbeispiel time come
from chroma DTW against SUPRA's renderings of the same rolls (beats from op15/data.json). Scharwenka's roll is not in
SUPRA: his beats are the median of alignments against the three other renderings, and his graphic is placed by the
left edges of bar 1 and bar 62.

Usage: python3 tools/op15_anim.py <key> [<key> ...]   (saintsaens, pugno, busoni, scharwenka)
"""

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OP15 = ROOT / "op15"
CLIPS = ROOT / "build/gottschewski/clips"
OUT = ROOT / "build/op15/anim"
SUPRA_AUDIO_DELAY = 0.06  # SUPRA's rendering starts this much after the MIDI time axis (op15 page, measured)
SR, HOP = 22050, 1024
FPS = 10
WIDTH = 1600
ACTIVE = (0x1D, 0x4E, 0xD8)  # the op15 page's highlight colour
LINE = 3
IN_SUPRA = ("saintsaens", "pugno", "busoni")
# Bar outlines coincide with Gottschewski's drawn bar boxes only here (checked by overlay); elsewhere playhead only.
OUTLINE_BARS = {"saintsaens", "pugno"}


@dataclass(frozen=True)
class Graphic:
    pixels: np.ndarray  # grayscale, original resolution
    base: int           # row of the time axis
    fifty: int          # row of the dotted 50-second line

    @property
    def px_per_second(self) -> float:
        return (self.base - self.fifty) / 50


@dataclass(frozen=True)
class Timing:
    """Hörbeispiel time → x on the graphic."""
    slope: float
    intercept: float

    def x(self, t):
        return self.intercept + self.slope * t


@dataclass(frozen=True)
class Box:
    x1: float
    x2: float
    top: float
    bottom: float


def graphic_path(key: str) -> Path:
    return OP15 / "img" / f"hauptgraphik-{key}.jpg"


def load_graphic(key: str) -> Graphic:
    pixels = np.asarray(Image.open(graphic_path(key)).convert("L")).astype(int)
    height, width = pixels.shape
    inner = pixels[:, int(width * 0.15):int(width * 0.95)]
    base = max(y for y in range(height) if (inner[y] < 128).mean() > 0.85)
    band = pixels[:int(height * 0.2), int(width * 0.05):int(width * 0.30)]
    dotted = (band < 215).mean(axis=1)
    # The label „Dauer in Sekunden“ sits above the 50-second line; the line is the strongest row below it.
    start, stop = int(height * 0.035), int(height * 0.10)
    fifty = int(np.argmax(dotted[start:stop])) + start
    return Graphic(pixels, base, fifty)


def bar_edges(graphic: Graphic) -> tuple[int, int]:
    """Left edges of bar 1 and of the final bar 62, read off the drawing."""
    filled = np.where(graphic.pixels[graphic.base - 6] < 200)[0]
    columns = (graphic.pixels[graphic.base - 200:graphic.base - 8] < 110).mean(axis=0)
    verticals = np.where(columns > 0.85)[0]
    last = verticals[verticals < filled.max() - 10].max()
    return int(filled.min()), int(last)


def performance(key: str) -> dict:
    return next(p for p in json.loads((OP15 / "data.json").read_text()) if p["key"] == key)


def calibrated_x(key: str, t: np.ndarray) -> np.ndarray:
    c = json.loads((OP15 / "calib.json").read_text())[key]
    return c["x0"] + (t - c["t0"]) * c["pxs"]


def decode(media: Path) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(media), "-vn", "-ac", "1", "-ar", str(SR), wav.name], check=True)
        samples, _ = librosa.load(wav.name, sr=SR)
    return samples


def hoerbeispiel(key: str) -> Path:
    return CLIPS / f"op15-{key}.mp4"


def beats_in(audio: np.ndarray, reference: str) -> np.ndarray:
    """The reference roll's beat times, carried over to `audio` by chroma DTW against SUPRA's rendering."""
    perf = performance(reference)
    chroma = lambda y: librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    _, path = librosa.sequence.dtw(X=chroma(audio), Y=chroma(decode(OP15 / perf["audio"])), metric="cosine")
    here, there = (path[::-1] * HOP / SR).T
    there_unique, first = np.unique(there, return_index=True)
    supra = np.array([b["t"] for b in perf["beats"]])
    return np.interp(supra + SUPRA_AUDIO_DELAY, there_unique, here[first])


def timing_from_calibration(key: str, beats: np.ndarray) -> Timing:
    supra = np.array([b["t"] for b in performance(key)["beats"]])
    slope, intercept = np.polyfit(beats, calibrated_x(key, supra), 1)
    return Timing(slope, intercept)


def timing_from_edges(graphic: Graphic, beats: np.ndarray) -> Timing:
    first, last = bar_edges(graphic)
    slope = (last - first) / (beats[-1] - beats[0])
    return Timing(slope, first - slope * beats[0])


def bar_boxes(beats: np.ndarray, downbeats: list[int], timing: Timing, graphic: Graphic) -> list[Box]:
    return [Box(timing.x(beats[i]), timing.x(beats[j]), graphic.base - (beats[j] - beats[i]) * graphic.px_per_second, graphic.base)
            for i, j in zip(downbeats, downbeats[1:])]


def scaled(key: str) -> tuple[np.ndarray, float]:
    picture = Image.open(graphic_path(key)).convert("RGB")
    scale = WIDTH / picture.width
    return np.asarray(picture.resize((WIDTH, round(picture.height * scale) // 2 * 2), Image.LANCZOS)).copy(), scale


def outline(frame: np.ndarray, box: Box, scale: float) -> None:
    x1, x2, y1, y2 = (round(v * scale) for v in (box.x1, box.x2, box.top, box.bottom))
    frame[y1:y1 + LINE, x1:x2 + 1] = ACTIVE
    frame[y1:y2, x1:x1 + LINE] = ACTIVE
    frame[y1:y2, x2 - LINE + 1:x2 + 1] = ACTIVE


def frame_at(base: np.ndarray, scale: float, x: float, boxes: list[Box], graphic: Graphic) -> np.ndarray:
    frame = base.copy()
    current = next((b for b in boxes if b.x1 <= x < b.x2), None)
    if current is not None:
        outline(frame, current, scale)
    px = round(x * scale)
    frame[round(graphic.fifty * scale):round(graphic.base * scale), px - 1:px + 1] = ACTIVE
    return frame


def duration(media: Path) -> float:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media)],
                           check=True, capture_output=True, text=True)
    return float(probe.stdout)


def render(key: str, timing: Timing, boxes: list[Box], graphic: Graphic, out: Path) -> Path:
    base, scale = scaled(key)
    height, width = base.shape[:2]
    clip = hoerbeispiel(key)
    seconds = duration(clip)
    # The Hörbeispiel's AAC stream is copied, so the sound is the one the slides already play.
    encoder = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS),
         "-i", "-", "-i", str(clip), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-crf", "23", "-c:a", "copy", "-t", f"{seconds:.3f}", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE,
    )
    for t in np.arange(0, seconds, 1 / FPS):
        encoder.stdin.write(frame_at(base, scale, timing.x(t), boxes, graphic).tobytes())
    encoder.stdin.close()
    if encoder.wait():
        raise RuntimeError(f"ffmpeg failed for {key}")
    Image.fromarray(base).save(out.with_suffix(".poster.png"))
    return out


def animate(key: str) -> Path:
    graphic = load_graphic(key)
    audio = decode(hoerbeispiel(key))
    if key in IN_SUPRA:
        beats = beats_in(audio, key)
        timing = timing_from_calibration(key, beats)
    else:
        beats = np.median([beats_in(audio, reference) for reference in IN_SUPRA], axis=0)
        timing = timing_from_edges(graphic, beats)
    downbeats = [i for i, b in enumerate(performance(IN_SUPRA[0])["beats"]) if b["half"] == 0]
    boxes = bar_boxes(beats, downbeats, timing, graphic) if key in OUTLINE_BARS else []
    print(f"{key}: {timing.slope:.3f} px/s, vertical {graphic.px_per_second:.2f} px/s, ratio "
          f"{graphic.px_per_second / timing.slope:.3f}, bar 1 at {beats[0]:.2f} s, bar 62 at {beats[-1]:.2f} s")
    OUT.mkdir(parents=True, exist_ok=True)
    return render(key, timing, boxes, graphic, OUT / f"op15-{key}.mp4")


if __name__ == "__main__":
    print(*map(animate, sys.argv[1:]), sep="\n")
