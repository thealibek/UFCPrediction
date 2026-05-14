"use client";

import Link from "next/link";
import { Calendar, ArrowRight, Crown, Trophy } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import type { Fight } from "@/lib/fights";
import { cn } from "@/lib/utils";

export function FightCard({ fight }: { fight: Fight }) {
  const date = new Date(fight.date).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  return (
    <Card className="overflow-hidden group transition-all hover:shadow-md hover:-translate-y-0.5 duration-200">
      <CardContent className="p-0">
        {/* Top tags */}
        <div className="flex items-center justify-between px-5 pt-5">
          <div className="flex items-center gap-1.5 flex-wrap">
            {fight.isMain && (
              <Badge className="gap-1">
                <Crown className="h-3 w-3" /> Main
              </Badge>
            )}
            {fight.isTitleFight && (
              <Badge variant="warning" className="gap-1">
                <Trophy className="h-3 w-3" /> Title
              </Badge>
            )}
            <Badge variant="outline">{fight.weightClass}</Badge>
          </div>
          <div className="text-xs text-muted-foreground inline-flex items-center gap-1">
            <Calendar className="h-3 w-3" /> {date}
          </div>
        </div>

        {/* Fighters */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-5 py-6">
          <FighterFace fighter={fight.fighterA} align="right" />
          <div className="grid place-items-center text-[10px] font-bold text-muted-foreground tracking-widest">
            VS
          </div>
          <FighterFace fighter={fight.fighterB} align="left" />
        </div>

        {/* Footer with CTA */}
        <div className="border-t bg-muted/20 px-5 py-3 flex items-center justify-between">
          <div className="text-xs text-muted-foreground truncate">{fight.eventName}</div>
          <Button asChild size="sm" variant="ghost" className="h-7 -mr-2 gap-1 text-xs">
            <Link href={`/fights/${fight.id}`}>
              View Fight <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function FighterFace({
  fighter,
  align,
}: {
  fighter: { name: string; country: string; record: string; photoUrl?: string };
  align: "left" | "right";
}) {
  const initials = fighter.name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("");
  return (
    <div className={cn("flex items-center gap-3 min-w-0", align === "right" ? "flex-row-reverse text-right" : "")}>
      <Avatar className="h-12 w-12 border bg-secondary">
        {fighter.photoUrl && <AvatarImage src={fighter.photoUrl} alt={fighter.name} />}
        <AvatarFallback className="text-xs font-semibold">{initials}</AvatarFallback>
      </Avatar>
      <div className="min-w-0">
        <div className="text-sm font-semibold truncate">{fighter.name}</div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          {fighter.country} · {fighter.record}
        </div>
      </div>
    </div>
  );
}
