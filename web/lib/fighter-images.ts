import images from "./fighter-images.json";

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
