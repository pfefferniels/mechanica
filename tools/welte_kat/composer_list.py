"""Curated list of composers playing their own works, from the parsed Freiburg catalogue."""

import json
import re
import sys
from collections import defaultdict

from self_played import distinct, fold, is_self_played

EXCLUDED = {
    "diverse",
    "D'Albert s. Albert",  # cross-reference row without a roll
    "Carroll / Wheeler",  # catalogue names Wheeler, the roll Carroll
}
# Composer field names Josef Pembaur sen., the performer is his son.
EXCLUDED_ROWS = {("3269", "Pembaur, Josef jun."), ("3272", "Pembaur, Josef jun.")}
# (number, performer) pairs the name match misses.
ADDED_ROWS = {
    ("0574", "Stenhammar, Wilhelm"): "Stenhammar, Vilhelm/Wilhelm",
    ("3650", "Zadora, Michael von"): None,
    ("3651", "Zadora, Michael von"): None,
}
DISPLAY = {
    "Europe & Dabney": "Europe, James Reese",
    "Weingartner, Felix, Edler von Münzberg": "Weingartner, Felix",
    "Feldmann, K. W.": "Feldmann, K. W.",
    "Lászlò, Sándor": "László, Sándor",
    "Hermanns, Hans & Hermanns-Stibbe, Marie": "Hermanns, Hans",
    "Motta, José Vianna da": "Vianna da Motta, José",
    "Egville, Louis Henry D. d'": "d'Egville, Louis",
    "Stenhammar, Wilhelm": "Stenhammar, Wilhelm",
    "Beck, James Montgomery jr.": "Beck, James M. jr.",
    "Cor de Las, Alonso": "Cor de Las, Alonso",
}
PARTICLES = {"von", "d'", "de", "da", "jr."}
DATES = {"Europe & Dabney": "1881-1919", "Hermanns, Hans & Hermanns-Stibbe, Marie": "1879-"}


def short(name: str) -> str:
    if name in DISPLAY:
        return DISPLAY[name]
    surname, _, given = (s.strip() for s in name.partition(","))
    words = given.replace(",", " ").split()
    tail = [w for w in words[1:] if w in PARTICLES]
    return f"{surname}, {' '.join(words[:1] + tail)}" if words else surname


def dates(raw: str) -> str:
    return raw.replace("-", "–")


def entries(rows: list[dict]) -> list[dict]:
    by_person = defaultdict(lambda: {"numbers": set(), "dates": ""})
    for r in rows:
        performer = r["performers"][0]
        key = (r["number"], performer["name"])
        own = is_self_played(r) and key not in EXCLUDED_ROWS and performer["name"] not in EXCLUDED
        if not (own or key in ADDED_ROWS) or not r["number"]:
            continue
        person = by_person[performer["name"]]
        person["numbers"].add(r["number"])
        person["dates"] = performer["dates"] or DATES.get(performer["name"], "")
    return sorted(
        ({"name": short(n), "dates": dates(p["dates"]), "numbers": sorted(p["numbers"])} for n, p in by_person.items()),
        key=lambda e: fold(e["name"].replace("d'", "")),
    )


def main(path: str, out: str) -> None:
    rows = distinct(json.load(open(path, encoding="utf-8")))
    result = entries(rows)
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for e in result:
        print(f"{e['name']} ({e['dates']}) {len(e['numbers'])}: {', '.join(e['numbers'])}")
    print(len(result), "persons,", sum(len(e["numbers"]) for e in result), "roll numbers")


if __name__ == "__main__":
    main(*sys.argv[1:])
