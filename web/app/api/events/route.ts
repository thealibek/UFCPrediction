import { NextResponse } from "next/server";
import { parseMainEvent, type EventSummary } from "@/lib/events";

export const revalidate = 1800;

const SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard";

function formatDate(d: Date) {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

interface EspnVenue {
  fullName?: string;
  address?: { city?: string; country?: string };
}
interface EspnAthlete {
  displayName?: string;
  shortName?: string;
  headshot?: { href?: string };
}
interface EspnCompetitor {
  athlete?: EspnAthlete;
}
interface EspnCompetition {
  id: string;
  competitors?: EspnCompetitor[];
  format?: { regulation?: { periods?: number } };
  note?: string;
}

// Pick the headliner of an event. ESPN orders competitions chronologically
// (early prelims → prelims → main card → main event LAST). The main event is
// also the only 5-round bout on a non-PPV card; on PPVs there's still exactly
// one true headliner. Strategy:
//   1. Find the LAST competition with periods === 5 (true main event marker)
//   2. Otherwise fall back to the last competition in the array
//   3. If still nothing — undefined (lets caller use title parsing)
function pickMainEvent(
  competitions: EspnCompetition[] | undefined
): EspnCompetition | undefined {
  if (!competitions || competitions.length === 0) return undefined;
  for (let i = competitions.length - 1; i >= 0; i--) {
    if (competitions[i].format?.regulation?.periods === 5) return competitions[i];
  }
  return competitions[competitions.length - 1];
}
interface EspnEvent {
  id: string;
  name: string;
  shortName?: string;
  date: string;
  venues?: EspnVenue[];
  competitions?: EspnCompetition[];
}

// Try to find a headshot for a given last name across all competitions of the event
function findHeadshot(competitions: EspnCompetition[] | undefined, lastName: string): string | undefined {
  if (!competitions || !lastName) return undefined;
  const ln = lastName.toLowerCase();
  for (const comp of competitions) {
    for (const c of comp.competitors ?? []) {
      const n = (c.athlete?.displayName ?? c.athlete?.shortName ?? "").toLowerCase();
      if (n.includes(ln) && c.athlete?.headshot?.href) return c.athlete.headshot.href;
    }
  }
  return undefined;
}

export async function GET() {
  try {
    const today = new Date();
    const end = new Date(today.getTime() + 90 * 24 * 3600 * 1000);
    const url = `${SCOREBOARD}?dates=${formatDate(today)}-${formatDate(end)}&limit=50`;

    const res = await fetch(url, {
      next: { revalidate: 1800 },
      headers: { "User-Agent": "OctagonAI/1.0" },
    });
    if (!res.ok) {
      return NextResponse.json({ source: "fallback", events: [] satisfies EventSummary[] });
    }

    const data: { events?: EspnEvent[] } = await res.json();
    const events: EventSummary[] = (data.events ?? []).map((e) => {
      const venue = e.venues?.[0];

      // Pick the headliner (last 5-round bout, falls back to last competition).
      // Gives us real full names + authoritative ESPN headshots. Fall back to
      // title parsing only if the scoreboard hasn't populated competitors yet.
      const mainComp = pickMainEvent(e.competitions);
      const cA = mainComp?.competitors?.[0]?.athlete;
      const cB = mainComp?.competitors?.[1]?.athlete;

      let fighterAName = cA?.displayName ?? "";
      let fighterBName = cB?.displayName ?? "";
      let fighterAImage = cA?.headshot?.href;
      let fighterBImage = cB?.headshot?.href;

      if (!fighterAName || !fighterBName) {
        const parsed = parseMainEvent(e.name);
        fighterAName = fighterAName || parsed.fighterAName;
        fighterBName = fighterBName || parsed.fighterBName;
        // Try to recover photos via fuzzy surname match across all competitions
        if (!fighterAImage && fighterAName) {
          fighterAImage = findHeadshot(e.competitions, fighterAName.split(/\s+/).pop() ?? "");
        }
        if (!fighterBImage && fighterBName) {
          fighterBImage = findHeadshot(e.competitions, fighterBName.split(/\s+/).pop() ?? "");
        }
      }

      return {
        id: e.id,
        name: e.name,
        shortName: e.shortName,
        date: e.date,
        venue: venue?.fullName ?? "TBA",
        city: [venue?.address?.city, venue?.address?.country].filter(Boolean).join(", "),
        mainEvent: {
          fighterAName,
          fighterBName,
          fighterAImage,
          fighterBImage,
        },
        fightCount: e.competitions?.length,
      };
    });

    return NextResponse.json({ source: "espn", count: events.length, events });
  } catch (e) {
    return NextResponse.json({
      source: "fallback",
      error: e instanceof Error ? e.message : "unknown",
      events: [] satisfies EventSummary[],
    });
  }
}
