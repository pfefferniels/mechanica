"""Figures, sound and videos for the Welte slides, from the emulator's JSON.

Usage: python3 tools/render.py <emu-dir> <out-dir> <soundfont.sf2> <traced-curves.csv>
"""

import bisect
import csv
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import mido
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
PLEX = FONTS / "IBMPlexSans-normal-400.ttf"
PLEX_MEDIUM = FONTS / "IBMPlexSans-normal-500.ttf"
GARAMOND_ITALIC = FONTS / "EBGaramond-italic-500.ttf"

INK = (17, 24, 39)
GRAY = (107, 114, 128)
RULE = (209, 213, 219)
GHOST = (229, 231, 235)
PAPER = (139, 74, 72)
HOLE = (255, 255, 255)
BASS = (29, 78, 216)
TREBLE = (194, 65, 12)
PLAYHEAD = (217, 119, 6)
DRAWN = (17, 24, 39)

FPS = 30
SCALE = 2

# Rails of roll 3309 on its printed scale (roll-nuance-tracer/empirics/docs/measurements.md §2).
RAILS = {"bass": (0.017, 0.912), "treble": (0.022, 0.952)}
MEZZOFORTE_PIN = 0.773

LABELS = {
    ("sforzando", "on"): "Sforzando an",
    ("sforzando", "off"): "Sforzando ab",
    ("crescendo", "on"): "Crescendo an",
    ("crescendo", "off"): "Crescendo ab",
    ("mezzoforte", "on"): "Mezzoforte an",
    ("mezzoforte", "off"): "Mezzoforte ab",
    ("sustainPedal", "on"): "Pedal an",
    ("sustainPedal", "off"): "Pedal ab",
}
FOUR_TRACKS = [("sforzando", "on"), ("sforzando", "off"), ("crescendo", "on"), ("crescendo", "off")]
SIX_TRACKS = FOUR_TRACKS + [("mezzoforte", "on"), ("mezzoforte", "off")]


def font(path: Path, size: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), round(size * SCALE))


@dataclass(frozen=True)
class Frame:
    """Pixel geometry of one figure, in slide pixels before SCALE."""

    width: int
    height: int
    left: int
    right: int
    seconds: float

    def x(self, t: float) -> float:
        return SCALE * (self.left + (self.width - self.left - self.right) * t / self.seconds)


@dataclass(frozen=True)
class RuleFigure:
    name: str
    tracks: list
    show_pin: bool = False
    hole_spans: bool = False


def scaled(points):
    return [(x * SCALE, y * SCALE) for x, y in points]


def dashed_vertical(draw, x, top, bottom, color, dash=8, gap=7, width=2):
    starts = range(int(top * SCALE), int(bottom * SCALE), (dash + gap) * SCALE)
    [draw.line([(x, y), (x, min(y + dash * SCALE, bottom * SCALE))], fill=color, width=width * SCALE) for y in starts]


def dashed_horizontal(draw, left, right, y, color, dash=14, gap=10, width=2):
    starts = range(int(left), int(right), (dash + gap) * SCALE)
    [draw.line([(x, y), (min(x + dash * SCALE, right), y)], fill=color, width=width * SCALE) for x in starts]


def curve_points(frame, seconds, values, top, bottom):
    return [(frame.x(t), SCALE * (bottom - (bottom - top) * v)) for t, v in zip(seconds, values)]


def draw_scale_lines(draw, frame, top, bottom, levels):
    """`levels`: (value, label, weight) with value 0 at the bottom line and 1 at the top."""
    label_font = font(GARAMOND_ITALIC, 40)
    for value, label, weight in levels:
        y = SCALE * (bottom - (bottom - top) * value)
        line = (frame.x(0) - 12 * SCALE, frame.width * SCALE - frame.right * SCALE)
        if weight == "dashed":
            dashed_horizontal(draw, *line, y, GRAY)
        else:
            draw.line([(line[0], y), (line[1], y)], fill=INK, width=(5 if weight == "thick" else 2) * SCALE)
        draw.text((frame.x(0) - 40 * SCALE, y), label, font=label_font, fill=INK, anchor="rm")


def draw_paper(draw, frame, punches, tracks, top, row_height, hole_spans=False, ports=None, seconds=None, half="bass"):
    label_font = font(PLEX, 24)
    bottom = top + row_height * len(tracks)
    draw.rectangle([frame.x(0) - 12 * SCALE, top * SCALE, frame.width * SCALE - frame.right * SCALE, bottom * SCALE], fill=PAPER)
    for index, track in enumerate(tracks):
        y = top + row_height * (index + 0.5)
        draw.text((frame.x(0) - 32 * SCALE, y * SCALE), LABELS[track], font=label_font, fill=GRAY, anchor="rm")
        if index:
            draw.line([(frame.x(0) - 12 * SCALE, (top + row_height * index) * SCALE), (frame.width * SCALE - frame.right * SCALE, (top + row_height * index) * SCALE)], fill=(122, 62, 60), width=SCALE)
    for punch in punches:
        track = (punch["control"], punch["action"])
        if track not in tracks or punch["half"] != half:
            continue
        y = top + row_height * (tracks.index(track) + 0.5)
        if hole_spans and ports is not None:
            series = ports.get(f"{half}:{punch['control']}:{punch['action']}", [])
            open_times = [t for t, v in zip(seconds, series) if v > 0.02 and punch["on"] - 0.2 <= t <= punch["off"] + 0.2]
            if open_times:
                draw.rounded_rectangle([frame.x(open_times[0]), (y - 16) * SCALE, frame.x(open_times[-1]), (y + 16) * SCALE], radius=16 * SCALE, outline=(250, 204, 21), width=3 * SCALE)
        radius = 11
        x0, x1 = frame.x(punch["on"]), frame.x(punch["off"])
        x1 = max(x1, x0 + 2 * radius * SCALE)
        draw.rounded_rectangle([x0, (y - radius) * SCALE, x1, (y + radius) * SCALE], radius=radius * SCALE, fill=HOLE)
    return bottom


def draw_guides(draw, frame, punches, tracks, top, bottom, half="bass"):
    onsets = sorted({round(p["on"], 3) for p in punches if (p["control"], p["action"]) in tracks and p["half"] == half})
    [dashed_vertical(draw, frame.x(t), top, bottom, RULE) for t in onsets]


def rule_images(data, figure):
    """The figure twice: the curve as drawn, and the curve still ahead of the tracker bar."""
    frame = Frame(width=1664, height=700, left=250, right=24, seconds=data["seconds"][-1])
    curve_top, curve_bottom = 40, 300
    paper_top = 350
    row_height = 40 if len(figure.tracks) > 4 else 44

    def draw_one(curve_color):
        image = Image.new("RGB", (frame.width * SCALE, frame.height * SCALE), "white")
        draw = ImageDraw.Draw(image)
        paper_bottom = paper_top + row_height * len(figure.tracks)
        draw_guides(draw, frame, data["punches"], figure.tracks, curve_top, paper_top)
        levels = [(1, "ff", "thick"), (0, "pp", "thick")]
        if figure.show_pin:
            levels.append((MEZZOFORTE_PIN, "mf", "dashed"))
        draw_scale_lines(draw, frame, curve_top, curve_bottom, levels)
        draw_paper(draw, frame, data["punches"], figure.tracks, paper_top, row_height,
                   figure.hole_spans, data.get("ports"), data["seconds"])
        draw.line(curve_points(frame, data["seconds"], data["bass"], curve_top, curve_bottom), fill=curve_color, width=5 * SCALE, joint="curve")
        return image.crop((0, 0, frame.width * SCALE, (paper_bottom + 16) * SCALE))

    return frame, draw_one(BASS), draw_one(GHOST)


def travel_at(seconds, values, t):
    index = min(range(len(seconds)), key=lambda i: abs(seconds[i] - t))
    return values[index]


def velocity(travel: float) -> int:
    return max(1, min(127, round(18 + 92 * travel)))


@dataclass(frozen=True)
class Note:
    key: int
    on: float
    off: float
    velocity: int


def march_figure(seconds: float) -> list:
    """Bass on the beat, chord on the off-beat, in E-flat, all within the bass half."""
    beat = 0.32
    beats = range(int(seconds / beat))
    bass = [39, 46]
    chord = [55, 58, 63]
    return [
        (t, key)
        for b in beats
        for t, keys in [(b * beat, [bass[(b // 2) % 2]]), (b * beat + beat / 2, chord)]
        for key in keys
    ]


def rule_notes(data) -> list:
    return [
        Note(key, t, t + 0.14, velocity(travel_at(data["seconds"], data["bass"], t)))
        for t, key in march_figure(data["seconds"][-1])
    ]


def write_midi(notes, path: Path, pedal=None):
    """`pedal`: (seconds, level 0..1) samples for the damper, or None."""
    midi = mido.MidiFile(ticks_per_beat=1000)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=1_000_000))
    events = [(n.on, mido.Message("note_on", note=n.key, velocity=n.velocity)) for n in notes]
    events += [(n.off, mido.Message("note_off", note=n.key, velocity=0)) for n in notes]
    if pedal:
        events += [(t, mido.Message("control_change", control=64, value=round(127 * level))) for t, level in pedal]
    events.sort(key=lambda e: (e[0], e[1].type != "note_off"))
    ticks = [round(t * 1000) for t, _ in events]
    deltas = [b - a for a, b in zip([0] + ticks, ticks)]
    track.extend(message.copy(time=delta) for delta, (_, message) in zip(deltas, events))
    midi.save(path)


def render_audio(midi_path: Path, wav_path: Path, soundfont: Path):
    subprocess.run(["fluidsynth", "-ni", "-q", "-r", "44100", "-g", "0.9", "-F", str(wav_path), str(soundfont), str(midi_path)], check=True)


def write_video(frame, solid, ghost, wav_path, out_path, tail=0.6):
    width, height = solid.size[0] // SCALE, solid.size[1] // SCALE
    width, height = width - width % 2, height - height % 2
    solid_small = solid.resize((width, height), Image.LANCZOS)
    ghost_small = ghost.resize((width, height), Image.LANCZOS)
    total = frame.seconds + tail
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(FPS), "-i", "-",
         "-i", str(wav_path), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest",
         "-movflags", "+faststart", str(out_path)],
        stdin=subprocess.PIPE,
    )

    def frame_at(t):
        x = min(frame.x(t), frame.x(frame.seconds)) / SCALE
        image = ghost_small.copy()
        image.paste(solid_small.crop((0, 0, int(x), height)), (0, 0))
        ImageDraw.Draw(image).line([(x, 0), (x, height)], fill=PLAYHEAD, width=4)
        return image

    for index in range(int(total * FPS)):
        ffmpeg.stdin.write(frame_at(index / FPS).tobytes())
    ffmpeg.stdin.close()
    ffmpeg.wait()


RULES = [
    RuleFigure("ruhe", FOUR_TRACKS),
    RuleFigure("crescendo", FOUR_TRACKS),
    RuleFigure("crescendo-lang", FOUR_TRACKS),
    RuleFigure("sforzando", FOUR_TRACKS),
    RuleFigure("lochlaenge", [("sforzando", "on"), ("sforzando", "off")], hole_spans=True),
    RuleFigure("sforzando-crescendo", FOUR_TRACKS),
    RuleFigure("mezzoforte", SIX_TRACKS, show_pin=True),
]


def render_rule(figure, emu_dir: Path, out_dir: Path, soundfont: Path):
    data = json.loads((emu_dir / f"{figure.name}.json").read_text())
    frame, solid, ghost = rule_images(data, figure)
    solid.save(out_dir / f"{figure.name}.png", optimize=True)
    with tempfile.TemporaryDirectory() as scratch:
        midi_path, wav_path = Path(scratch) / "a.mid", Path(scratch) / "a.wav"
        write_midi(rule_notes(data), midi_path)
        render_audio(midi_path, wav_path, soundfont)
        write_video(frame, solid, ghost, wav_path, out_dir / f"{figure.name}.mp4")
    print("rendered", figure.name)


# --- The Backhaus excerpt: the line the instrument drew, and the notes ---

@dataclass(frozen=True)
class DrawnLine:
    """The traced Handnuancierung, in seconds and on the roll's printed scale."""

    seconds: list
    bass: list
    treble: list

    def travel_at(self, half: str, t: float) -> float:
        piano, forte = RAILS[half]
        index = min(bisect.bisect_left(self.seconds, t), len(self.seconds) - 1)
        value = getattr(self, half)[index]
        return min(max((value - piano) / (forte - piano), 0.0), 1.0)


def drawn_line(path: Path, data, step=5) -> DrawnLine:
    with path.open() as handle:
        rows = [r for r in csv.DictReader(handle) if data["startRow"] <= int(r["y_px"]) <= data["lastRow"]][::step]

    def seconds_of_row(row):
        index = min(bisect.bisect_left(data["rows"], row), len(data["rows"]) - 1)
        return data["seconds"][index]

    return DrawnLine(
        seconds=[seconds_of_row(int(r["y_px"])) for r in rows],
        bass=[float(r["bass_value"]) for r in rows],
        treble=[float(r["treble_value"]) for r in rows],
    )


def backhaus_images(data, line: DrawnLine, seconds_limit):
    frame = Frame(width=1664, height=700, left=150, right=24, seconds=seconds_limit)
    panels = {"treble": (40, 220), "bass": (480, 660)}
    keys_top, keys_bottom = 250, 450
    low, high = 24, 103
    notes = [n for n in data["notes"] if n["on"] <= seconds_limit]
    visible = [i for i, t in enumerate(line.seconds) if t <= seconds_limit]

    def note_color(note, show_lines, ghosted):
        if ghosted and show_lines:
            return GHOST
        if not show_lines:
            return GHOST if ghosted else INK
        return BASS if note["half"] == "bass" else TREBLE

    def draw_one(show_lines, ghosted):
        image = Image.new("RGB", (frame.width * SCALE, frame.height * SCALE), "white")
        draw = ImageDraw.Draw(image)
        for top, bottom in panels.values():
            draw_scale_lines(draw, frame, top, bottom, [(1, "ff", "thick"), (0.5, "mf", "thin"), (0, "pp", "thick")])
        for note in notes:
            y = keys_bottom - (keys_bottom - keys_top) * (note["key"] - low) / (high - low)
            x0 = frame.x(note["on"])
            x1 = max(frame.x(min(note["off"], seconds_limit)), x0 + 6 * SCALE)
            draw.rounded_rectangle([x0, (y - 3) * SCALE, x1, (y + 3) * SCALE], radius=3 * SCALE, fill=note_color(note, show_lines, ghosted))
        if show_lines:
            for half, color in (("treble", TREBLE), ("bass", BASS)):
                top, bottom = panels[half]
                values = getattr(line, half)
                points = [(frame.x(line.seconds[i]), SCALE * (bottom - (bottom - top) * values[i])) for i in visible]
                draw.line(points, fill=GHOST if ghosted else color, width=5 * SCALE, joint="curve")
        return image

    return frame, draw_one


def backhaus_notes(data, line: DrawnLine, seconds_limit, dynamic: bool):
    def vel(note):
        return velocity(line.travel_at(note["half"], note["on"])) if dynamic else 64

    return [Note(n["key"], n["on"], n["off"], vel(n)) for n in data["notes"] if n["on"] <= seconds_limit]


def backhaus_pedal(data, seconds_limit):
    samples = [(t, round(d * 8) / 8) for t, d in zip(data["seconds"], data["damper"]) if t <= seconds_limit]
    return [s for previous, s in zip([(None, None)] + samples, samples) if s[1] != previous[1]]


def render_backhaus(emu_dir: Path, out_dir: Path, soundfont: Path, curves_csv: Path, seconds_limit=20.0):
    data = json.loads((emu_dir / "backhaus-3309.json").read_text())
    line = drawn_line(curves_csv, data)
    frame, draw_one = backhaus_images(data, line, seconds_limit)
    versions = {
        "backhaus-toene": (False, backhaus_notes(data, line, seconds_limit, False), None),
        "backhaus-dynamik": (True, backhaus_notes(data, line, seconds_limit, True), backhaus_pedal(data, seconds_limit)),
    }
    for name, (show_lines, notes, pedal) in versions.items():
        solid, ghost = draw_one(show_lines, False), draw_one(show_lines, True)
        solid.save(out_dir / f"{name}.png", optimize=True)
        with tempfile.TemporaryDirectory() as scratch:
            midi_path, wav_path = Path(scratch) / "a.mid", Path(scratch) / "a.wav"
            write_midi(notes, midi_path, pedal)
            render_audio(midi_path, wav_path, soundfont)
            write_video(frame, solid, ghost, wav_path, out_dir / f"{name}.mp4")
        print("rendered", name)


def render_pedal(emu_dir: Path, out_dir: Path, seconds_limit=12.0):
    """The damper of the Backhaus excerpt: it knows up and down, nothing between."""
    data = json.loads((emu_dir / "backhaus-3309.json").read_text())
    tracks = [("sustainPedal", "on"), ("sustainPedal", "off")]
    punches = [p for p in data["punches"] if p["on"] <= seconds_limit]
    frame = Frame(width=1664, height=520, left=250, right=24, seconds=seconds_limit)
    top, bottom, paper_top = 40, 260, 320
    image = Image.new("RGB", (frame.width * SCALE, frame.height * SCALE), "white")
    draw = ImageDraw.Draw(image)
    draw_guides(draw, frame, punches, tracks, top, paper_top, half="treble")
    label_font = font(PLEX, 26)
    for value, label in ((1, "gehoben"), (0, "auf den Saiten")):
        y = SCALE * (bottom - (bottom - top) * value)
        draw.line([(frame.x(0) - 12 * SCALE, y), (frame.width * SCALE - frame.right * SCALE, y)], fill=INK, width=4 * SCALE)
        draw.text((frame.x(0) - 32 * SCALE, y), label, font=label_font, fill=GRAY, anchor="rm")
    paper_bottom = draw_paper(draw, frame, punches, tracks, paper_top, 44, half="treble")
    visible = [i for i, t in enumerate(data["seconds"]) if t <= seconds_limit]
    points = curve_points(frame, [data["seconds"][i] for i in visible], [data["damper"][i] for i in visible], top, bottom)
    draw.line(points, fill=TREBLE, width=5 * SCALE, joint="curve")
    image.crop((0, 0, frame.width * SCALE, (paper_bottom + 16) * SCALE)).save(out_dir / "pedal.png", optimize=True)
    print("rendered pedal")


def main():
    emu_dir, out_dir, soundfont, curves_csv = map(Path, sys.argv[1:5])
    out_dir.mkdir(parents=True, exist_ok=True)
    [render_rule(figure, emu_dir, out_dir, soundfont) for figure in RULES]
    render_backhaus(emu_dir, out_dir, soundfont, curves_csv)
    render_pedal(emu_dir, out_dir)


if __name__ == "__main__":
    main()
