"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Calendar, MapPin, Crown, Trophy, Lock, Sparkles, ChevronRight } from "lucide-react";
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

const SEGMENT_LABEL: Record<EventBout["cardSegment"], string> = {
  main: "Main Card",
  prelims: "Prelims",
  earlyprelims: "Early Prelims",
};

export default function EventDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { hasFullAccess } = useUser();
  const [data, setData] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/events/${id}`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 py-20 text-sm">
        <div className="font-medium">Failed to load event</div>
        <div className="text-muted-foreground">{error}</div>
        <Button asChild variant="ghost" size="sm" className="mt-2">
          <Link href="/">Back to dashboard</Link>
        </Button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6 max-w-5xl">
        <div className="h-8 w-40 rounded bg-muted animate-pulse" />
        <div className="h-32 rounded-lg border bg-card animate-pulse" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 rounded-lg border bg-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const date = new Date(data.date);
  const dateStr = date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const isPPV = /UFC \d{3}/.test(data.name) || /Freedom/i.test(data.name);

  // Group bouts by segment
  const grouped = data.bouts.reduce(
    (acc, b) => {
      (acc[b.cardSegment] ??= []).push(b);
      return acc;
    },
    {} as Record<EventBout["cardSegment"], EventBout[]>
  );

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
          <Badge variant={isPPV ? "default" : "outline"} className="gap-1">
            {isPPV ? <Trophy className="h-3 w-3" /> : null}
            {isPPV ? "PPV" : "Fight Night"}
          </Badge>
          <Badge variant="outline">{data.bouts.length} bouts</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">{data.name}</h1>
        <div className="flex items-center gap-4 mt-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" /> {dateStr}
          </span>
          {data.venue && data.venue !== "TBA" && (
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5" /> {data.venue}
              {data.city && ` · ${data.city}`}
            </span>
          )}
        </div>
      </div>

      {(["main", "prelims", "earlyprelims"] as const).map((seg) => {
        const list = grouped[seg];
        if (!list || list.length === 0) return null;
        return (
          <section key={seg} className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
                {SEGMENT_LABEL[seg]}
              </h2>
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-muted-foreground">{list.length} bouts</span>
            </div>
            <Card>
              <CardContent className="p-0">
                <div className="divide-y">
                  {list.map((bout, idx) => (
                    <Link
                      key={bout.id}
                      href={`/events/${id}/${bout.id}`}
                      className="block group"
                    >
                      <BoutRow
                        bout={bout}
                        isMain={seg === "main" && idx === 0}
                        unlocked={hasFullAccess}
                        onUpgrade={() => setUpgradeOpen(true)}
                      />
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>
        );
      })}

      <UpgradeModal open={upgradeOpen} onOpenChange={setUpgradeOpen} />
    </div>
  );
}

function BoutRow({
  bout,
  isMain,
  unlocked,
  onUpgrade,
}: {
  bout: EventBout;
  isMain: boolean;
  unlocked: boolean;
  onUpgrade: () => void;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,240px)_auto_minmax(0,240px)_1fr] gap-x-4 gap-y-2 items-center px-5 py-4 hover:bg-muted/30 transition-colors">
      {/* Top tags */}
      <div className="lg:hidden flex items-center gap-1.5 flex-wrap">
        {isMain && (
          <Badge className="gap-1">
            <Crown className="h-3 w-3" /> Main
          </Badge>
        )}
        {bout.isTitleFight && (
          <Badge variant="warning" className="gap-1">
            <Trophy className="h-3 w-3" /> Title
          </Badge>
        )}
        <Badge variant="outline">{bout.weightClass}</Badge>
      </div>

      <Fighter
        name={bout.fighterA.name}
        country={bout.fighterA.country}
        record={bout.fighterA.record}
        imageUrl={bout.fighterA.imageUrl ?? getFighterImage(bout.fighterA.name)}
        align="left"
      />
      <div className="hidden lg:grid place-items-center text-[10px] font-bold text-muted-foreground tracking-widest">
        VS
      </div>
      <div className="lg:hidden text-[10px] font-bold text-muted-foreground tracking-widest text-center">VS</div>
      <Fighter
        name={bout.fighterB.name}
        country={bout.fighterB.country}
        record={bout.fighterB.record}
        imageUrl={bout.fighterB.imageUrl ?? getFighterImage(bout.fighterB.name)}
        align="left"
      />

      {/* Right: weight + prediction */}
      <div className="flex flex-col items-end gap-1.5 min-w-[180px] relative">
        <ChevronRight className="absolute -right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hidden lg:block" />
        <div className="hidden lg:flex items-center gap-1.5 flex-wrap justify-end">
          {isMain && (
            <Badge className="gap-1">
              <Crown className="h-3 w-3" /> Main
            </Badge>
          )}
          {bout.isTitleFight && (
            <Badge variant="warning" className="gap-1">
              <Trophy className="h-3 w-3" /> Title
            </Badge>
          )}
          <Badge variant="outline" className="font-normal">
            {bout.weightClass}
          </Badge>
        </div>
        <PredictionBlock bout={bout} unlocked={unlocked} onUpgrade={onUpgrade} />
      </div>
    </div>
  );
}

function PredictionBlock({
  bout,
  unlocked,
  onUpgrade,
}: {
  bout: EventBout;
  unlocked: boolean;
  onUpgrade: () => void;
}) {
  if (!unlocked) {
    return (
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onUpgrade();
        }}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Lock className="h-3 w-3" /> Unlock prediction
      </button>
    );
  }
  return (
    <div className="text-xs text-right">
      <div className="inline-flex items-center gap-1.5">
        <Sparkles className="h-3 w-3 text-primary" />
        <span className="text-muted-foreground">Pick:</span>
        <span className="font-semibold">{bout.prediction.winner}</span>
        <Badge variant="secondary" className="tabular-nums">
          {bout.prediction.confidence}%
        </Badge>
      </div>
      <div className="text-[11px] text-muted-foreground mt-1">via {bout.prediction.method}</div>
    </div>
  );
}

function Fighter({
  name,
  country,
  record,
  imageUrl,
  align,
}: {
  name: string;
  country: string;
  record: string;
  imageUrl?: string;
  align: "left" | "right";
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 min-w-0",
        align === "right" ? "lg:flex-row-reverse lg:text-right" : ""
      )}
    >
      <FighterPhoto src={imageUrl} alt={name} size={48} className="border" />
      <div className="min-w-0">
        <div className="text-sm font-semibold truncate">{name}</div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          {country} · {record}
        </div>
      </div>
    </div>
  );
}
