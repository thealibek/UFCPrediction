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
      const main = parseMainEvent(e.name);
      // last name = last whitespace token (e.g. "Allen", "Costa", "Topuria", "Gaethje")
      const lastA = main.fighterAName.split(/\s+/).pop() ?? "";
      const lastB = main.fighterBName.split(/\s+/).pop() ?? "";
      return {
        id: e.id,
        name: e.name,
        shortName: e.shortName,
        date: e.date,
        venue: venue?.fullName ?? "TBA",
        city: [venue?.address?.city, venue?.address?.country].filter(Boolean).join(", "),
        mainEvent: {
          ...main,
          fighterAImage: findHeadshot(e.competitions, lastA),
          fighterBImage: findHeadshot(e.competitions, lastB),
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
