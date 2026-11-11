"""Gottschewski's half-bar beat times for Chopin op. 15/2 from SUPRA roll MIDI.

Rules after Gottschewski 1996, S. 269f.: outer sections take the left-hand attack
(upper note of an octave), the middle section (T. 25–48) the top right-hand note.
"""

from __future__ import annotations

import json
import statistics
import sys
from dataclasses import dataclass, asdict
from functools import reduce
from itertools import groupby
from pathlib import Path

import librosa
import mido
import music21 as m21
import numpy as np

BARS = 62
UPBEAT = 0.5  # quarter lengths before bar 1
MIDDLE = range(25, 49)
EVENT_GAP = 0.035  # s; roll notes closer than this form one event
SEARCH = 1.0  # s; window around the aligned time for a beat note
MIN_GAP = 0.15  # s; a half bar is never shorter than this


@dataclass(frozen=True, order=True)
class ScoreNote:
    offset: float
    pitch: int
    left_hand: bool


@dataclass(frozen=True, order=True)
class RollNote:
    time: float
    pitch: int
    end: float


@dataclass(frozen=True)
class Beat:
    bar: int
    half: int
    pitch: int | None
    time: float
    inferred: bool = False


def score_notes(path: Path) -> list[ScoreNote]:
    score = m21.converter.parse(str(path))
    left = min(score.parts, key=lambda part: statistics.mean(p.midi for p in part.pitches))
    return sorted(
        ScoreNote(float(n.getOffsetInHierarchy(score)), p.midi, part is left)
        for part in score.parts
        for n in part.recurse().notes
        if not n.duration.isGrace
        for p in n.pitches
        if not tied_over(n, p)
    )


def tied_over(note: m21.note.GeneralNote, pitch: m21.pitch.Pitch) -> bool:
    """True for a pitch that continues a tie and is therefore not struck."""
    tie = note.tie if note.isNote else next(
        (n.tie for n in note.notes if n.pitch == pitch), None)
    return tie is not None and tie.type in ("stop", "continue")


def roll_notes(path: Path) -> list[RollNote]:
    """Note-ons with absolute seconds, tempo map (roll acceleration) applied."""
    midi = mido.MidiFile(str(path))
    clock = np.cumsum([msg.time for msg in midi])
    messages = list(midi)
    ons = [(t, m) for t, m in zip(clock, messages) if m.type == "note_on" and m.velocity > 0]
    offs = [(t, m) for t, m in zip(clock, messages)
            if m.type == "note_off" or (m.type == "note_on" and m.velocity == 0)]

    def release(start: float, pitch: int) -> float:
        return next((t for t, m in offs if m.note == pitch and t > start), start)

    return sorted(RollNote(float(t), m.note, float(release(t, m.note))) for t, m in ons)


def events(onsets: list[tuple[float, int]], gap: float) -> list[tuple[float, frozenset[int]]]:
    """Group (time, pitch) pairs into onset events, starting a new one after `gap`."""
    starts = [t for t, _ in onsets]
    labels = np.cumsum([0] + [b - a > gap for a, b in zip(starts, starts[1:])])
    grouped = groupby(zip(labels, onsets), key=lambda item: item[0])
    return [
        (members[0][1][0], frozenset(p for _, (_, p) in members))
        for members in (list(g) for _, g in grouped)
    ]


def pitch_matrix(evts: list[tuple[float, frozenset[int]]]) -> np.ndarray:
    """One column per event: exact pitches plus half weight for their pitch class."""
    exact = np.zeros((128, len(evts)))
    chroma = np.zeros((12, len(evts)))
    for column, (_, pitches) in enumerate(evts):
        exact[list(pitches), column] = 1
        chroma[[p % 12 for p in pitches], column] = 1
    return np.vstack([exact, 0.5 * chroma])


def align(score: list[ScoreNote], roll: list[RollNote]) -> dict[float, float]:
    """Map each score offset to a roll time by DTW over onset events."""
    score_events = events([(n.offset, n.pitch) for n in score], 1e-6)
    roll_events = events([(n.time, n.pitch) for n in roll], EVENT_GAP)
    _, path = librosa.sequence.dtw(
        X=pitch_matrix(score_events), Y=pitch_matrix(roll_events), metric="cosine"
    )
    pairs = sorted((score_events[i][0], roll_events[j][0]) for i, j in path)
    return {offset: statistics.median(t for _, t in group)
            for offset, group in groupby(pairs, key=lambda p: p[0])}


def beat_offsets() -> list[tuple[int, int, float]]:
    """(bar, half, score offset) for every half bar from T. 1 to the final note of T. 62."""
    return [(bar, half, UPBEAT + 2 * (bar - 1) + half)
            for bar in range(1, BARS + 1) for half in (0, 1)
            if (bar, half) != (BARS, 1)]


def beat_pitches(notes: list[ScoreNote], bar: int, offset: float) -> list[int]:
    """Pitches struck on this half bar, Gottschewski's choice first, then fallbacks."""
    at_beat = [n for n in notes if abs(n.offset - offset) < 1e-6]
    right = sorted((n.pitch for n in at_beat if not n.left_hand), reverse=True)
    left = sorted(n.pitch for n in at_beat if n.left_hand)
    if len(left) > 1 and left[1] - left[0] == 12:
        left = [left[1], left[0], *left[2:]]
    return right + left if bar in MIDDLE else left + right


@dataclass(frozen=True)
class Candidate:
    pitch: int
    time: float
    rank: int  # 0 written pitch, 1 its octave, 2 lowest attack, 3 other written pitch


RANK_COST = (0.0, 0.5, 1.0, 1.5)  # s of misalignment a weaker reading is worth
SMOOTHNESS = 0.25  # weight of tempo jumps against the aligned estimate


def lowest_attacks(roll: list[RollNote], around: float, window: float = 0.4) -> list[RollNote]:
    """Per onset event near `around` its lowest note; of a bass octave, the upper one."""
    near = [n for n in roll if abs(n.time - around) <= window]
    grouped = events([(n.time, n.pitch) for n in near], EVENT_GAP)
    lowest = [(t, sorted(pitches)) for t, pitches in grouped]
    return [RollNote(t, p[1] if len(p) > 1 and p[1] - p[0] == 12 else p[0], t)
            for t, p in lowest]


def candidates(roll: list[RollNote], written: list[int], around: float,
               bass: bool) -> list[Candidate]:
    def matching(pitches: set[int], rank: int) -> list[Candidate]:
        return [Candidate(n.pitch, n.time, rank) for n in roll
                if n.pitch in pitches and abs(n.time - around) <= SEARCH]

    octaves = {written[0] + shift for shift in (-12, 12, -24, 24)}
    low = [Candidate(n.pitch, n.time, 2) for n in lowest_attacks(roll, around)] if bass else []
    return (matching({written[0]}, 0) + matching(octaves, 1) + low
            + matching(set(written[1:]), 3))


def best_path(columns: list[list[Candidate]], estimates: list[float]) -> list[Candidate]:
    """Viterbi: ascending times, close to the estimates, smooth relative to them."""
    def unary(column: list[Candidate], estimate: float) -> np.ndarray:
        return np.array([abs(c.time - estimate) + RANK_COST[c.rank] for c in column])

    def step(state, k):
        cost, back = state
        prev, here = columns[k - 1], columns[k]
        expected = max(estimates[k] - estimates[k - 1], 0.05)
        gaps = np.array([[c.time - p.time for c in here] for p in prev])
        jump = np.where(gaps > MIN_GAP,
                        SMOOTHNESS * np.abs(np.log(np.maximum(gaps, 1e-3) / expected)), np.inf)
        total = cost[-1][:, None] + jump
        return ([*cost, total.min(axis=0) + unary(here, estimates[k])],
                [*back, total.argmin(axis=0)])

    cost, back = reduce(step, range(1, len(columns)), ([unary(columns[0], estimates[0])], []))
    last = int(np.argmin(cost[-1]))
    if not np.isfinite(cost[-1][last]):
        raise LookupError("no ascending sequence of beat notes found")
    chosen = reduce(lambda path, k: [int(back[k][path[0]]), *path],
                    range(len(back) - 1, -1, -1), [last])
    return [column[i] for column, i in zip(columns, chosen)]


def beats(score: list[ScoreNote], roll: list[RollNote]) -> tuple[list[Beat], list[str]]:
    """Beat times plus a remark for every beat that needed a fallback reading."""
    mapping = align(score, roll)
    offsets = np.array(sorted(mapping))
    times = np.array([mapping[o] for o in offsets])
    positions = beat_offsets()
    written = [beat_pitches(score, bar, offset) for bar, _, offset in positions]
    struck = [k for k, w in enumerate(written) if w]
    estimates = [float(np.interp(positions[k][2], offsets, times)) for k in struck]
    columns = [candidates(roll, written[k], e, bass=positions[k][0] not in MIDDLE)
               for k, e in zip(struck, estimates)]
    empty = [positions[k][:2] for k, column in zip(struck, columns) if not column]
    if empty:
        raise LookupError(f"no candidate notes for {empty}")
    chosen = dict(zip(struck, best_path(columns, estimates)))
    found = [Beat(bar, half, chosen[k].pitch, chosen[k].time) if k in chosen else None
             for k, (bar, half, _) in enumerate(positions)]
    complete = reduce(fill_rest, enumerate(found), [])
    remarks = [f"T. {b.bar}/{b.half + 1}: written {written[k][0]}, roll {b.pitch} at {b.time:.2f}s"
               for k, b in enumerate(complete) if not b.inferred and b.pitch != written[k][0]]
    remarks += [f"T. {b.bar}/{b.half + 1}: no attack written, ritardando continued"
                for b in complete if b.inferred]
    return complete, remarks


def fill_rest(earlier: list[Beat], item: tuple[int, Beat | None]) -> list[Beat]:
    k, beat = item
    if beat is not None:
        return [*earlier, beat]
    bar, half, _ = beat_offsets()[k]
    return [*earlier, Beat(bar, half, None, continued(earlier), inferred=True)]


def continued(earlier: list[Beat]) -> float:
    """Next time point if the last half-bar ratio continues (Gottschewski S. 260 for Pugno)."""
    a, b, c = (x.time for x in earlier[-3:])
    last = c - b
    return c + last * last / (b - a)


def main(krn: str, midi: str, out: str) -> None:
    result, remarks = beats(score_notes(Path(krn)), roll_notes(Path(midi)))
    Path(out).write_text(json.dumps([asdict(b) for b in result], indent=1))
    durations = np.diff([b.time for b in result])
    print(f"{len(result)} beats, half-bar durations {durations.min():.2f}–{durations.max():.2f}s")
    print("\n".join(remarks))


if __name__ == "__main__":
    main(*sys.argv[1:4])
