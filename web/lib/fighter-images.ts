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
 *
 * Strategy (in order):
 *   1. Exact key match.
 *   2. Case-insensitive full-name match.
 *   3. If `hint.weightClass` is provided, restrict to that division for the
 *      remaining steps — avoids "Costa" → wrong Costa in another weight.
 *   4. First-name + last-name match (both parts, case-insensitive).
 *   5. Unique last-name match — returns ONLY if exactly one fighter shares
 *      that surname. If two or more candidates exist, returns undefined so
 *      the UI falls back to initials instead of showing the wrong fighter.
 */
export function getFighterImage(
  name: string | undefined | null,
  hint?: { weightClass?: string }
): string | undefined {
  if (!name) return undefined;
  const direct = pick(name);
  if (direct) return direct;

  const lower = name.toLowerCase();
  const parts = lower.split(/\s+/).filter(Boolean);
  const firstName = parts[0];
  const lastName = parts[parts.length - 1];

  // Build candidate pool, optionally filtered by weight class
  const isInDivision = (key: string): boolean => {
    if (!hint?.weightClass) return true;
    const wc = enrichment[key]?.weightClass;
    return !wc || wc === hint.weightClass;
  };
  const candidates = Object.keys(raw).filter(isInDivision);

  // 2. Case-insensitive full match
  for (const key of candidates) {
    if (key.toLowerCase() === lower) {
      const v = pick(key);
      if (v) return v;
    }
  }

  if (!lastName) return undefined;

  // 4. First + last name match (handles "Bryce Mitchell" vs "Bryce Henry")
  if (firstName && firstName !== lastName) {
    for (const key of candidates) {
      const kp = key.toLowerCase().split(/\s+/);
      if (kp[0] === firstName && kp[kp.length - 1] === lastName) {
        const v = pick(key);
        if (v) return v;
      }
    }
  }

  // 5. Unique surname match — bail out if ambiguous
  const surnameMatches: string[] = [];
  for (const key of candidates) {
    const keyLast = key.split(/\s+/).pop()?.toLowerCase();
    if (keyLast === lastName && raw[key]) surnameMatches.push(key);
  }
  if (surnameMatches.length === 1) {
    return pick(surnameMatches[0]);
  }
  // 0 or 2+ candidates → can't disambiguate safely
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
