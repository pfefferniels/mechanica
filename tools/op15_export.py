"""Write the beat data of the three SUPRA op. 15/2 rolls for the interactive SKYLINE page."""

import json
import sys
from pathlib import Path

from op15_skyline import beats, roll_notes, score_notes

AUDIO_LAG = 0.06  # s; SUPRA mp3 renderings start this much after the MIDI clock (measured)

ROLLS = [
    ("saintsaens", "Camille Saint-Saëns", 807, "tx963yw9164", 250),
    ("pugno", "Raoul Pugno", 548, "vm423wb2944", 177),
    ("busoni", "Ferruccio Busoni", 441, "wz719qg6993", 165),
]


def performance(supra: Path, score, key: str, name: str, number: int, druid: str, condon: int):
    roll = roll_notes(supra / f"{druid}_exp.mid")
    found, remarks = beats(score, roll)
    last = found[-1]
    final = next(n for n in roll if n.pitch == last.pitch and abs(n.time - last.time) < 1e-6)
    return {
        "key": key, "name": name, "roll": number, "druid": druid, "condon": condon,
        "audio": f"audio/{key}.mp3",
        "beats": [{"bar": b.bar, "half": b.half, "t": round(b.time + AUDIO_LAG, 3),
                   "pitch": b.pitch, "inferred": b.inferred} for b in found],
        "end": round(final.end + AUDIO_LAG, 3),
        "remarks": remarks,
    }


def main(supra: str, krn: str, out: str) -> None:
    score = score_notes(Path(krn))
    data = [performance(Path(supra), score, *r) for r in ROLLS]
    Path(out).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print("\n".join(f"{d['name']}: {len(d['beats'])} beats, {len(d['remarks'])} remarks" for d in data))


if __name__ == "__main__":
    main(*sys.argv[1:4])
