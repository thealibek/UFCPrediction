export interface EventBout {
  id: string;
  matchNumber?: number;
  cardSegment: "main" | "prelims" | "earlyprelims";
  weightClass: string;
  isTitleFight: boolean;
  isFiveRound: boolean;
  fighterA: { name: string; country: string; record: string; flagUrl?: string; imageUrl?: string };
  fighterB: { name: string; country: string; record: string; flagUrl?: string; imageUrl?: string };
  prediction: {
    winner: string;
    confidence: number;
    method: "KO/TKO" | "Submission" | "Decision";
  };
}

export interface EventSummary {
  id: string;
  name: string;          // "UFC Fight Night: Allen vs. Costa"
  shortName?: string;
  date: string;          // ISO
  venue: string;
  city: string;
  mainEvent: {           // parsed from name
    fighterAName: string;
    fighterBName: string;
    fighterAImage?: string;
    fighterBImage?: string;
  };
  fightCount?: number;   // optional, only on detail
}

export interface EventDetail extends EventSummary {
  bouts: EventBout[];
}

// Parse "UFC Fight Night: Allen vs. Costa" -> { a: "Allen", b: "Costa" }
export function parseMainEvent(name: string): { fighterAName: string; fighterBName: string } {
  const colonIdx = name.lastIndexOf(":");
  const tail = colonIdx >= 0 ? name.slice(colonIdx + 1).trim() : name;
  const match = tail.match(/^(.+?)\s+vs\.?\s+(.+)$/i);
  if (match) return { fighterAName: match[1].trim(), fighterBName: match[2].trim() };
  return { fighterAName: tail, fighterBName: "" };
}

// Deterministic synthetic prediction (placeholder until Python model is wired)
export function syntheticPrediction(seed: string, a: string, b: string) {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const confidence = 55 + (h % 25);
  const winner = h % 2 === 0 ? a : b;
  const methods: Array<"KO/TKO" | "Submission" | "Decision"> = ["KO/TKO", "Submission", "Decision"];
  return { winner, confidence, method: methods[h % 3] };
}
