"""Parse the crawled Welte-Mignon catalogue pages into JSON rows."""

import html
import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"<tr\s+class=\"(?:even|odd)\">(.*?)</tr>", re.S)
CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
PERSON = re.compile(r"<div[^>]*>(.*?)</div>\s*(?:&nbsp;\(([^)]*)\))?", re.S)


def text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def people(cell: str) -> list[dict]:
    return [{"name": text(name), "dates": text(dates or "")} for name, dates in PERSON.findall(cell)]


def rows(page: str):
    for row in ROW.findall(page):
        cells = CELL.findall(row)
        if len(cells) < 8:
            continue
        _, number, composer, performer, title, recorded, catalogue, remark = cells[:8]
        yield {
            "number": text(number),
            "composers": people(composer),
            "performers": people(performer),
            "title": text(title),
            "recorded": text(recorded),
            "catalogue": text(catalogue),
            "remark": text(remark),
        }


def main(page_dir: str, out: str) -> None:
    pages = sorted(Path(page_dir).glob("p*.html"))
    all_rows = [r for p in pages for r in rows(p.read_text(encoding="utf-8", errors="replace"))]
    Path(out).write_text(json.dumps(all_rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(pages)} pages, {len(all_rows)} rows")


if __name__ == "__main__":
    main(*sys.argv[1:])
