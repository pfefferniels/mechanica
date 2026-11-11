// Writes the scan geometry SUPRA embeds in each raw MIDI file, for the facsimile tiles.
// Usage: node scan_meta.mjs <out.json> <druid> […]
import { readFileSync, writeFileSync } from "node:fs";
import { readRoll } from "../../../welte-t100/dist/t100/index.js";

const MIDI = new URL("../../../roll-nuance-tracer/cache/SUPRA/welte-red/midi-raw/", import.meta.url);
const KEYS = ["IMAGE_WIDTH", "IMAGE_LENGTH", "PRELEADER_ROW", "LEADER_ROW", "FIRST_HOLE", "LAST_HOLE", "END_MARGIN",
  "HOLE_SEPARATION", "HOLE_OFFSET", "AVG_HOLE_WIDTH", "LENGTH_DPI"];

const geometryOf = (druid) => {
  const metadata = Object.fromEntries(readRoll(druid, readFileSync(new URL(`${druid}_raw.mid`, MIDI))).metadata);
  return [druid, Object.fromEntries(KEYS.map((key) => [key, parseFloat(metadata[key])]))];
};

const [out, ...druids] = process.argv.slice(2);
writeFileSync(out, JSON.stringify(Object.fromEntries(druids.map(geometryOf)), null, 1));
