// Shared logic for refreshing the fighter database from ESPN.
// Used by:
//   - scripts/fetch-fighter-images.mjs / enrich-fighter-data.mjs (CLI)
//   - /api/admin/refresh-fighters (HTTP)
//
// Reads/writes the JSON files under lib/.

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

const LIB_DIR = join(process.cwd(), "lib");
const IMAGES_FILE = join(LIB_DIR, "fighter-images.json");
const DATA_FILE = join(LIB_DIR, "fighter-data.json");
const META_FILE = join(LIB_DIR, "fighter-meta.json");

const SEARCH_URL = "https://site.web.api.espn.com/apis/common/v3/search";
const SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard";
const CORE = "http://sports.core.api.espn.com/v2/sports/mma/athletes";

export interface RefreshOptions {
  /** Months of scoreboard history to scan for new fighter names. Default 6. */
  monthsBack?: number;
  /** Months of upcoming events to scan. Default 6. */
  monthsFwd?: number;
  /** Retry previously-missed names? Default false (saves time). */
  retryMisses?: boolean;
}

export interface RefreshResult {
  lastUpdated: string;
  totalFighters: number;
  withImage: number;
  withWeight: number;
  newlyResolvedImages: number;
  newlyEnriched: number;
  durationMs: number;
}

export interface FighterMeta {
  lastUpdated: string;
  totalFighters: number;
  withImage: number;
  withWeight: number;
}

// ---------- helpers ----------

function readJSON<T>(file: string, fallback: T): T {
  try {
    return JSON.parse(readFileSync(file, "utf8")) as T;
  } catch {
    return fallback;
  }
}

function writeJSON(file: string, data: unknown) {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(data, null, 2) + "\n");
}

function fmtDate(d: Date) {
  return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;
}

function divisionFromWeight(lbs: number | null | undefined): string | undefined {
  if (!lbs) return undefined;
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

async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { headers: { "User-Agent": "OctagonAI/1.0" } });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------- phase 1: collect names from scoreboard ----------

interface ScoreboardResp {
  events?: Array<{
    competitions?: Array<{
      competitors?: Array<{ athlete?: { displayName?: string } }>;
    }>;
  }>;
}

async function fetchRosterNames(monthsBack: number, monthsFwd: number): Promise<string[]> {
  const names = new Set<string>();
  const today = new Date();
  const start = new Date(today);
  start.setUTCMonth(start.getUTCMonth() - monthsBack);
  const end = new Date(today);
  end.setUTCMonth(end.getUTCMonth() + monthsFwd);

  let cursor = new Date(start);
  while (cursor < end) {
    const next = new Date(cursor);
    next.setUTCDate(next.getUTCDate() + 180);
    const windowEnd = next > end ? end : next;
    const url = `${SCOREBOARD}?dates=${fmtDate(cursor)}-${fmtDate(windowEnd)}&limit=100`;
    const data = await fetchJSON<ScoreboardResp>(url);
    for (const e of data?.events ?? []) {
      for (const c of e.competitions ?? []) {
        for (const comp of c.competitors ?? []) {
          const n = comp.athlete?.displayName;
          if (n) names.add(n);
        }
      }
    }
    cursor = next;
    await sleep(150);
  }
  return [...names];
}

// ---------- phase 2: resolve headshot URLs via ESPN search ----------

interface SearchItem {
  displayName?: string;
  headshot?: { href?: string };
}

async function lookupHeadshot(name: string): Promise<string | null> {
  const url = `${SEARCH_URL}?query=${encodeURIComponent(name)}&limit=5&type=player&sport=mma`;
  const data = await fetchJSON<{ items?: SearchItem[] }>(url);
  const items = data?.items ?? [];
  const lower = name.toLowerCase();
  const exact = items.find((i) => (i.displayName ?? "").toLowerCase() === lower);
  const chosen = exact ?? items[0];
  return chosen?.headshot?.href ?? null;
}

// ---------- phase 3: enrich with weight/age/country via core API ----------

interface CoreAthleteResp {
  weight?: number;
  displayHeight?: string;
  age?: number;
  citizenship?: string;
  flag?: { href?: string; alt?: string };
  gender?: string;
}

interface FighterEnrichment {
  id: string;
  weight: number | null;
  weightClass?: string;
  height: string | null;
  age: number | null;
  country: string | null;
  flagUrl: string | null;
  sex: string | null;
}

function extractId(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  const m = url.match(/\/(\d+)\.png/);
  return m?.[1];
}

async function enrichAthlete(id: string): Promise<FighterEnrichment | null> {
  const a = await fetchJSON<CoreAthleteResp>(`${CORE}/${id}`);
  if (!a) return null;
  return {
    id,
    weight: a.weight ?? null,
    weightClass: divisionFromWeight(a.weight),
    height: a.displayHeight ?? null,
    age: a.age ?? null,
    country: a.citizenship ?? a.flag?.alt ?? null,
    flagUrl: a.flag?.href ?? null,
    sex: a.gender?.toLowerCase() ?? null,
  };
}

// ---------- main entry point ----------

export async function refreshFighterDatabase(opts: RefreshOptions = {}): Promise<RefreshResult> {
  const start = Date.now();
  const monthsBack = opts.monthsBack ?? 6;
  const monthsFwd = opts.monthsFwd ?? 6;

  const images = readJSON<Record<string, string | null>>(IMAGES_FILE, {});
  const data = readJSON<Record<string, FighterEnrichment>>(DATA_FILE, {});

  // 1. Discover names from scoreboard (skips API if already known)
  const rosterNames = await fetchRosterNames(monthsBack, monthsFwd);

  // 2. Resolve headshots for new names
  let newlyResolved = 0;
  for (const name of rosterNames) {
    const cached = name in images;
    if (cached && !(opts.retryMisses && images[name] === null)) continue;
    try {
      const url = await lookupHeadshot(name);
      images[name] = url;
      if (url) newlyResolved++;
    } catch {
      // leave unset → retry next run
    }
    await sleep(120);
  }
  writeJSON(IMAGES_FILE, images);

  // 3. Enrich newly-resolved (or anyone missing weight)
  let newlyEnriched = 0;
  for (const [name, url] of Object.entries(images)) {
    if (!url) continue;
    if (data[name]?.weight != null) continue;
    const id = extractId(url);
    if (!id) continue;
    try {
      const enr = await enrichAthlete(id);
      if (enr) {
        data[name] = enr;
        newlyEnriched++;
      }
    } catch {
      // skip
    }
    await sleep(100);
  }
  writeJSON(DATA_FILE, data);

  // 4. Persist meta
  const totalFighters = Object.keys(images).length;
  const withImage = Object.values(images).filter((v) => typeof v === "string" && v).length;
  const withWeight = Object.values(data).filter((v) => v.weight != null).length;
  const meta: FighterMeta = {
    lastUpdated: new Date().toISOString(),
    totalFighters,
    withImage,
    withWeight,
  };
  writeJSON(META_FILE, meta);

  return {
    ...meta,
    newlyResolvedImages: newlyResolved,
    newlyEnriched,
    durationMs: Date.now() - start,
  };
}

/** Read the current database meta without refreshing. */
export function readFighterMeta(): FighterMeta | null {
  try {
    return readJSON<FighterMeta>(META_FILE, null as unknown as FighterMeta);
  } catch {
    return null;
  }
}
