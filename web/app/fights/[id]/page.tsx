"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  MapPin,
  Crown,
  Trophy,
  Lock,
  Sparkles,
  TrendingUp,
  Target,
} from "lucide-react";
import { getFightById, type Fight } from "@/lib/fights";
import { useUser } from "@/lib/user";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { UpgradeModal } from "@/components/upgrade-modal";
import { cn } from "@/lib/utils";

export default function FightDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const localFight = getFightById(id);
  const { hasFullAccess } = useUser();
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [fight, setFight] = useState<Fight | undefined>(localFight);
  const [loading, setLoading] = useState(!localFight);

  useEffect(() => {
    if (localFight) return;
    let cancelled = false;
    fetch("/api/upcoming-fights")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const found = (data.fights as Fight[] | undefined)?.find((f) => f.id === id);
        setFight(found);
        setLoading(false);
      })
      .catch(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [id, localFight]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">
        Loading fight...
      </div>
    );
  }

  if (!fight) notFound();

  const date = new Date(fight.date).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex flex-col gap-8 max-w-5xl">
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-4"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to dashboard
        </Link>
        <div className="flex items-center gap-1.5 flex-wrap mb-3">
          {fight.isMain && (
            <Badge className="gap-1">
              <Crown className="h-3 w-3" /> Main Event
            </Badge>
          )}
          {fight.isTitleFight && (
            <Badge variant="warning" className="gap-1">
              <Trophy className="h-3 w-3" /> Title Fight
            </Badge>
          )}
          <Badge variant="outline">{fight.weightClass}</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">
          {fight.fighterA.name} <span className="text-muted-foreground font-normal">vs</span> {fight.fighterB.name}
        </h1>
        <p className="text-sm text-muted-foreground mt-1.5">{fight.eventName}</p>
        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" /> {date}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5" /> {fight.venue}
          </span>
        </div>
      </div>

      <Tabs defaultValue="prediction">
        <TabsList className="h-9">
          <TabsTrigger value="overview" className="text-xs px-4">Overview</TabsTrigger>
          <TabsTrigger value="prediction" className="text-xs px-4 gap-1.5">
            <Sparkles className="h-3 w-3" /> Prediction
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid md:grid-cols-2 gap-4">
            <FighterCard fighter={fight.fighterA} />
            <FighterCard fighter={fight.fighterB} />
          </div>
        </TabsContent>

        <TabsContent value="prediction" className="mt-6">
          <PredictionTab
            fight={fight}
            unlocked={hasFullAccess}
            onUpgrade={() => setUpgradeOpen(true)}
          />
        </TabsContent>
      </Tabs>

      <UpgradeModal open={upgradeOpen} onOpenChange={setUpgradeOpen} />
    </div>
  );
}

function FighterCard({ fighter }: { fighter: ReturnType<typeof getFightById> extends infer F ? F extends { fighterA: infer X } ? X : never : never }) {
  if (!fighter) return null;
  const initials = fighter.name.split(" ").map((n: string) => n[0]).slice(0, 2).join("");
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16 border bg-secondary">
            {fighter.photoUrl && <AvatarImage src={fighter.photoUrl} alt={fighter.name} />}
            <AvatarFallback className="text-base font-semibold">{initials}</AvatarFallback>
          </Avatar>
          <div>
            <div className="text-base font-semibold">{fighter.name}</div>
            <div className="text-xs text-muted-foreground">
              {fighter.country} · {fighter.record}
            </div>
          </div>
        </div>
        <Separator className="my-4" />
        <div className="grid grid-cols-2 gap-4 text-sm">
          <Field label="Age" value={fighter.age ?? "—"} />
          <Field label="Stance" value={fighter.stance ?? "—"} />
          <Field label="Height" value={fighter.height ?? "—"} />
          <Field label="Reach" value={fighter.reach ?? "—"} />
        </div>
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">{label}</div>
      <div className="text-sm font-medium mt-0.5">{value}</div>
    </div>
  );
}

function PredictionTab({
  fight,
  unlocked,
  onUpgrade,
}: {
  fight: NonNullable<ReturnType<typeof getFightById>>;
  unlocked: boolean;
  onUpgrade: () => void;
}) {
  const { prediction } = fight;

  return (
    <div className="relative">
      <div className={cn("space-y-4", !unlocked && "prediction-blur")}>
        {/* Winner card */}
        <Card className="overflow-hidden">
          <CardContent className="p-6">
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                  Predicted Winner
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
                  {prediction.confidence}<span className="text-2xl text-muted-foreground">%</span>
                </div>
                {typeof prediction.edgeVsVegas === "number" && (
                  <Badge variant="success" className="mt-1 gap-1">
                    <TrendingUp className="h-3 w-3" /> +{prediction.edgeVsVegas}pp vs Vegas
                  </Badge>
                )}
              </div>
            </div>

            <Separator className="my-6" />

            {/* Confidence bar */}
            <div>
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                <span>Probability distribution</span>
                <span className="tabular-nums">{prediction.confidence}% / {100 - prediction.confidence}%</span>
              </div>
              <div className="h-2 rounded-full bg-secondary overflow-hidden flex">
                <div
                  className="bg-primary transition-all"
                  style={{ width: `${prediction.confidence}%` }}
                />
                <div className="flex-1 bg-muted" />
              </div>
              <div className="flex items-center justify-between mt-1.5 text-xs">
                <span className="font-medium">{fight.fighterA.name}</span>
                <span className="text-muted-foreground">{fight.fighterB.name}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recommended bet */}
        {prediction.recommendedBet && (
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
                <Target className="h-3.5 w-3.5" />
                Recommended bet
              </div>
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="text-base font-semibold">{prediction.recommendedBet}</div>
                <Badge variant="success">Value pick</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Reasoning */}
        <Card>
          <CardContent className="p-6">
            <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
              AI Reasoning
            </div>
            <p className="text-sm leading-relaxed text-foreground/85">{prediction.reasoning}</p>
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
              Get win probability, betting recommendations and full reasoning for every fight on the card.
            </p>
          </div>
          <Button onClick={onUpgrade} className="gap-1.5">
            <Crown className="h-4 w-4" />
            Upgrade to Pro
          </Button>
        </div>
      )}
    </div>
  );
}
