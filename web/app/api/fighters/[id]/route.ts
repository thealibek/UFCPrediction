import { NextResponse } from "next/server";

export const revalidate = 3600;

const CORE = "http://sports.core.api.espn.com/v2/sports/mma/athletes";

interface CoreAthlete {
  id: string;
  displayName?: string;
  shortName?: string;
  weight?: number;
  displayWeight?: string;
  height?: number;
  displayHeight?: string;
  age?: number;
  dateOfBirth?: string;
  citizenship?: string;
  flag?: { href?: string; alt?: string };
  headshot?: { href?: string };
  slug?: string;
  links?: Array<{ rel?: string[]; href?: string }>;
}

interface RecordItem {
  type?: string;
  summary?: string;
  displayValue?: string;
}

interface StatRow {
  name?: string;
  displayName?: string;
  abbreviation?: string;
  value?: number;
  displayValue?: string;
}

async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, {
      next: { revalidate: 3600 },
      headers: { "User-Agent": "OctagonAI/1.0" },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const [athlete, records, stats] = await Promise.all([
    fetchJSON<CoreAthlete>(`${CORE}/${id}`),
    fetchJSON<{ items?: RecordItem[] }>(`${CORE}/${id}/records`),
    fetchJSON<{ splits?: { categories?: Array<{ displayName?: string; stats?: StatRow[] }> } }>(
      `${CORE}/${id}/statistics`
    ),
  ]);

  if (!athlete?.displayName) {
    return NextResponse.json({ error: "Fighter not found" }, { status: 404 });
  }

  // Find total record
  const total = records?.items?.find((r) => r.type === "total");

  // Flatten stats from "General" category
  const general = stats?.splits?.categories?.find((c) => c.displayName === "General");
  const statMap: Record<string, string | number | undefined> = {};
  for (const s of general?.stats ?? []) {
    const key = s.abbreviation ?? s.name ?? s.displayName ?? "";
    if (!key) continue;
    statMap[key] = s.displayValue ?? s.value;
  }

  return NextResponse.json({
    id,
    name: athlete.displayName,
    slug: athlete.slug,
    record: total?.summary ?? total?.displayValue ?? "—",
    weight: athlete.displayWeight,
    height: athlete.displayHeight,
    age: athlete.age,
    dateOfBirth: athlete.dateOfBirth,
    country: athlete.citizenship ?? athlete.flag?.alt,
    flagUrl: athlete.flag?.href,
    imageUrl: athlete.headshot?.href,
    espnUrl: athlete.links?.find((l) => l.rel?.includes("playercard"))?.href,
    stats: statMap,
  });
}
