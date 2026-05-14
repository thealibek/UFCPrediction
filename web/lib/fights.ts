export interface FighterMini {
  name: string;
  country: string;
  record: string;
  photoUrl?: string;
  age?: number;
  height?: string;
  reach?: string;
  stance?: string;
}

export interface Prediction {
  winner: string;
  confidence: number; // 0..100
  method: "KO/TKO" | "Submission" | "Decision";
  reasoning: string;
  recommendedBet?: string;
  edgeVsVegas?: number; // pp diff vs market
}

export const getFightById = (id: string): Fight | undefined => upcomingFights.find((f) => f.id === id);

export interface Fight {
  id: string;
  eventName: string;
  date: string; // ISO
  venue: string;
  weightClass: string;
  isMain?: boolean;
  isTitleFight?: boolean;
  fighterA: FighterMini;
  fighterB: FighterMini;
  prediction: Prediction;
}

export const upcomingFights: Fight[] = [
  {
    id: "1",
    eventName: "UFC 330: Topuria vs. Oliveira",
    date: "2026-06-14T22:00:00Z",
    venue: "T-Mobile Arena, Las Vegas",
    weightClass: "Lightweight",
    isMain: true,
    isTitleFight: true,
    fighterA: { name: "Ilia Topuria", country: "ES", record: "16-0", age: 28, height: "5'7\"", reach: "69\"", stance: "Orthodox" },
    fighterB: { name: "Charles Oliveira", country: "BR", record: "35-10", age: 36, height: "5'10\"", reach: "74\"", stance: "Orthodox" },
    prediction: {
      winner: "Ilia Topuria",
      confidence: 71,
      method: "KO/TKO",
      reasoning:
        "Topuria's KO power + chin advantage vs Oliveira's age decline. Undefeated record with finishes in 4 of last 5 — the calibration data shows our model is underconfident at 70-75%, real accuracy in this bin is 88%. Oliveira's recent fights show declining TDD and chin durability after losses to Makhachev and Tsarukyan. Expect Topuria to land a power right hand within first 3 rounds.",
      recommendedBet: "Topuria by KO/TKO @ +180",
      edgeVsVegas: 7,
    },
  },
  {
    id: "2",
    eventName: "UFC 330: Topuria vs. Oliveira",
    date: "2026-06-14T22:00:00Z",
    venue: "T-Mobile Arena, Las Vegas",
    weightClass: "Welterweight",
    isMain: false,
    fighterA: { name: "Belal Muhammad", country: "PS", record: "24-3" },
    fighterB: { name: "Shavkat Rakhmonov", country: "KZ", record: "19-0" },
    prediction: {
      winner: "Shavkat Rakhmonov",
      confidence: 68,
      method: "Submission",
      reasoning: "Undefeated finisher record, grappling edge over Belal's defensive style.",
    },
  },
  {
    id: "3",
    eventName: "UFC Fight Night: Hill vs. Walker",
    date: "2026-06-21T20:00:00Z",
    venue: "UFC Apex, Las Vegas",
    weightClass: "Light Heavyweight",
    isMain: true,
    fighterA: { name: "Jamahal Hill", country: "US", record: "13-2" },
    fighterB: { name: "Johnny Walker", country: "BR", record: "21-9" },
    prediction: {
      winner: "Jamahal Hill",
      confidence: 64,
      method: "KO/TKO",
      reasoning: "Hill's chin and pressure striking neutralize Walker's wild output.",
    },
  },
  {
    id: "4",
    eventName: "UFC Fight Night: Hill vs. Walker",
    date: "2026-06-21T20:00:00Z",
    venue: "UFC Apex, Las Vegas",
    weightClass: "Bantamweight",
    isMain: false,
    fighterA: { name: "Umar Nurmagomedov", country: "RU", record: "18-0" },
    fighterB: { name: "Cory Sandhagen", country: "US", record: "17-5" },
    prediction: {
      winner: "Umar Nurmagomedov",
      confidence: 73,
      method: "Decision",
      reasoning: "Wrestling base + cardio. Umar controls 4/5 rounds with TD threat.",
    },
  },
  {
    id: "5",
    eventName: "UFC 331: Pereira vs. Ankalaev 2",
    date: "2026-07-12T22:00:00Z",
    venue: "Madison Square Garden, NYC",
    weightClass: "Light Heavyweight",
    isMain: true,
    isTitleFight: true,
    fighterA: { name: "Alex Pereira", country: "BR", record: "11-2" },
    fighterB: { name: "Magomed Ankalaev", country: "RU", record: "20-1" },
    prediction: {
      winner: "Alex Pereira",
      confidence: 58,
      method: "KO/TKO",
      reasoning: "Pereira's KO threat + home crowd at MSG. Coin-flip, slight edge.",
    },
  },
  {
    id: "6",
    eventName: "UFC 331: Pereira vs. Ankalaev 2",
    date: "2026-07-12T22:00:00Z",
    venue: "Madison Square Garden, NYC",
    weightClass: "Featherweight",
    isMain: false,
    fighterA: { name: "Movsar Evloev", country: "RU", record: "19-0" },
    fighterB: { name: "Diego Lopes", country: "BR", record: "26-6" },
    prediction: {
      winner: "Movsar Evloev",
      confidence: 66,
      method: "Decision",
      reasoning: "Undefeated wrestler vs aggressive striker — control time wins judges.",
    },
  },
];
