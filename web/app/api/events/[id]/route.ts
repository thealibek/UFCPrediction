import { NextResponse } from "next/server";
import { parseMainEvent, syntheticPrediction, type EventBout, type EventDetail } from "@/lib/events";

export const revalidate = 1800;

const CORE_BASE = "http://sports.core.api.espn.com/v2/sports/mma/leagues/ufc";
const SITE_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard";

interface CoreCompetition {
  id: string;
  date?: string;
  matchNumber?: number;
  cardSegment?: { id?: string; name?: string; description?: string };
  type?: { text?: string; abbreviation?: string };
  format?: { regulation?: { periods?: number } };
  note?: string;
  competitors?: Array<{
    id?: string;
    order?: number;
    winner?: boolean;
    athlete?: { $ref: string };
    record?: { $ref: string };
  }>;
}

interface CoreAthlete {
  id: string;
  displayName?: string;
  flag?: { href?: string; alt?: string };
  headshot?: { href?: string };
  records?: { $ref: string };
}

interface CoreRecordsList {
  items?: Array<{ summary?: string; type?: string; displayValue?: string }>;
}

async function fetchJSON<T>(url: string, signal?: AbortSignal): Promise<T | null> {
  try {
    const res = await fetch(url, {
      next: { revalidate: 1800 },
      headers: { "User-Agent": "OctagonAI/1.0" },
      signal,
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function segmentNameToKey(name?: string): EventBout["cardSegment"] {
  const n = (name ?? "").toLowerCase();
  if (n.includes("early")) return "earlyprelims";
  if (n.includes("prelim")) return "prelims";
  return "main";
}

// ESPN matchNumber: 1 = main event (listed first on card), highest = first walkout (early prelim).
// So sort ASCENDING so main event appears at the top.
function sortBouts(a: EventBout, b: EventBout): number {
  const segOrder = { main: 0, prelims: 1, earlyprelims: 2 } as const;
  const segDiff = segOrder[a.cardSegment] - segOrder[b.cardSegment];
  if (segDiff !== 0) return segDiff;
  return (a.matchNumber ?? 999) - (b.matchNumber ?? 999);
}

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  // Step 1: find the event in scoreboard to get name/date/venue
  // (we query a wide date range; scoreboard is cached)
  try {
    const today = new Date();
    const start = new Date(today.getTime() - 30 * 24 * 3600 * 1000);
    const end = new Date(today.getTime() + 180 * 24 * 3600 * 1000);
    const fmt = (d: Date) =>
      `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, "0")}${String(d.getUTCDate()).padStart(2, "0")}`;

    const sbUrl = `${SITE_SCOREBOARD}?dates=${fmt(start)}-${fmt(end)}&limit=50`;
    const sbRes = await fetch(sbUrl, { next: { revalidate: 1800 } });
    const sbData = (await sbRes.json()) as {
      events?: Array<{
        id: string;
        name: string;
        shortName?: string;
        date: string;
        venues?: Array<{ fullName?: string; address?: { city?: string; country?: string } }>;
      }>;
    };
    const event = sbData.events?.find((e) => e.id === id);
    if (!event) {
      return NextResponse.json({ error: "Event not found" }, { status: 404 });
    }
    const venue = event.venues?.[0];

    // Step 2: list competitions of the event
    const compsList = await fetchJSON<{ items?: Array<{ $ref: string }> }>(
      `${CORE_BASE}/events/${id}/competitions?limit=50`
    );
    if (!compsList?.items) {
      return NextResponse.json({
        id,
        name: event.name,
        shortName: event.shortName,
        date: event.date,
        venue: venue?.fullName ?? "TBA",
        city: [venue?.address?.city, venue?.address?.country].filter(Boolean).join(", "),
        mainEvent: parseMainEvent(event.name),
        fightCount: 0,
        bouts: [],
      } satisfies EventDetail);
    }

    // Step 3: fetch competition detail + athletes (parallel)
    const compRefs = compsList.items.map((i) => i.$ref);
    const comps = (await Promise.all(compRefs.map((r) => fetchJSON<CoreCompetition>(r)))).filter(
      (c): c is CoreCompetition => c !== null
    );

    // Collect all athlete + records refs
    const allAthleteRefs = new Set<string>();
    const allRecordRefs = new Set<string>();
    for (const c of comps) {
      for (const comp of c.competitors ?? []) {
        if (comp.athlete?.$ref) allAthleteRefs.add(comp.athlete.$ref);
        if (comp.record?.$ref) allRecordRefs.add(comp.record.$ref);
      }
    }

    const [athletes, records] = await Promise.all([
      Promise.all(
        Array.from(allAthleteRefs).map((r) =>
          fetchJSON<CoreAthlete>(r).then((a) => [r, a] as const)
        )
      ),
      Promise.all(
        Array.from(allRecordRefs).map((r) =>
          fetchJSON<{ summary?: string; displayValue?: string }>(r).then((rec) => [r, rec] as const)
        )
      ),
    ]);

    const athleteMap = new Map(athletes.map(([k, v]) => [k, v]));
    const recordMap = new Map(records.map(([k, v]) => [k, v]));

    // Step 4: build bouts
    const bouts: EventBout[] = [];
    for (const c of comps) {
      const [a, b] = c.competitors ?? [];
      if (!a || !b) continue;
      const athleteA = a.athlete?.$ref ? athleteMap.get(a.athlete.$ref) : null;
      const athleteB = b.athlete?.$ref ? athleteMap.get(b.athlete.$ref) : null;
      if (!athleteA?.displayName || !athleteB?.displayName) continue;

      const recA = a.record?.$ref ? recordMap.get(a.record.$ref) : null;
      const recB = b.record?.$ref ? recordMap.get(b.record.$ref) : null;

      const periods = c.format?.regulation?.periods ?? 3;
      const weightClass = c.type?.text ?? c.type?.abbreviation ?? "Catchweight";
      const note = (c.note ?? "").toLowerCase();

      bouts.push({
        id: c.id,
        matchNumber: c.matchNumber,
        cardSegment: segmentNameToKey(c.cardSegment?.name ?? c.cardSegment?.description),
        weightClass,
        isTitleFight: note.includes("title"),
        isFiveRound: periods === 5,
        fighterA: {
          name: athleteA.displayName,
          country: athleteA.flag?.alt ?? "—",
          record: recA?.summary ?? recA?.displayValue ?? "—",
          flagUrl: athleteA.flag?.href,
          imageUrl: athleteA.headshot?.href,
        },
        fighterB: {
          name: athleteB.displayName,
          country: athleteB.flag?.alt ?? "—",
          record: recB?.summary ?? recB?.displayValue ?? "—",
          flagUrl: athleteB.flag?.href,
          imageUrl: athleteB.headshot?.href,
        },
        prediction: syntheticPrediction(c.id, athleteA.displayName, athleteB.displayName),
      });
    }

    bouts.sort(sortBouts);

    const detail: EventDetail = {
      id,
      name: event.name,
      shortName: event.shortName,
      date: event.date,
      venue: venue?.fullName ?? "TBA",
      city: [venue?.address?.city, venue?.address?.country].filter(Boolean).join(", "),
      mainEvent: parseMainEvent(event.name),
      fightCount: bouts.length,
      bouts,
    };

    return NextResponse.json(detail);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "unknown" },
      { status: 500 }
    );
  }
}
