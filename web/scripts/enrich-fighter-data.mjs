// Enrich fighter database with weight class, country, age, etc.
// Usage:  node scripts/enrich-fighter-data.mjs
//
// Reads:  lib/fighter-images.json (name -> headshot URL)
// Writes: lib/fighter-data.json   (name -> { id, weightClass, country, age, height, weight })
// Idempotent: skips already-enriched fighters.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = join(__dirname, "..");
const IN_FILE = join(WEB_ROOT, "lib", "fighter-images.json");
const OUT_FILE = join(WEB_ROOT, "lib", "fighter-data.json");
const CORE = "http://sports.core.api.espn.com/v2/sports/mma/athletes";

// Map weight in lbs -> UFC division name
function divisionFromWeight(lbs) {
  if (!lbs) return undefined;
  // UFC official divisions (men's + women's share names; add Women's prefix unknown without sex flag)
  if (lbs <= 116) return "Strawweight";
  if (lbs <= 125) return "Flyweight";
  if (lbs <= 135) return "Bantamweight";
  if (lbs <= 145) return "Featherweight";
  if (lbs <= 155) return "Lightweight";
  if (lbs <= 170) return "Welterweight";
  if (lbs <= 185) return "Middleweight";
  if (lbs <= 205) return "Light Heavyweight";
  return "Heavyweight";
}

function extractId(url) {
  const m = (url ?? "").match(/\/(\d+)\.png/);
  return m?.[1];
}

async function fetchJSON(url) {
  try {
    const res = await fetch(url, { headers: { "User-Agent": "OctagonAI/1.0" } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function enrich(id) {
  const a = await fetchJSON(`${CORE}/${id}`);
  if (!a) return null;
  return {
    id,
    weight: a.weight ?? null,
    weightClass: divisionFromWeight(a.weight),
    height: a.displayHeight ?? null,
    age: a.age ?? null,
    country: a.citizenship ?? a.flag?.alt ?? null,
    flagUrl: a.flag?.href ?? null,
    sex: a.gender?.toLowerCase?.() ?? null,
  };
}

async function main() {
  const images = JSON.parse(readFileSync(IN_FILE, "utf8"));
  let existing = {};
  try {
    existing = JSON.parse(readFileSync(OUT_FILE, "utf8"));
  } catch {
    /* first run */
  }

  const out = { ...existing };
  const todo = [];
  for (const [name, url] of Object.entries(images)) {
    if (!url) continue;
    if (out[name]?.weightClass || out[name]?.weight) continue;
    const id = extractId(url);
    if (!id) continue;
    todo.push({ name, id });
  }

  console.log(`Already enriched: ${Object.keys(existing).length}`);
  console.log(`To process: ${todo.length}\n`);

  let processed = 0;
  let failed = 0;

  const save = () => {
    mkdirSync(dirname(OUT_FILE), { recursive: true });
    writeFileSync(OUT_FILE, JSON.stringify(out, null, 2) + "\n");
  };

  for (const { name, id } of todo) {
    try {
      const data = await enrich(id);
      if (data) {
        out[name] = data;
      } else {
        failed++;
      }
    } catch (e) {
      failed++;
      console.log(`  err ${name}: ${e.message}`);
    }
    processed++;
    if (processed % 25 === 0) {
      console.log(`  [${processed}/${todo.length}] failed=${failed}`);
      save();
    }
    await new Promise((r) => setTimeout(r, 100));
  }

  save();
  const withWeight = Object.values(out).filter((v) => v.weight).length;
  console.log(`\nSaved ${Object.keys(out).length} entries (${withWeight} with weight)`);
  console.log(`Failed: ${failed}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
