"""Builds the static site: the deck as one page with a viewer, and the two apps beside it.

The deck in deck/ is a copy of the files of the Slides artifact (deck.json and one
<section> per slide in slides/, speaker notes in its <aside>); media referenced
as /_blob/<id> lie in assets/. The notes show only in the presenter window.
The apps are artifact pages without a document shell, so they are wrapped here.

Usage: python3 tools/site/build_site.py <repo-root> <out-dir>
"""
import json
import re
import shutil
import sys
from html import escape
from pathlib import Path

from bs4 import BeautifulSoup

BLOB = re.compile(r"/_blob/([0-9a-f]{32})")
HAS_DISPLAY = re.compile(r"(^|;)\s*display\s*:")
YOUTUBE = re.compile(r"youtube\.com/watch\?v=([\w-]+)")
TIME_RANGE = re.compile(r"(\d+):(\d\d)\s*[–-]\s*(\d+):(\d\d)")
ASSET = re.compile(r"assets/([0-9a-f]{32}\.\w+)")
VIDEO_ATTRIBUTES = ["data-video", "data-video-sound", "data-video-start"]
APP_LINKS = {
    "https://claude.ai/artifact/PDChzSTLwMAaFkL7jzapCu": "rollenlabor/",
    "https://claude.ai/artifact/1AfxLvyg6ofVCq7LFXYT9p": "skyline/",
}
APPS = {"rollenlabor": "Rollenlabor", "skyline": "Skyline-Werkstatt"}
APP_SKIP = {"build", "README.md"}


def asset_paths(assets):
    return {path.stem: f"assets/{path.name}" for path in assets.iterdir() if path.is_file()}


def localised(text, assets):
    with_media = BLOB.sub(lambda match: assets.get(match.group(1), match.group(0)), text)
    return re.sub("|".join(map(re.escape, APP_LINKS)), lambda match: APP_LINKS[match.group(0)], with_media)


# The slide format lays out a section or div without `display` as a flex column.
def with_default_display(tag):
    style = tag.get("style", "")
    if not HAS_DISPLAY.search(style):
        tag["style"] = f"display:flex;flex-direction:column;{style}"


# The viewer sets src on the slides near the current one only.
def deferred(img):
    if img.has_attr("src"):
        img["data-src"] = img["src"]
        del img["src"]


def seconds(minutes, secs):
    return int(minutes) * 60 + int(secs)


# A clip cut from a YouTube video is shown through YouTube's player, over the cited time range.
def youtube_source(section):
    text = section.get_text(" ")
    ids = set(YOUTUBE.findall(text))
    if len(ids) != 1:
        return None
    span = TIME_RANGE.search(text)
    return {"data-youtube": ids.pop(), **({"data-start": seconds(*span.groups()[:2]), "data-end": seconds(*span.groups()[2:])} if span else {})}


def embedded(img, source):
    [img.attrs.pop(name, None) for name in VIDEO_ATTRIBUTES]
    img.attrs.update({name: str(value) for name, value in source.items()})


def with_youtube_player(section):
    clips = [img for img in section.find_all("img") if img.has_attr("data-video")]
    source = youtube_source(section)
    if source and len(clips) == 1:
        embedded(clips[0], source)


def slide_markup(path, assets, number):
    soup = BeautifulSoup(localised(path.read_text(encoding="utf-8"), assets), "html.parser")
    section = soup.find("section")
    [with_default_display(tag) for tag in [section, *section.find_all("div")]]
    with_youtube_player(section)
    [deferred(img) for img in section.find_all("img")]
    missing = BLOB.findall(str(section))
    if missing:
        raise SystemExit(f"{path.name}: media not in assets/: {', '.join(missing)}")
    section["class"] = "slide"
    section["data-number"] = str(number)
    return str(section)


def contents_markup(deck, numbers):
    starts = sorted(deck["sections"].values(), key=lambda section: numbers.get(section["start"], 0))
    items = [
        f'<li><a href="#slide-{numbers[section["start"]]}">{numbers[section["start"]]}</a> {escape(section["description"])}</li>'
        for section in starts if section["start"] in numbers
    ]
    return "\n".join(items)


def deck_page(root, deck, slides, contents):
    faces = "\n".join(f'<link rel="stylesheet" href="{escape(face["href"])}">' for face in deck["faces"].values() if "href" in face)
    apps = " ".join(f'<a href="{folder}/">{name}</a>' for folder, name in APPS.items())
    template = (root / "viewer" / "deck.html").read_text(encoding="utf-8")
    return (template
            .replace("{{title}}", escape(deck["title"]))
            .replace("{{faces}}", faces)
            .replace("{{slides}}", "\n".join(slides))
            .replace("{{contents}}", contents)
            .replace("{{apps}}", apps))


def build_deck(root, out):
    deck = json.loads((root / "deck" / "deck.json").read_text(encoding="utf-8"))
    assets = asset_paths(root / "assets")
    order = [slide for slide in deck["order"] if (root / "deck" / "slides" / f"{slide}.html").exists()]
    numbers = {slide: index + 1 for index, slide in enumerate(order)}
    slides = [slide_markup(root / "deck" / "slides" / f"{slide}.html", assets, numbers[slide]) for slide in order]
    (out / "index.html").write_text(deck_page(root, deck, slides, contents_markup(deck, numbers)), encoding="utf-8")
    (out / "assets").mkdir()
    [shutil.copyfile(root / "assets" / name, out / "assets" / name) for name in sorted(set(ASSET.findall("".join(slides))))]
    shutil.copytree(root / "viewer", out / "viewer", ignore=shutil.ignore_patterns("deck.html"))
    return len(slides)


def document(page):
    return ("<!doctype html>\n<html lang=\"de\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"</head>\n<body>\n{page}\n</body>\n</html>\n")


def build_app(root, out, folder):
    shutil.copytree(root / folder, out / folder, ignore=shutil.ignore_patterns(*APP_SKIP))
    page = out / folder / "index.html"
    page.write_text(document(page.read_text(encoding="utf-8")), encoding="utf-8")


def main(root_dir, out_dir):
    root = Path(root_dir)
    out = Path(out_dir)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    count = build_deck(root, out)
    [build_app(root, out, folder) for folder in APPS]
    (out / ".nojekyll").write_text("")
    print(f"{count} slides, apps: {', '.join(APPS)} -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
