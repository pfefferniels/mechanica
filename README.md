# Was wir von mechanischen Musikinstrumenten lernen können

Slides and two small analysis apps for the workshop „Was wir von mechanischen
Musikinstrumenten lernen können“ (Niels Pfeffer), ZHdK, HIPE Werkstatt 4,
11 November 2026.

Site: https://pfefferniels.github.io/mechanica/

- **Slides** (`/`): arrow keys or space to page, I for contents, F for full
  screen, S for the presenter window (speaker notes, next slide, timer; it
  stays in step with the main window, which shows no notes). A slide's address
  is `#slide-N`.
- **Rollenlabor** (`/rollenlabor/`): red Welte-Mignon rolls on Stanford's
  scans. Holes are clickable; marks give distances, times and notes; the
  emulated bellows travel of bass and treble runs under the roll; playback of
  the emulated performance.
- **Skyline-Werkstatt** (`/skyline/`): tap along, durations combined in pairs,
  drawn as SKYLINE2 (duration) or SKYLINE (tempo), after Hermann Gottschewski,
  *Die Interpretation als Kunstwerk*, Laaber 1996, S. 245–257 and 269 f. Its
  recordings: Gottschewski's examples from the website for his dissertation
  (fusehime.c.u-tokyo.ac.jp/gottschewski; Welte-Mignon rolls Reinecke 237,
  Saint-Saëns 807, Scharwenka 242, Pugno 548, Busoni 441), and Stanford
  University Libraries' audio for the Welte-Mignon rolls 207, 2979, 419, 1275,
  1208 and 2555 (Denis Condon Collection, SUPRA), accessed 10 November 2026.

## Layout

- `deck/`: `deck.json` and one `<section>` per slide, as written in the Slides
  artifact the workshop was presented from, with the speaker notes;
  `assets/` holds their images and videos.
- `viewer/`: page template, styles and script of the static slide viewer.
- `rollenlabor/`, `skyline/`: the apps (artifact pages; the build adds the
  document shell).
- `tools/`: the scripts behind figures, animations, the composer list from the
  Freiburg roll catalogue, the advertisement crops and the facsimile tiles.
  `tools/site/build_site.py` builds the site.

GitHub Actions builds and deploys the site on every push to `main`. To build it
locally:

```
pip install beautifulsoup4
python3 tools/site/build_site.py . _site
python3 -m http.server -d _site
```

## Sources and rights

Every slide names its sources in its caption, with licences where there are
any. Clips taken from YouTube videos are not stored here: those slides embed the
original video from YouTube over the cited time range. Figures from publications
are quoted with their full reference.

Roll scans, MIDI and audio renderings derive from the Stanford University
Libraries (Denis Condon Collection; SUPRA). SUPRA's MIDI files are licensed CC
BY-NC-SA 4.0; for publishing or reproducing items, Stanford asks to contact the
Stanford Archive of Recorded Sound. The audio in the apps is a FluidSynth
rendering of an emulation, not a recording of an instrument.
