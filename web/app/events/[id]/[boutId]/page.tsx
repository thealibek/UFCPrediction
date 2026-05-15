"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Crown, Trophy, Sparkles, Lock, TrendingUp, Calendar, MapPin } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FighterPhoto } from "@/components/fighter-photo";
import { Separator } from "@/components/ui/separator";
import { UpgradeModal } from "@/components/upgrade-modal";
import { useUser } from "@/lib/user";
import type { EventDetail, EventBout } from "@/lib/events";
import { getFighterImage } from "@/lib/fighter-images";
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

      {/* Prediction */}
      <PredictionPanel bout={bout} unlocked={hasFullAccess} onUpgrade={() => setUpgradeOpen(true)} />

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
