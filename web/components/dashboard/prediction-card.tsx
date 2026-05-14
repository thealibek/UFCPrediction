"use client";

import { Lock, Calendar, MapPin, Crown, Trophy } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { Fight } from "@/lib/fights";

interface Props {
  fight: Fight;
  unlocked: boolean;
  onUpgrade: () => void;
}

function confidenceTone(conf: number) {
  if (conf >= 70) return { label: "High", variant: "success" as const };
  if (conf >= 60) return { label: "Medium", variant: "secondary" as const };
  return { label: "Coin flip", variant: "warning" as const };
}

export function PredictionCard({ fight, unlocked, onUpgrade }: Props) {
  const date = new Date(fight.date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const tone = confidenceTone(fight.prediction.confidence);

  return (
    <Card className="overflow-hidden transition-all hover:shadow-md">
      <CardContent className="p-0">
        {/* Header */}
        <div className="flex items-start justify-between p-5 pb-4">
          <div className="flex flex-col gap-1.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              {fight.isMain && (
                <Badge variant="default" className="gap-1">
                  <Crown className="h-3 w-3" /> Main Event
                </Badge>
              )}
              {fight.isTitleFight && (
                <Badge variant="warning" className="gap-1">
                  <Trophy className="h-3 w-3" /> Title
                </Badge>
              )}
              <Badge variant="outline">{fight.weightClass}</Badge>
            </div>
            <div className="text-sm font-medium text-foreground truncate">{fight.eventName}</div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <Calendar className="h-3 w-3" /> {date}
              </span>
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" /> {fight.venue}
              </span>
            </div>
          </div>
        </div>

        {/* Fighters */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 px-5 py-3">
          <FighterBlock
            name={fight.fighterA.name}
            country={fight.fighterA.country}
            record={fight.fighterA.record}
            align="right"
            highlight={unlocked && fight.prediction.winner === fight.fighterA.name}
          />
          <div className="grid place-items-center text-xs font-bold text-muted-foreground tracking-wider">VS</div>
          <FighterBlock
            name={fight.fighterB.name}
            country={fight.fighterB.country}
            record={fight.fighterB.record}
            align="left"
            highlight={unlocked && fight.prediction.winner === fight.fighterB.name}
          />
        </div>

        <Separator />

        {/* Prediction */}
        <div className="relative p-5 pt-4">
          <div className="text-xs uppercase tracking-wider text-muted-foreground mb-3 font-medium">
            AI Prediction
          </div>

          <div className={cn("space-y-3", !unlocked && "prediction-blur")}>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs text-muted-foreground">Predicted winner</div>
                <div className="text-base font-semibold mt-0.5">{fight.prediction.winner}</div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Confidence</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-base font-semibold tabular-nums">{fight.prediction.confidence}%</span>
                  <Badge variant={tone.variant}>{tone.label}</Badge>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground">Method:</span>
              <Badge variant="outline">{fight.prediction.method}</Badge>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">{fight.prediction.reasoning}</p>
          </div>

          {!unlocked && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-5">
              <div className="grid place-items-center h-10 w-10 rounded-full bg-background border shadow-sm">
                <Lock className="h-4 w-4" />
              </div>
              <div className="text-center max-w-[260px]">
                <div className="text-sm font-medium">Subscribe to unlock full predictions</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  Get win probability, method, round and reasoning for every fight.
                </div>
              </div>
              <Button size="sm" onClick={onUpgrade} className="gap-1.5">
                <Crown className="h-3.5 w-3.5" />
                Upgrade to Pro
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function FighterBlock({
  name,
  country,
  record,
  align,
  highlight,
}: {
  name: string;
  country: string;
  record: string;
  align: "left" | "right";
  highlight: boolean;
}) {
  return (
    <div className={cn("flex flex-col gap-0.5 min-w-0", align === "right" ? "items-end text-right" : "items-start")}>
      <div
        className={cn(
          "text-sm font-semibold truncate w-full transition-colors",
          align === "right" ? "text-right" : "text-left",
          highlight && "text-primary"
        )}
      >
        {name}
      </div>
      <div className="text-xs text-muted-foreground">
        {country} · {record}
      </div>
    </div>
  );
}
