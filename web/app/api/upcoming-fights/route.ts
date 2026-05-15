import { NextResponse } from "next/server";
import type { Fight } from "@/lib/fights";

// ESPN public scoreboard endpoint — no auth required, returns upcoming UFC events
const ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard";

// Cache 30 min on the server (Next.js ISR-style)
export const revalidate = 1800;

interface EspnAthlete {
  displayName?: string;
  flag?: { alt?: string };
  shortName?: string;
}

interface EspnCompetitor {
  athlete?: EspnAthlete;
  records?: Array<{ summary?: string }>;
  winner?: boolean;
}

interface EspnCompetition {
  date?: string;
  type?: { abbreviation?: string };
  note?: string;
  competitors?: EspnCompetitor[];
  status?: { type?: { state?: string; completed?: boolean } };
  format?: { regulation?: { periods?: number } };
}

interface EspnEvent {
  id: string;
  name: string;
  shortName?: string;
  date: string;
  competitions?: EspnCompetition[];
}

interface EspnResponse {
  events?: EspnEvent[];
}

// Best-effort weight-class normalization from ESPN's "type.abbreviation" or note text
function inferWeightClass(c: EspnCompetition): string {
  const abbr = c.type?.abbreviation?.toLowerCase() ?? "";
  const note = c.note?.toLowerCase() ?? "";
  const map: Array<[string, string]> = [
    ["heavy", "Heavyweight"],
    ["light heavy", "Light Heavyweight"],
    ["middle", "Middleweight"],
    ["welter", "Welterweight"],
    ["light", "Lightweight"],
    ["feather", "Featherweight"],
    ["bantam", "Bantamweight"],
    ["fly", "Flyweight"],
    ["straw", "Strawweight"],
  ];
  for (const [needle, label] of map) {
    if (abbr.includes(needle) || note.includes(needle)) {
      const womens = note.includes("women") || abbr.includes("w");
      return womens ? `Women's ${label}` : label;
    }
  }
  return "Catchweight";
}

// Deterministic pseudo-prediction so each fight has stable confidence/winner
// without needing a real model call here (the real predictor lives in Python).
function syntheticPrediction(seed: string, fighterA: string, fighterB: string) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const confidence = 55 + (h % 25); // 55..79
  const winner = h % 2 === 0 ? fighterA : fighterB;
  const methods: Array<"KO/TKO" | "Submission" | "Decision"> = ["KO/TKO", "Submission", "Decision"];
  const method = methods[h % 3];
  return { winner, confidence, method, reasoning: "AI prediction placeholder — connect Python model service to populate." };
}

function transform(events: EspnEvent[]): Fight[] {
  const out: Fight[] = [];
  for (const ev of events) {
    const eventName = ev.shortName ?? ev.name;
    const comps = ev.competitions ?? [];

    // Find the main event index for this card.
    // ESPN orders chronologically (prelims first, main last).
    // Main event = LAST 5-round bout, fallback to last competition.
    let mainIdx = -1;
    for (let i = comps.length - 1; i >= 0; i--) {
      if (comps[i].format?.regulation?.periods === 5) {
        mainIdx = i;
        break;
      }
    }
    if (mainIdx === -1 && comps.length > 0) mainIdx = comps.length - 1;

    for (let i = 0; i < comps.length; i++) {
      const comp = comps[i];
      // Skip already-completed bouts
      if (comp.status?.type?.completed) continue;

      const [a, b] = comp.competitors ?? [];
      if (!a?.athlete?.displayName || !b?.athlete?.displayName) continue;

      const fightId = `${ev.id}-${out.length}`;
      const fighterA = {
        name: a.athlete.displayName,
        country: a.athlete.flag?.alt ?? "—",
        record: a.records?.[0]?.summary ?? "—",
      };
      const fighterB = {
        name: b.athlete.displayName,
        country: b.athlete.flag?.alt ?? "—",
        record: b.records?.[0]?.summary ?? "—",
      };

      const isMain = i === mainIdx;
      const isTitleFight = (comp.note ?? "").toLowerCase().includes("title");

      out.push({
        id: fightId,
        eventName,
        date: comp.date ?? ev.date,
        venue: "",
        weightClass: inferWeightClass(comp),
        isMain,
        isTitleFight,
        fighterA,
        fighterB,
        prediction: syntheticPrediction(fightId, fighterA.name, fighterB.name),
      });
    }
  }
  return out;
}

export async function GET() {
  try {
    const res = await fetch(ESPN_URL, {
      next: { revalidate: 1800 },
      headers: { "User-Agent": "OctagonAI/1.0 (+https://octagon.ai)" },
    });
    if (!res.ok) {
      return NextResponse.json({ source: "fallback", error: `ESPN ${res.status}`, fights: [] }, { status: 200 });
    }
    const data: EspnResponse = await res.json();
    const fights = transform(data.events ?? []);
    return NextResponse.json({ source: "espn", count: fights.length, fights });
  } catch (e) {
    return NextResponse.json({
      source: "fallback",
      error: e instanceof Error ? e.message : "unknown",
      fights: [],
    });
  }
}
