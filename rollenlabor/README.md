# Rollenlabor

A page for measuring red Welte rolls (T-100) on Stanford's SUPRA scans: the
scan itself as the working surface, with the holes from SUPRA laid over it
(clickable, expression tracks coloured and labelled), marks with distances,
times and notes, the emulated bellows travel of bass and treble, and playback
of the emulated performance.

Published as https://claude.ai/artifact/PDChzSTLwMAaFkL7jzapCu (private).

## Adding a roll

```
node build/build-roll.mjs <druid> [<druid> …]
```

This reads `<druid>_raw.mid` from `../../roll-nuance-tracer/cache/SUPRA/welte-red/midi-raw`
(or GitHub `pianoroll/SUPRA`), runs welte-mignon-emulator (consensus instrument,
Gottschewski's spool axis) and writes `data/<druid>.json`,
`audio/<druid>.mp3` and the entry in `rolls.json`. German title,
performer, recording date and notes for the selector come from
`build/catalogue.json`. Velocities follow `velocityOf` in linked-rolls. Audio is
rendered with fluidsynth and `~/Downloads/Dokumente/Full Grand Piano.sf2`.

Then the facsimile tiles, from `../tools/facsimile`:

```
node scan_meta.mjs ../../build/facsimile/meta.json <druid> […]
python3 -I tiles.py ../../build/facsimile/meta.json <druid> ../../rollenlabor/scan ../../build/facsimile/manifests
python3 -I calibrate.py <region.jpg> ../../rollenlabor/data/<druid>.json <row0> 0.5 <FIRST_HOLE> <HOLE_SEPARATION>
python3 -I merge_scan.py ../../rollenlabor ../../build/facsimile/manifests ../../build/facsimile/meta.json ../../build/facsimile/calibration.json
```

`tiles.py` fetches the scan from Stanford's IIIF service at half resolution,
rotates it so the roll runs left to right with the bass at the bottom, and
writes four WebP levels. `calibrate.py` fits the image column of each MIDI key
on a 6000-row region fetched just before the first hole (`<row0>` = its first row);
its `offset` goes into `calibration.json`. The hole numbering of the scanning
software differs between rolls, so the stated `HOLE_OFFSET` alone does not give
the column.

Then publish `index.html` with root `rollenlabor/` and `rolls.json`, `data/`,
`audio/` and `scan/` (not `build/` or this README). The folder is also the
`rollenlabor/` directory of the GitHub Pages site.

## Axes

- mm along the roll: scan rows from the first hole divided by the scan's rows per mm (`LENGTH_DPI`); the leader has negative values.
- mm across the roll: image columns from the treble edge of the scan, at the same resolution.
- s: `secondsAtRow` of the emulator from the first hole. The audio is rendered on
  the same axis, so the cursor follows it exactly.
