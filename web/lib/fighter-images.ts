import images from "./fighter-images.json";
import data from "./fighter-data.json";

// Values may be `null` (sentinel = we tried and ESPN had no headshot).
const raw = images as Record<string, string | null>;

function pick(key: string): string | undefined {
  const v = raw[key];
  return typeof v === "string" && v.length > 0 ? v : undefined;
}

/**
 * Resolve a fighter name to an ESPN headshot URL (or undefined).
 * Tries exact, then case-insensitive, then last-name fallback.
 */
export function getFighterImage(name: string | undefined | null): string | undefined {
  if (!name) return undefined;
  const direct = pick(name);
  if (direct) return direct;

  const lower = name.toLowerCase();
  for (const key of Object.keys(raw)) {
    if (key.toLowerCase() === lower) {
      const v = pick(key);
      if (v) return v;
    }
  }

  const lastName = name.split(/\s+/).pop()?.toLowerCase();
  if (!lastName) return undefined;
  for (const key of Object.keys(raw)) {
    const keyLast = key.split(/\s+/).pop()?.toLowerCase();
    if (keyLast === lastName) {
      const v = pick(key);
      if (v) return v;
    }
  }
  return undefined;
}

/** Extract ESPN athlete id from a headshot URL like .../full/4350812.png */
export function extractAthleteId(url: string | undefined | null): string | undefined {
  if (!url) return undefined;
  const m = url.match(/\/(\d+)\.png/);
  return m?.[1];
}

interface FighterEnrichment {
  id?: string;
  weight?: number | null;
  weightClass?: string;
  height?: string | null;
  age?: number | null;
  country?: string | null;
  flagUrl?: string | null;
  sex?: string | null;
}

const enrichment = data as Record<string, FighterEnrichment>;

export interface FighterIndexEntry {
  name: string;
  id?: string;
  imageUrl?: string;
  weightClass?: string;
  country?: string;
}

/** Full list of all fighters (with at least a name). */
export function getAllFighters(): FighterIndexEntry[] {
  const list: FighterIndexEntry[] = [];
  for (const [name, url] of Object.entries(raw)) {
    if (!url) continue; // skip null misses
    const e = enrichment[name];
    list.push({
      name,
      imageUrl: url,
      id: e?.id ?? extractAthleteId(url),
      weightClass: e?.weightClass,
      country: e?.country ?? undefined,
    });
  }
  return list.sort((a, b) => a.name.localeCompare(b.name));
}

export const WEIGHT_CLASSES = [
  "Strawweight",
  "Flyweight",
  "Bantamweight",
  "Featherweight",
  "Lightweight",
  "Welterweight",
  "Middleweight",
  "Light Heavyweight",
  "Heavyweight",
] as const;
