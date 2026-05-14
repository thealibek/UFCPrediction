// Resolve UFC fighter names -> ESPN headshot URLs.
// Usage:
//   node scripts/fetch-fighter-images.mjs              # just mock data names
//   node scripts/fetch-fighter-images.mjs --roster     # + every fighter from ESPN scoreboard (last 24mo + next 6mo)
//   node scripts/fetch-fighter-images.mjs --roster --months-back 36
//
// Writes web/lib/fighter-images.json as { "Fighter Name": "https://..." }
// Idempotent: already-resolved names are kept; only missing ones get queried.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = join(__dirname, "..");
const FIGHTS_FILE = join(WEB_ROOT, "lib", "fights.ts");
const OUT_FILE = join(WEB_ROOT, "lib", "fighter-images.json");
const SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search";
const SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard";

const args = process.argv.slice(2);
const FETCH_ROSTER = args.includes("--roster");
const MONTHS_BACK = (() => {
  const i = args.indexOf("--months-back");
  return i >= 0 ? parseInt(args[i + 1] ?? "24", 10) : 24;
})();
const MONTHS_FWD = (() => {
  const i = args.indexOf("--months-fwd");
  return i >= 0 ? parseInt(args[i + 1] ?? "6", 10) : 6;
})();

const fmt = (d) =>
  `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;

/** Extract all unique `name: "..."` strings from fights.ts (FighterMini blocks). */
function extractFighterNames(src) {
  const names = new Set();
  const re = /name:\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(src)) !== null) names.add(m[1]);
  return [...names];
}

/** Pull all UFC fighter names from scoreboard over a date range, split into ~6-month chunks. */
async function fetchRosterNames(monthsBack, monthsFwd) {
  const names = new Set();
  const today = new Date();
  const start = new Date(today);
  start.setUTCMonth(start.getUTCMonth() - monthsBack);
  const end = new Date(today);
  end.setUTCMonth(end.getUTCMonth() + monthsFwd);

  // Walk in 180-day windows to avoid overly large responses
  let cursor = new Date(start);
  while (cursor < end) {
    const next = new Date(cursor);
    next.setUTCDate(next.getUTCDate() + 180);
    const windowEnd = next > end ? end : next;
    const url = `${SCOREBOARD}?dates=${fmt(cursor)}-${fmt(windowEnd)}&limit=100`;
    process.stdout.write(`  scoreboard ${fmt(cursor)}-${fmt(windowEnd)} ... `);
    try {
      const res = await fetch(url, { headers: { "User-Agent": "OctagonAI/1.0" } });
      if (!res.ok) {
        console.log(`HTTP ${res.status}`);
      } else {
        const data = await res.json();
        let added = 0;
        for (const e of data.events ?? []) {
          for (const c of e.competitions ?? []) {
            for (const comp of c.competitors ?? []) {
              const n = comp.athlete?.displayName;
              if (n && !names.has(n)) {
                names.add(n);
                added++;
              }
            }
          }
        }
        console.log(`+${added} (total ${names.size})`);
      }
    } catch (e) {
      console.log(`error: ${e.message}`);
    }
    cursor = next;
    await new Promise((r) => setTimeout(r, 150));
  }
  return [...names];
}

async function lookup(name) {
  const url = `${SEARCH_URL}?query=${encodeURIComponent(name)}&limit=5&type=player&sport=mma`;
  const res = await fetch(url, { headers: { "User-Agent": "OctagonAI/1.0" } });
  if (!res.ok) throw new Error(`ESPN ${res.status} for ${name}`);
  const data = await res.json();
  const items = data.items ?? [];

  // Prefer exact case-insensitive match on displayName
  const lower = name.toLowerCase();
  const exact = items.find((i) => (i.displayName ?? "").toLowerCase() === lower);
  const chosen = exact ?? items[0];
  return chosen?.headshot?.href ?? null;
}

async function main() {
  const src = readFileSync(FIGHTS_FILE, "utf8");
  const mockNames = extractFighterNames(src);
  console.log(`Mock data: ${mockNames.length} unique fighters`);

  let rosterNames = [];
  if (FETCH_ROSTER) {
    console.log(`Pulling UFC roster from scoreboard (last ${MONTHS_BACK}mo + next ${MONTHS_FWD}mo)...`);
    rosterNames = await fetchRosterNames(MONTHS_BACK, MONTHS_FWD);
    console.log(`Roster: ${rosterNames.length} unique fighters`);
  }

  const names = [...new Set([...mockNames, ...rosterNames])];
  console.log(`Total to process: ${names.length}\n`);

  // Load existing map so we only fill missing entries
  let existing = {};
  try {
    existing = JSON.parse(readFileSync(OUT_FILE, "utf8"));
  } catch {
    /* first run */
  }

  const out = { ...existing };
  // Mark misses so we don't keep re-querying every run (value = null in JSON keeps the key)
  const MISS_SENTINEL = null;
  let resolved = 0;
  let cached = 0;
  let failed = 0;
  let processed = 0;

  const todo = names.filter((n) => !(n in out));
  console.log(`Cached: ${names.length - todo.length} · To query: ${todo.length}\n`);

  const save = () => {
    mkdirSync(dirname(OUT_FILE), { recursive: true });
    writeFileSync(OUT_FILE, JSON.stringify(out, null, 2) + "\n");
  };

  for (const name of todo) {
    try {
      const url = await lookup(name);
      if (url) {
        out[name] = url;
        resolved++;
      } else {
        out[name] = MISS_SENTINEL;
        failed++;
      }
    } catch (e) {
      // Don't store on transient errors so they retry next run
      failed++;
      console.log(`  err     ${name}  ${e.message}`);
    }
    processed++;
    if (processed % 25 === 0) {
      console.log(`  [${processed}/${todo.length}] resolved=${resolved} miss=${failed}`);
      save();
    }
    await new Promise((r) => setTimeout(r, 120));
  }

  cached = names.length - todo.length;
  save();
  const withUrl = Object.values(out).filter((v) => typeof v === "string").length;
  console.log(`\nSaved ${Object.keys(out).length} total entries (${withUrl} with URL) to ${OUT_FILE}`);
  console.log(`Newly resolved: ${resolved} · Misses: ${failed} · Pre-cached: ${cached}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
