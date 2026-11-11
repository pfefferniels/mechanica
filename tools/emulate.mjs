// Runs the welte-t100 emulator on constructed punch patterns (one per reading
// rule) and on an excerpt of roll 3309, and writes the bellows travel as JSON.
// Usage: node tools/emulate.mjs <raw.mid> <out-dir>

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { Grid } from "../../welte-t100/dist/index.js";
import {
  aperturePorts, instrumentParameters, perforations, pneumaticModel, readRoll,
  runPedals, travelBetweenRails,
} from "../../welte-t100/dist/t100/index.js";

const [rawPath, outDir] = process.argv.slice(2);
mkdirSync(outDir, { recursive: true });

const roll = readRoll("jq774vx6544", readFileSync(rawPath));
const HALVES = ["bass", "treble"];

function gridFrom(startRow, seconds) {
  const endRow = Array.from({ length: 400000 }, (_, i) => startRow + i)
    .find((row) => roll.timing.secondsAtRow(row) - roll.timing.secondsAtRow(startRow) >= seconds);
  return Grid.overRows(roll.timing, startRow, endRow);
}

function secondsOf(grid) {
  const t0 = roll.timing.secondsAtRow(grid.rowAt(0));
  return Array.from({ length: grid.length }, (_, i) => roll.timing.secondsAtRow(grid.rowAt(i)) - t0);
}

function rowAtSecond(grid, t) {
  const t0 = roll.timing.secondsAtRow(grid.rowAt(0));
  const index = Array.from({ length: grid.length }, (_, i) => i)
    .find((i) => roll.timing.secondsAtRow(grid.rowAt(i)) - t0 >= t) ?? grid.length - 1;
  return grid.rowAt(index);
}

function travel(grid, punches, instrument = "consensus") {
  const ports = aperturePorts(grid, punches);
  const of = (half) => {
    const params = instrumentParameters(half, instrument);
    return travelBetweenRails(pneumaticModel.run({ grid, half, ports }, params), params);
  };
  return { bass: of("bass"), treble: of("treble"), ports };
}

const every = (array, step) => Array.from(array).filter((_, i) => i % step === 0);
const round = (x) => Math.round(x * 10000) / 10000;

// A scenario names its punches in seconds; `half` defaults to bass.
function scenario(name, seconds, punchesInSeconds) {
  const grid = gridFrom(roll.timing.firstHole + 30000, seconds);
  const punches = punchesInSeconds.map(([control, action, on, off, half = "bass"]) => ({
    half, control, action, rowOn: rowAtSecond(grid, on), rowOff: rowAtSecond(grid, off),
  }));
  const result = travel(grid, punches);
  const step = 5;
  const out = {
    name,
    seconds: every(secondsOf(grid), step).map(round),
    bass: every(result.bass, step).map(round),
    treble: every(result.treble, step).map(round),
    punches: punchesInSeconds.map(([control, action, on, off, half = "bass"]) => ({ half, control, action, on, off })),
    ports: Object.fromEntries([...result.ports].map(([key, series]) => [key, every(series, step).map(round)])),
  };
  writeFileSync(join(outDir, `${name}.json`), JSON.stringify(out));
  return out;
}

const SHORT = 0.06;

scenario("ruhe", 6, []);
scenario("crescendo", 9, [
  ["crescendo", "on", 1.0, 1.0 + SHORT],
  ["crescendo", "off", 4.5, 4.5 + SHORT],
]);
scenario("crescendo-lang", 12, [
  ["crescendo", "on", 1.0, 1.0 + SHORT],
]);
scenario("sforzando", 8, [
  ["sforzando", "on", 1.0, 1.6],
  ["sforzando", "off", 3.5, 3.75],
  ["sforzando", "on", 5.5, 5.5 + SHORT],
]);
scenario("lochlaenge", 6, [
  ["sforzando", "on", 1.0, 1.0 + 0.02],
  ["sforzando", "off", 2.0, 2.4],
  ["sforzando", "on", 3.0, 3.0 + 0.08],
  ["sforzando", "off", 4.0, 4.4],
  ["sforzando", "on", 5.0, 5.0 + 0.16],
]);
scenario("sforzando-crescendo", 8, [
  ["sforzando", "on", 1.0, 2.2],
  ["sforzando", "off", 3.0, 3.4],
  ["crescendo", "on", 4.5, 4.5 + SHORT],
  ["sforzando", "on", 4.5, 5.7],
]);
// The hook engages from above, as on every Mezzoforte punch of roll 3309.
scenario("mezzoforte", 10.5, [
  ["crescendo", "on", 0.5, 0.5 + SHORT],
  ["mezzoforte", "on", 3.0, 3.0 + SHORT],
  ["sforzando", "on", 3.6, 4.1],
  ["sforzando", "off", 5.0, 5.4],
  ["crescendo", "off", 6.5, 6.5 + SHORT],
  ["mezzoforte", "off", 8.3, 8.3 + SHORT],
]);

// The beginning of roll 3309, both halves, with notes and pedal.
function excerpt(name, fromSeconds, seconds) {
  const first = roll.timing.firstHole;
  const startRow = Array.from({ length: 300000 }, (_, i) => first + i)
    .find((row) => roll.timing.secondsAtRow(row) - roll.timing.secondsAtRow(first) >= fromSeconds);
  const grid = gridFrom(startRow, seconds);
  const lastRow = grid.rowAt(grid.length - 1);
  const t0 = roll.timing.secondsAtRow(startRow);
  const inWindow = (on, off) => off >= startRow && on <= lastRow;

  const expression = perforations(roll).filter((p) => inWindow(p.rowOn, p.rowOff));
  const result = travel(grid, perforations(roll), { preset: "3309" });
  const pedals = runPedals({ grid, ports: result.ports });

  const notes = [1, 2].flatMap((track) => {
    const open = new Map();
    return roll.smf.tracks[track].flatMap((event) => {
      if (event.kind === "note-on") { open.set(event.key, event.tick); return []; }
      if (event.kind !== "note-off" || !open.has(event.key)) return [];
      const tickOn = open.get(event.key);
      open.delete(event.key);
      const rowOn = roll.timing.rowAtTick(tickOn);
      const rowOff = roll.timing.rowAtTick(event.tick);
      if (!inWindow(rowOn, rowOff)) return [];
      return [{
        key: event.key, half: track === 1 ? "bass" : "treble",
        on: round(roll.timing.secondsAtRow(rowOn) - t0), off: round(roll.timing.secondsAtRow(rowOff) - t0),
        rowOn, rowOff,
      }];
    });
  });

  const step = 5;
  const out = {
    name, startRow, lastRow, fromSeconds,
    seconds: every(secondsOf(grid), step).map(round),
    rows: every(Array.from({ length: grid.length }, (_, i) => grid.rowAt(i)), step),
    bass: every(result.bass, step).map(round),
    treble: every(result.treble, step).map(round),
    damper: every(pedals.damper, step).map(round),
    notes,
    punches: expression.map((p) => ({
      half: p.half, control: p.control, action: p.action,
      on: round(roll.timing.secondsAtRow(p.rowOn) - t0), off: round(roll.timing.secondsAtRow(p.rowOff) - t0),
      rowOn: p.rowOn, rowOff: p.rowOff,
    })),
  };
  writeFileSync(join(outDir, `${name}.json`), JSON.stringify(out));
  return out;
}

const backhaus = excerpt("backhaus-3309", 0, 30);
console.log("excerpt", backhaus.notes.length, "notes", backhaus.punches.length, "expression punches", backhaus.startRow, backhaus.lastRow);
