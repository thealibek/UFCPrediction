"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Crown, Trophy, Sparkles, Lock, TrendingUp, Calendar, MapPin } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FighterPhoto } from "@/components/fighter-photo";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { UpgradeModal } from "@/components/upgrade-modal";
import { useUser } from "@/lib/user";
import type { EventDetail, EventBout } from "@/lib/events";
import { getFighterImage, extractAthleteId } from "@/lib/fighter-images";
import { cn } from "@/lib/utils";

export default function BoutDetailPage({ params }: { params: Promise<{ id: string; boutId: string }> }) {
  const { id, boutId } = use(params);
  const { hasFullAccess } = useUser();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/events/${id}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((d) => !cancelled && setEvent(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 py-20 text-sm">
        <div className="font-medium">Failed to load</div>
        <div className="text-muted-foreground">{error}</div>
        <Button asChild variant="ghost" size="sm" className="mt-2">
          <Link href={`/events/${id}`}>Back to event</Link>
        </Button>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="flex flex-col gap-6 max-w-4xl">
        <div className="h-6 w-40 rounded bg-muted animate-pulse" />
        <div className="h-64 rounded-lg border bg-card animate-pulse" />
        <div className="h-32 rounded-lg border bg-card animate-pulse" />
      </div>
    );
  }

  const bout = event.bouts.find((b) => b.id === boutId);
  if (!bout) {
    return (
      <div className="flex flex-col items-center gap-3 py-20 text-sm">
        <div className="font-medium">Bout not found</div>
        <Button asChild variant="ghost" size="sm">
          <Link href={`/events/${id}`}>Back to event</Link>
        </Button>
      </div>
    );
  }

  const date = new Date(event.date);
  const dateStr = date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const mainIndex = event.bouts.findIndex((b) => b.cardSegment === "main");
  const isMain = event.bouts[mainIndex]?.id === bout.id;

  return (
    <div className="flex flex-col gap-8 max-w-4xl">
      <div>
        <Link
          href={`/events/${id}`}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> {event.shortName ?? event.name}
        </Link>
        <div className="flex items-center gap-1.5 flex-wrap mb-3">
          {isMain && (
            <Badge className="gap-1">
              <Crown className="h-3 w-3" /> Main Event
            </Badge>
          )}
          {bout.isTitleFight && (
            <Badge variant="warning" className="gap-1">
              <Trophy className="h-3 w-3" /> Title Fight
            </Badge>
          )}
          <Badge variant="outline">{bout.weightClass}</Badge>
          {bout.isFiveRound && <Badge variant="outline">5 rounds</Badge>}
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">
          {bout.fighterA.name} <span className="text-muted-foreground font-normal">vs</span> {bout.fighterB.name}
        </h1>
        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" /> {dateStr}
          </span>
          {event.venue && event.venue !== "TBA" && (
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" /> {event.venue}
            </span>
          )}
        </div>
      </div>

      {/* Fighter comparison */}
      <Card>
        <CardContent className="p-6">
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
            <FighterCard side={bout.fighterA} align="right" />
            <div className="grid place-items-center text-xs font-bold text-muted-foreground tracking-widest">VS</div>
            <FighterCard side={bout.fighterB} align="left" />
          </div>
        </CardContent>
      </Card>

      {/* Tabs: Prediction / Stats */}
      <Tabs defaultValue="prediction" className="w-full">
        <TabsList className="h-10 p-1 w-full sm:w-auto">
          <TabsTrigger value="prediction" className="text-sm px-4 py-1.5 flex-1 sm:flex-none">
            <Sparkles className="h-3.5 w-3.5" /> Prediction
          </TabsTrigger>
          <TabsTrigger value="stats" className="text-sm px-4 py-1.5 flex-1 sm:flex-none">
            <TrendingUp className="h-3.5 w-3.5" /> Stats
          </TabsTrigger>
        </TabsList>
        <TabsContent value="prediction" className="mt-5">
          <PredictionPanel bout={bout} unlocked={hasFullAccess} onUpgrade={() => setUpgradeOpen(true)} />
        </TabsContent>
        <TabsContent value="stats" className="mt-5">
          <StatsPanel bout={bout} />
        </TabsContent>
      </Tabs>

      <UpgradeModal open={upgradeOpen} onOpenChange={setUpgradeOpen} />
    </div>
  );
}

function FighterCard({
  side,
  align,
}: {
  side: { name: string; country: string; record: string; flagUrl?: string; imageUrl?: string };
  align: "left" | "right";
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 min-w-0",
        align === "right" ? "flex-row-reverse text-right" : ""
      )}
    >
      <FighterPhoto
        src={side.imageUrl ?? getFighterImage(side.name)}
        alt={side.name}
        size={80}
        className="border"
        priority
      />
      <div className="min-w-0">
        <div className="text-base font-semibold truncate">{side.name}</div>
        <div className="text-xs text-muted-foreground mt-0.5">
          {side.country} · <span className="tabular-nums">{side.record}</span>
        </div>
      </div>
    </div>
  );
}

function PredictionPanel({
  bout,
  unlocked,
  onUpgrade,
}: {
  bout: EventBout;
  unlocked: boolean;
  onUpgrade: () => void;
}) {
  const { prediction, fighterA, fighterB } = bout;
  const winnerIsA = prediction.winner === fighterA.name;
  const winnerPct = prediction.confidence;
  const loserPct = 100 - winnerPct;

  return (
    <div className="relative">
      <div className={cn("space-y-4", !unlocked && "prediction-blur")}>
        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium inline-flex items-center gap-1.5">
                  <Sparkles className="h-3 w-3 text-primary" /> Predicted Winner
                </div>
                <div className="text-2xl font-semibold mt-2">{prediction.winner}</div>
                <Badge variant="outline" className="mt-2">
                  Method: {prediction.method}
                </Badge>
              </div>
              <div className="text-right">
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                  Confidence
                </div>
                <div className="text-5xl font-semibold tabular-nums tracking-tight mt-1">
                  {winnerPct}
                  <span className="text-2xl text-muted-foreground">%</span>
                </div>
                <Badge
                  variant={winnerPct >= 70 ? "success" : winnerPct >= 60 ? "secondary" : "warning"}
                  className="mt-1"
                >
                  {winnerPct >= 70 ? "High" : winnerPct >= 60 ? "Medium" : "Coin flip"}
                </Badge>
              </div>
            </div>

            <Separator className="my-6" />

            <div>
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                <span>Probability distribution</span>
                <span className="tabular-nums">
                  {winnerIsA ? winnerPct : loserPct}% / {winnerIsA ? loserPct : winnerPct}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-secondary overflow-hidden flex">
                <div
                  className={cn("transition-all", winnerIsA ? "bg-primary" : "bg-muted")}
                  style={{ width: `${winnerIsA ? winnerPct : loserPct}%` }}
                />
                <div className={cn("flex-1", winnerIsA ? "bg-muted" : "bg-primary")} />
              </div>
              <div className="flex items-center justify-between mt-1.5 text-xs">
                <span className={cn("font-medium", winnerIsA && "text-primary")}>{fighterA.name}</span>
                <span className={cn("font-medium", !winnerIsA && "text-primary")}>{fighterB.name}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
              Method breakdown
            </div>
            <div className="grid grid-cols-3 gap-3">
              {(["KO/TKO", "Submission", "Decision"] as const).map((m) => {
                const isPick = prediction.method === m;
                const pct = isPick ? Math.round(winnerPct * 0.7) : Math.round((100 - winnerPct * 0.7) / 2);
                return (
                  <div
                    key={m}
                    className={cn(
                      "rounded-md border p-3 text-center",
                      isPick && "border-primary bg-primary/5"
                    )}
                  >
                    <div className="text-xs text-muted-foreground">{m}</div>
                    <div className="text-lg font-semibold tabular-nums mt-1">{pct}%</div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2 inline-flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5" /> AI Reasoning
            </div>
            <p className="text-sm leading-relaxed text-foreground/85">
              Model gives {prediction.winner} a {winnerPct}% edge via {prediction.method.toLowerCase()}.
              {bout.isFiveRound
                ? " 5-round format favors cardio and championship experience."
                : " 3-round bout — early aggression and pace are decisive."}{" "}
              Full reasoning will be available once the Python model service is wired into this dashboard.
            </p>
          </CardContent>
        </Card>
      </div>

      {!unlocked && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-8">
          <div className="grid place-items-center h-14 w-14 rounded-full bg-background border shadow-md">
            <Lock className="h-5 w-5" />
          </div>
          <div className="text-center max-w-sm">
            <div className="text-lg font-semibold">Subscribe to unlock</div>
            <p className="text-sm text-muted-foreground mt-1">
              Get win probability, method breakdown and full reasoning for every bout.
            </p>
          </div>
          <Button onClick={onUpgrade} className="gap-1.5">
            <Crown className="h-4 w-4" /> Upgrade to Pro
          </Button>
        </div>
      )}
    </div>
  );
}

// ---------- Stats panel ----------

interface FighterProfile {
  id: string;
  name: string;
  record: string;
  weight?: string;
  height?: string;
  age?: number;
  country?: string;
  imageUrl?: string;
  stats: Record<string, string | number | undefined>;
}

const STAT_ROWS: Array<{ key: string; label: string; suffix?: string; higherIsBetter: boolean }> = [
  { key: "Sig Strk LPM", label: "Sig. Strikes Landed / Min", higherIsBetter: true },
  { key: "Sig Strk Acc", label: "Strike Accuracy", suffix: "%", higherIsBetter: true },
  { key: "Takedown Average", label: "Takedowns / 15 Min", higherIsBetter: true },
  { key: "Takedown Accuracy", label: "Takedown Accuracy", suffix: "%", higherIsBetter: true },
  { key: "Submission Average", label: "Submissions / 15 Min", higherIsBetter: true },
  { key: "KO Percentage", label: "KO/TKO Win %", suffix: "%", higherIsBetter: true },
  { key: "Decision Percentage", label: "Decision Win %", suffix: "%", higherIsBetter: true },
];

function StatsPanel({ bout }: { bout: EventBout }) {
  const idA = extractAthleteId(bout.fighterA.imageUrl ?? getFighterImage(bout.fighterA.name));
  const idB = extractAthleteId(bout.fighterB.imageUrl ?? getFighterImage(bout.fighterB.name));

  const [a, setA] = useState<FighterProfile | null>(null);
  const [b, setB] = useState<FighterProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [pa, pb] = await Promise.all([
          idA ? fetch(`/api/fighters/${idA}`).then((r) => (r.ok ? r.json() : null)) : null,
          idB ? fetch(`/api/fighters/${idB}`).then((r) => (r.ok ? r.json() : null)) : null,
        ]);
        if (cancelled) return;
        setA(pa);
        setB(pb);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed");
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [idA, idB]);

  if (!idA || !idB) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Stats unavailable — one or both fighters are not yet in the database.
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Failed to load stats: {error}
        </CardContent>
      </Card>
    );
  }

  if (!a || !b) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-16 rounded-lg border bg-card animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Bio strip */}
      <Card>
        <CardContent className="p-5">
          <div className="grid grid-cols-3 gap-3 items-center">
            <BioColumn p={a} align="right" />
            <div className="text-center text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
              Bio
            </div>
            <BioColumn p={b} align="left" />
          </div>
          <Separator className="my-4" />
          <div className="grid grid-cols-3 gap-2 text-xs">
            <BioRow label="Record" a={a.record} b={b.record} />
            <BioRow label="Weight" a={a.weight} b={b.weight} />
            <BioRow label="Height" a={a.height} b={b.height} />
            <BioRow label="Age" a={a.age?.toString()} b={b.age?.toString()} />
            <BioRow label="Country" a={a.country} b={b.country} />
          </div>
        </CardContent>
      </Card>

      {/* Stat comparison rows */}
      <Card>
        <CardContent className="p-5">
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-4">
            Career Stats Comparison
          </div>
          <div className="flex flex-col gap-4">
            {STAT_ROWS.map((row) => (
              <StatRow
                key={row.key}
                label={row.label}
                suffix={row.suffix}
                higherIsBetter={row.higherIsBetter}
                aValue={toNum(a.stats[row.key])}
                bValue={toNum(b.stats[row.key])}
              />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function toNum(v: string | number | undefined): number | null {
  if (v == null || v === "") return null;
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function BioColumn({ p, align }: { p: FighterProfile; align: "left" | "right" }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 min-w-0",
        align === "right" ? "flex-row-reverse text-right" : ""
      )}
    >
      <FighterPhoto src={p.imageUrl} alt={p.name} size={40} />
      <div className="min-w-0 text-xs font-semibold truncate">{p.name}</div>
    </div>
  );
}

function BioRow({ label, a, b }: { label: string; a?: string; b?: string }) {
  return (
    <>
      <div className="text-right tabular-nums text-foreground/85">{a ?? "—"}</div>
      <div className="text-center text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div className="text-left tabular-nums text-foreground/85">{b ?? "—"}</div>
    </>
  );
}

function StatRow({
  label,
  suffix,
  aValue,
  bValue,
  higherIsBetter,
}: {
  label: string;
  suffix?: string;
  aValue: number | null;
  bValue: number | null;
  higherIsBetter: boolean;
}) {
  const aWins = aValue != null && bValue != null && (higherIsBetter ? aValue > bValue : aValue < bValue);
  const bWins = aValue != null && bValue != null && (higherIsBetter ? bValue > aValue : bValue < aValue);
  const max = Math.max(aValue ?? 0, bValue ?? 0, 1);
  const aPct = aValue == null ? 0 : (aValue / max) * 100;
  const bPct = bValue == null ? 0 : (bValue / max) * 100;

  return (
    <div>
      <div className="grid grid-cols-3 items-center gap-3 mb-1.5">
        <div
          className={cn(
            "text-right text-sm tabular-nums font-semibold",
            aWins ? "text-foreground" : "text-muted-foreground"
          )}
        >
          {aValue != null ? aValue.toFixed(2) : "—"}
          {suffix && aValue != null && <span className="text-xs ml-0.5">{suffix}</span>}
        </div>
        <div className="text-center text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
          {label}
        </div>
        <div
          className={cn(
            "text-left text-sm tabular-nums font-semibold",
            bWins ? "text-foreground" : "text-muted-foreground"
          )}
        >
          {bValue != null ? bValue.toFixed(2) : "—"}
          {suffix && bValue != null && <span className="text-xs ml-0.5">{suffix}</span>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1">
        {/* Fighter A bar — fills from right */}
        <div className="h-1.5 rounded-full bg-secondary overflow-hidden flex justify-end">
          <div
            className={cn("h-full rounded-full transition-all", aWins ? "bg-primary" : "bg-muted-foreground/40")}
            style={{ width: `${aPct}%` }}
          />
        </div>
        {/* Fighter B bar — fills from left */}
        <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all", bWins ? "bg-primary" : "bg-muted-foreground/40")}
            style={{ width: `${bPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
