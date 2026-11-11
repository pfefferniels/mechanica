"""Rolls on which the performer is the composer, grouped by person."""

import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass


ANONYMOUS = {"unbekannt", "unknown", "anonym", "anonymous"}


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if c.isalnum() or c == " ").strip()


@dataclass(frozen=True)
class Name:
    surname: str
    given: str

    @classmethod
    def parse(cls, raw: str) -> "Name":
        surname, _, given = raw.partition(",")
        return cls(fold(surname), fold(given))

    def same_person(self, other: "Name") -> bool:
        initials_agree = not self.given or not other.given or self.given[:1] == other.given[:1]
        return self.surname == other.surname and initials_agree


def names(people: list[dict]) -> list[Name]:
    raw = [part for p in people for part in re.split(r"\s+(?:&|/|und)\s+", p["name"])]
    return [n for n in map(Name.parse, raw) if n.surname and n.surname not in ANONYMOUS]


def is_self_played(row: dict) -> bool:
    return any(c.same_person(p) for c in names(row["composers"]) for p in names(row["performers"]))


def surname_only_matches(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if not is_self_played(r)
        and any(c.surname == p.surname for c in names(r["composers"]) for p in names(r["performers"]))
    ]


def is_own_arrangement(row: dict) -> bool:
    """Performer named inside the composer field or title, e.g. 'Strauß, J.-Grünfeld'."""
    composer_field = fold(" ".join(c["name"] for c in row["composers"]))
    title = fold(row["title"])
    return not is_self_played(row) and any(
        len(p.surname) > 3 and (p.surname in composer_field or p.surname in title)
        for p in names(row["performers"])
    )


def distinct(rows: list[dict]) -> list[dict]:
    keyed = {(r["number"], r["title"], r["performers"][0]["name"]): r for r in rows}
    return list(keyed.values())


def main(path: str) -> None:
    rows = distinct(json.load(open(path, encoding="utf-8")))
    print(f"{len(rows)} distinct rows")
    by_person = defaultdict(list)
    for r in filter(is_self_played, rows):
        p = r["performers"][0]
        by_person[(p["name"], p["dates"])].append(r)
    for (name, dates), rs in sorted(by_person.items(), key=lambda kv: fold(kv[0][0])):
        numbers = ", ".join(sorted((r["number"] for r in rs), key=lambda n: (len(n), n)))
        print(f"{name} ({dates}) | {len(rs)} | {numbers}")
    print(f"\n{len(by_person)} persons, {sum(map(len, by_person.values()))} rolls")
    print("\n# surname matches with different given name")
    for r in surname_only_matches(rows):
        print(r["number"], "|", r["composers"][0]["name"], "|", r["performers"][0]["name"], "|", r["title"][:70])
    print("\n# own arrangements")
    for r in filter(is_own_arrangement, rows):
        print(r["number"], "|", r["composers"][0]["name"], "|", r["performers"][0]["name"], "|", r["title"][:90])


if __name__ == "__main__":
    main(*sys.argv[1:])
