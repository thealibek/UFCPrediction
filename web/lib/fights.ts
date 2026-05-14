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

export interface PastFight {
  id: string;
  eventName: string;
  date: string;
  weightClass: string;
  fighterA: FighterMini;
  fighterB: FighterMini;
  predictedWinner: string;
  predictedConfidence: number;
  actualWinner: string;
  actualMethod: "KO/TKO" | "Submission" | "Decision";
  actualRound?: number;
}

export const pastFights: PastFight[] = [
  {
    id: "p1",
    eventName: "UFC FN: Cannonier vs. Imavov",
    date: "2026-05-10",
    weightClass: "Middleweight",
    fighterA: { name: "Jared Cannonier", country: "US", record: "17-8" },
    fighterB: { name: "Nassourdine Imavov", country: "FR", record: "15-4" },
    predictedWinner: "Nassourdine Imavov",
    predictedConfidence: 59,
    actualWinner: "Nassourdine Imavov",
    actualMethod: "KO/TKO",
    actualRound: 2,
  },
  {
    id: "p2",
    eventName: "UFC 331: Pereira vs. Ankalaev 2",
    date: "2026-05-03",
    weightClass: "Light Heavyweight",
    fighterA: { name: "Alex Pereira", country: "BR", record: "12-3" },
    fighterB: { name: "Magomed Ankalaev", country: "RU", record: "20-1" },
    predictedWinner: "Alex Pereira",
    predictedConfidence: 58,
    actualWinner: "Magomed Ankalaev",
    actualMethod: "Decision",
  },
  {
    id: "p3",
    eventName: "UFC 331: Pereira vs. Ankalaev 2",
    date: "2026-05-03",
    weightClass: "Featherweight",
    fighterA: { name: "Movsar Evloev", country: "RU", record: "19-0" },
    fighterB: { name: "Diego Lopes", country: "BR", record: "26-6" },
    predictedWinner: "Movsar Evloev",
    predictedConfidence: 66,
    actualWinner: "Movsar Evloev",
    actualMethod: "Decision",
  },
  {
    id: "p4",
    eventName: "UFC 330: Topuria vs. Oliveira",
    date: "2026-04-25",
    weightClass: "Lightweight",
    fighterA: { name: "Ilia Topuria", country: "ES", record: "17-0" },
    fighterB: { name: "Charles Oliveira", country: "BR", record: "35-11" },
    predictedWinner: "Ilia Topuria",
    predictedConfidence: 71,
    actualWinner: "Ilia Topuria",
    actualMethod: "KO/TKO",
    actualRound: 3,
  },
  {
    id: "p5",
    eventName: "UFC 330: Topuria vs. Oliveira",
    date: "2026-04-25",
    weightClass: "Welterweight",
    fighterA: { name: "Belal Muhammad", country: "PS", record: "24-4" },
    fighterB: { name: "Shavkat Rakhmonov", country: "KZ", record: "20-0" },
    predictedWinner: "Shavkat Rakhmonov",
    predictedConfidence: 68,
    actualWinner: "Shavkat Rakhmonov",
    actualMethod: "Submission",
    actualRound: 2,
  },
  {
    id: "p6",
    eventName: "UFC FN: Hill vs. Walker",
    date: "2026-04-18",
    weightClass: "Light Heavyweight",
    fighterA: { name: "Jamahal Hill", country: "US", record: "13-2" },
    fighterB: { name: "Johnny Walker", country: "BR", record: "21-9" },
    predictedWinner: "Jamahal Hill",
    predictedConfidence: 64,
    actualWinner: "Jamahal Hill",
    actualMethod: "KO/TKO",
    actualRound: 2,
  },
];

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
    eventName: "UFC 332: Jones vs. Aspinall",
    date: "2026-05-30T22:00:00Z",
    venue: "T-Mobile Arena, Las Vegas",
    weightClass: "Heavyweight",
    isMain: true,
    isTitleFight: true,
    fighterA: { name: "Jon Jones", country: "US", record: "27-1", age: 38, height: "6'4\"", reach: "84.5\"", stance: "Orthodox" },
    fighterB: { name: "Tom Aspinall", country: "GB", record: "15-3", age: 33, height: "6'5\"", reach: "78\"", stance: "Orthodox" },
    prediction: {
      winner: "Tom Aspinall",
      confidence: 62,
      method: "KO/TKO",
      reasoning:
        "Aspinall's hand speed + cardio in a 5-round fight is the kryptonite for a 38-year-old Jones. Aspinall's last 6 fights average 1:34 finish time — fastest in HW history. Our model weights age-decline curves heavily for fighters >35, and Jones has had two long layoffs since the Gane fight. Expect Aspinall to land first big shot in R1 or R2.",
      recommendedBet: "Aspinall by KO/TKO @ +110",
      edgeVsVegas: 9,
    },
  },
  {
    id: "2",
    eventName: "UFC 332: Jones vs. Aspinall",
    date: "2026-05-30T22:00:00Z",
    venue: "T-Mobile Arena, Las Vegas",
    weightClass: "Bantamweight",
    isMain: false,
    isTitleFight: true,
    fighterA: { name: "Sean O'Malley", country: "US", record: "18-2" },
    fighterB: { name: "Petr Yan", country: "RU", record: "18-5" },
    prediction: {
      winner: "Petr Yan",
      confidence: 61,
      method: "Decision",
      reasoning:
        "Yan's volume and pressure outwork O'Malley's range game. Sugar's TDD has been suspect when pressed against the cage.",
    },
  },
  {
    id: "3",
    eventName: "UFC Fight Night: Edwards vs. Rakhmonov",
    date: "2026-06-13T20:00:00Z",
    venue: "O2 Arena, London",
    weightClass: "Welterweight",
    isMain: true,
    fighterA: { name: "Leon Edwards", country: "GB", record: "22-4" },
    fighterB: { name: "Shavkat Rakhmonov", country: "KZ", record: "20-0" },
    prediction: {
      winner: "Shavkat Rakhmonov",
      confidence: 67,
      method: "Submission",
      reasoning:
        "100% finish rate vs Edwards' grappling vulnerability shown in the Belal rematch. Home crowd gives Edwards a small bump but not enough.",
      recommendedBet: "Rakhmonov by Submission @ +220",
      edgeVsVegas: 6,
    },
  },
  {
    id: "4",
    eventName: "UFC Fight Night: Edwards vs. Rakhmonov",
    date: "2026-06-13T20:00:00Z",
    venue: "O2 Arena, London",
    weightClass: "Bantamweight",
    isMain: false,
    fighterA: { name: "Umar Nurmagomedov", country: "RU", record: "18-1" },
    fighterB: { name: "Cory Sandhagen", country: "US", record: "17-5" },
    prediction: {
      winner: "Umar Nurmagomedov",
      confidence: 65,
      method: "Decision",
      reasoning: "Wrestling base + cardio. Umar controls rounds 1-3, Sandhagen rallies but loses on cards.",
    },
  },
  {
    id: "5",
    eventName: "UFC 333: Du Plessis vs. Chimaev",
    date: "2026-06-27T22:00:00Z",
    venue: "Madison Square Garden, NYC",
    weightClass: "Middleweight",
    isMain: true,
    isTitleFight: true,
    fighterA: { name: "Dricus du Plessis", country: "ZA", record: "23-2" },
    fighterB: { name: "Khamzat Chimaev", country: "AE", record: "14-0" },
    prediction: {
      winner: "Khamzat Chimaev",
      confidence: 69,
      method: "Submission",
      reasoning:
        "Khamzat's takedown average (4.2/15min) overwhelms DDP's awkward but stoppable defense. DDP's cardio is elite but Khamzat's finishing rate from top position is league-leading.",
      recommendedBet: "Chimaev inside distance @ +140",
      edgeVsVegas: 5,
    },
  },
  {
    id: "6",
    eventName: "UFC 333: Du Plessis vs. Chimaev",
    date: "2026-06-27T22:00:00Z",
    venue: "Madison Square Garden, NYC",
    weightClass: "Women's Bantamweight",
    isMain: false,
    isTitleFight: true,
    fighterA: { name: "Kayla Harrison", country: "US", record: "19-1" },
    fighterB: { name: "Julianna Peña", country: "US", record: "13-5" },
    prediction: {
      winner: "Kayla Harrison",
      confidence: 78,
      method: "Submission",
      reasoning:
        "Olympic judo + size + cardio advantage. Peña's only path is durability, but Kayla's mat control is suffocating. High-confidence pick (78% bin = 88% real accuracy historically).",
    },
  },
  {
    id: "7",
    eventName: "UFC 334: Makhachev vs. Tsarukyan 2",
    date: "2026-07-11T22:00:00Z",
    venue: "Etihad Arena, Abu Dhabi",
    weightClass: "Lightweight",
    isMain: true,
    isTitleFight: true,
    fighterA: { name: "Islam Makhachev", country: "RU", record: "26-1" },
    fighterB: { name: "Arman Tsarukyan", country: "AM", record: "22-3" },
    prediction: {
      winner: "Islam Makhachev",
      confidence: 56,
      method: "Decision",
      reasoning:
        "Closest fight on the schedule. Tsarukyan has improved striking and the first fight was razor-close. Slight edge to Islam from championship rounds experience and cage IQ.",
    },
  },
  {
    id: "8",
    eventName: "UFC 334: Makhachev vs. Tsarukyan 2",
    date: "2026-07-11T22:00:00Z",
    venue: "Etihad Arena, Abu Dhabi",
    weightClass: "Featherweight",
    isMain: false,
    fighterA: { name: "Max Holloway", country: "US", record: "27-8" },
    fighterB: { name: "Yair Rodríguez", country: "MX", record: "16-5" },
    prediction: {
      winner: "Max Holloway",
      confidence: 70,
      method: "Decision",
      reasoning: "Volume + chin + 5-round cardio. Yair's unpredictability is fun but Holloway breaks him by R3.",
    },
  },
];
