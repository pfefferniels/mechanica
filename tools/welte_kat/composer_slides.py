"""Two list slides in the deck's format from composers.json."""

import json
import sys
from html import escape

ROWS = 18
COLUMNS = 3
SECTION = (
    '<section id="{id}" data-transition="fade" style="background:#ffffff;color:#000000;'
    "font-family:'IBM Plex Mono', 'Courier New', monospace;padding:64px 64px 160px;"
    'display:flex;flex-direction:column;gap:40px">'
)
TITLE = (
    "<h2 style=\"font-family:'IBM Plex Mono', 'Courier New', monospace;font-size:56px;"
    'font-weight:500;line-height:1.1">Eigene Werke auf Welte-Mignon · {span}</h2>'
)
CAPTION = (
    '<p style="position:absolute;left:64px;bottom:36px;width:1792px;font-size:24px;line-height:1.35">'
    "Alle Rollen, auf denen Komponist und Interpret dieselbe Person sind, Namensformen und Lebensdaten "
    "nach: <i>Verzeichnis der WELTE-MIGNON-Reproduktionsrollen</i>, Datenbank, Augustinermuseum Freiburg "
    "und Universitätsbibliothek Freiburg, https://www.welte-mignon.de/kat/, abgerufen am 10.11.2026.</p>"
)


def line(e: dict) -> str:
    years = f" ({e['dates']})" if e["dates"] else ""
    return f'<p style="font-size:24px;line-height:1.3">{escape(e["name"] + years, quote=False)}</p>'


def column(entries: list[dict]) -> str:
    return '<div style="flex:1;display:flex;flex-direction:column">' + "".join(map(line, entries)) + "</div>"


def numbers(entries: list[dict]) -> str:
    return "; ".join(f"{e['name'].split(',')[0]} {', '.join(e['numbers'])}" for e in entries)


def slide(slide_id: str, entries: list[dict], notes: str) -> str:
    span = f"{entries[0]['name'][0].upper()}–{entries[-1]['name'][0].upper()}"
    columns = [entries[i:i + ROWS] for i in range(0, len(entries), ROWS)]
    return "\n".join([
        SECTION.format(id=slide_id),
        TITLE.format(span=span),
        '<div style="display:flex;flex-direction:row;gap:48px">' + "".join(map(column, columns)) + "</div>",
        CAPTION,
        f"<aside>{escape(notes, quote=False)}\nRollennummern: {numbers(entries)}.</aside>",
        "</section>",
    ])


def main(path: str, notes_path: str, out_dir: str) -> None:
    entries = json.load(open(path, encoding="utf-8"))
    notes = open(notes_path, encoding="utf-8").read().split("\n---\n")
    per_slide = ROWS * COLUMNS
    for n, (start, note) in enumerate(zip(range(0, len(entries), per_slide), notes), 1):
        html = slide(f"komp-{n}", entries[start:start + per_slide], note.strip())
        open(f"{out_dir}/komp-{n}.html", "w", encoding="utf-8").write(html + "\n")
        print(f"komp-{n}: {len(entries[start:start + per_slide])} entries, {len(html)} chars")


if __name__ == "__main__":
    main(*sys.argv[1:])
