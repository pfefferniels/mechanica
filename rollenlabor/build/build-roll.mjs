// Prepares one red Welte roll for the roll analysis page: holes in mm, bellows
// travel of both halves, the time map, and an audio rendering of the emulated
// performance on the same time axis.
// Usage: node build/build-roll.mjs <druid> [<druid> …]

import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Grid, noteOff, noteOn, pedalMessages, setTempo, writeSmf } from "../../../welte-t100/dist/index.js";
import {
  aperturePorts, instrumentParameters, meaningOf, mezzoforteTravel, perforations,
  pixelsPerInch, pneumaticModel, readRoll, runPedals, travelBetweenRails,
} from "../../../welte-t100/dist/t100/index.js";
import { defaultVelocityMap, velocityOf } from "../../../linked-rolls/src/systems/velocity.ts";

const APP = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = APP;
const SUPRA_MIDI = join(APP, "../../roll-nuance-tracer/cache/SUPRA/welte-red/midi-raw");
const SUPRA_REMOTE = "https://raw.githubusercontent.com/pianoroll/SUPRA/master/welte-red/midi-raw";
const PIANOTEQ = "/Applications/Pianoteq 9/Pianoteq 9.app/Contents/MacOS/Pianoteq 9";
const PRESET = "NY Steinway D Classical";
const HALVES = ["bass", "treble"];
const STEP_MM = 1;
const RUN_OUT_ROWS = 600;
const TAIL_SECONDS = 2;

const CATALOGUE = JSON.parse(readFileSync(join(APP, "build/catalogue.json"), "utf8"));

const round = (x, digits) => Math.round(x * 10 ** digits) / 10 ** digits;
const decodeEntities = (text = "") => text
  .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
  .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(Number(dec)))
  .replace(/&amp;/g, "&");
const range = (n) => Array.from({ length: n }, (_, i) => i);

async function rawMidi(druid) {
  const local = join(SUPRA_MIDI, `${druid}_raw.mid`);
  if (existsSync(local)) return readFileSync(local);
  const response = await fetch(`${SUPRA_REMOTE}/${druid}_raw.mid`);
  if (!response.ok) throw new Error(`${druid}: no raw MIDI locally or on GitHub (${response.status})`);
  return new Uint8Array(await response.arrayBuffer());
}

// Pairs note-on and note-off per key; every pair is one (bridged) hole.
function holesOfTrack(roll, track) {
  const open = new Map();
  return roll.smf.tracks[track].flatMap((event) => {
    if (event.kind === "note-on") { open.set(event.key, event.tick); return []; }
    if (event.kind !== "note-off" || !open.has(event.key)) return [];
    const tickOn = open.get(event.key);
    open.delete(event.key);
    return [{ key: event.key, track, rowOn: roll.timing.rowAtTick(tickOn), rowOff: roll.timing.rowAtTick(event.tick) }];
  });
}

// On the six rolls, paper bridges leave gaps of at most 1.7 mm, repetitions at least 2.6 mm.
const BRIDGE_MM = 2;

function sameKeyRuns(holes) {
  const byKey = Map.groupBy(holes, (hole) => hole.key);
  return [...byKey.values()].map((run) => run.toSorted((a, b) => a.rowOn - b.rowOn));
}

function joinAcrossBridges(run, maxGapRows) {
  return run.reduce((notes, hole) => {
    const last = notes.at(-1);
    if (last && hole.rowOn - last.rowOff <= maxGapRows) {
      return [...notes.slice(0, -1), { ...last, rowOff: Math.max(last.rowOff, hole.rowOff) }];
    }
    return [...notes, hole];
  }, []);
}

function notesOfHoles(holes, rowsPerMm) {
  return sameKeyRuns(holes).flatMap((run) => joinAcrossBridges(run, BRIDGE_MM * rowsPerMm));
}

function emulate(roll, firstRow, lastRow) {
  const grid = Grid.overRows(roll.timing, firstRow, lastRow + RUN_OUT_ROWS);
  const ports = aperturePorts(grid, perforations(roll));
  const halfOf = (half) => {
    const params = instrumentParameters(half);
    const travel = travelBetweenRails(pneumaticModel.run({ grid, half, ports }, params), params);
    return { travel, hook: mezzoforteTravel(params) };
  };
  return { grid, nuance: Object.fromEntries(HALVES.map((half) => [half, halfOf(half)])), pedals: runPedals({ grid, ports }) };
}

function noteEvents(notes, emulation, secondsOf) {
  const velocityAt = (note) => {
    const { travel, hook } = emulation.nuance[note.track === 1 ? "bass" : "treble"];
    return Math.round(velocityOf(travel[emulation.grid.indexOfRow(note.rowOn)], hook, defaultVelocityMap));
  };
  const ms = (row) => Math.round(secondsOf(row) * 1000);
  return notes.flatMap((note) => [noteOn(ms(note.rowOn), 0, note.key, velocityAt(note)), noteOff(ms(note.rowOff), 0, note.key)]);
}

// Continuous CC 64 and 67: Pianoteq models half-pedal and the dampers' travel.
function pedalEvents(emulation, secondsOf) {
  const tickAt = (index) => Math.round(secondsOf(emulation.grid.rowAt(index)) * 1000);
  return pedalMessages(emulation.pedals, tickAt);
}

// A static gain keeps the rendering's dynamics; only the level is raised.
function peakDb(wavPath) {
  const { stderr } = spawnSync("ffmpeg", ["-i", wavPath, "-af", "volumedetect", "-f", "null", "-"], { encoding: "utf8" });
  return Number(/max_volume: (-?[\d.]+) dB/.exec(stderr)[1]);
}

// One tick per millisecond: division 1000 at 60 bpm.
function renderAudio(druid, events) {
  const midiPath = join(OUT, "audio", `${druid}.mid`);
  const wavPath = join(OUT, "audio", `${druid}.wav`);
  const sorted = [setTempo(0, 1_000_000), ...events].sort((a, b) => a.tick - b.tick);
  writeFileSync(midiPath, writeSmf(1000, [sorted]));
  execFileSync(PIANOTEQ, ["--headless", "--preset", PRESET, "--mono", "--midi", midiPath, "--wav", wavPath], { stdio: "ignore" });
  const gain = -2 - peakDb(wavPath);
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", wavPath, "-af", `volume=${gain.toFixed(1)}dB`, "-ac", "1", "-b:a", "96k", join(OUT, "audio", `${druid}.mp3`)]);
  execFileSync("rm", [wavPath, midiPath]);
}

function expressionLabels(holes) {
  const keys = [...new Set(holes.map((hole) => hole.key))];
  return Object.fromEntries(keys.map((key) => [key, meaningOf(key)]).filter(([, meaning]) => meaning));
}

async function buildRoll(druid) {
  const roll = readRoll(druid, await rawMidi(druid));
  const meta = Object.fromEntries(roll.metadata);
  const rowsPerMm = pixelsPerInch(meta.LENGTH_DPI) / 25.4;
  const holes = [1, 2, 3, 4].flatMap((track) => holesOfTrack(roll, track));
  const firstRow = Math.min(...holes.map((hole) => hole.rowOn));
  const lastRow = Math.max(...holes.map((hole) => hole.rowOff));
  const mmOf = (row) => (row - firstRow) / rowsPerMm;
  const secondsOf = (row) => roll.timing.secondsAtRow(row) - roll.timing.secondsAtRow(firstRow);
  const emulation = emulate(roll, firstRow, lastRow);

  const lengthMm = mmOf(lastRow) + 30;
  const samples = range(Math.ceil(lengthMm / STEP_MM) + 1).map((i) => firstRow + i * STEP_MM * rowsPerMm);
  const curveOf = (half) => samples.map((row) => round(emulation.nuance[half].travel[emulation.grid.indexOfRow(row)], 3));

  const data = {
    druid,
    label: meta.LABEL, title: decodeEntities(meta.TITLE), performer: decodeEntities(meta.PERFORMER),
    composer: decodeEntities(meta.COMPOSER), purl: meta.PURL, callnum: meta.CALLNUM,
    catalogue: CATALOGUE[druid] ?? null,
    rowsPerMm: round(rowsPerMm, 4),
    lengthMm: round(lengthMm, 1),
    holes: holes.map((hole) => [hole.key, round(mmOf(hole.rowOn), 2), round(mmOf(hole.rowOff), 2)]),
    expression: expressionLabels(holes),
    curve: {
      stepMm: STEP_MM,
      bass: curveOf("bass"), treble: curveOf("treble"),
      hook: { bass: round(emulation.nuance.bass.hook, 3), treble: round(emulation.nuance.treble.hook, 3) },
    },
    seconds: samples.map((row) => round(secondsOf(Math.min(row, emulation.grid.rowAt(emulation.grid.length - 1))), 3)),
  };
  mkdirSync(join(OUT, "data"), { recursive: true });
  mkdirSync(join(OUT, "audio"), { recursive: true });
  writeFileSync(join(OUT, "data", `${druid}.json`), JSON.stringify(data));

  const notes = notesOfHoles(holes.filter((hole) => hole.track <= 2), rowsPerMm);
  const tail = Math.round((secondsOf(lastRow) + TAIL_SECONDS) * 1000);
  renderAudio(druid, [...noteEvents(notes, emulation, secondsOf), ...pedalEvents(emulation, secondsOf), noteOff(tail, 0, 0)]);
  return {
    druid, label: data.label,
    selector: data.catalogue?.selector ?? `${data.performer} · ${data.title} · ${data.label}`,
    seconds: data.seconds.at(-1),
  };
}

function updateIndex(entries) {
  const indexPath = join(OUT, "rolls.json");
  const existing = existsSync(indexPath) ? JSON.parse(readFileSync(indexPath, "utf8")) : [];
  const byDruid = new Map([...existing, ...entries].map((entry) => [entry.druid, entry]));
  writeFileSync(indexPath, JSON.stringify([...byDruid.values()], null, 1));
}

const entries = [];
for (const druid of process.argv.slice(2)) {
  entries.push(await buildRoll(druid));
  console.log(entries.at(-1));
}
updateIndex(entries);
