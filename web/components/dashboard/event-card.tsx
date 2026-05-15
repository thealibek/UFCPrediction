"use client";

import Link from "next/link";
import { Calendar, MapPin, ArrowRight, Trophy } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FighterPhoto } from "@/components/fighter-photo";
import { motion } from "motion/react";
import { ANIMATIONS_ENABLED, fadeUp } from "@/lib/animations";
import type { EventSummary } from "@/lib/events";
import { getFighterImage } from "@/lib/fighter-images";
import { cn } from "@/lib/utils";


export function EventCard({ event }: { event: EventSummary }) {
  const date = new Date(event.date);
  const dateStr = date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
  const isPPV = /UFC \d{3}/.test(event.name) || /Freedom/i.test(event.name);
  const cardTitle = event.shortName ?? event.name;

  return (
    <motion.div
      variants={ANIMATIONS_ENABLED ? fadeUp : undefined}
      whileHover={ANIMATIONS_ENABLED ? { y: -4, transition: { duration: 0.18, ease: [0.22, 1, 0.36, 1] } } : undefined}
      className="will-change-transform"
    >
    <Card className="overflow-hidden group transition-shadow hover:shadow-lg hover:shadow-black/5 duration-200">
      <CardContent className="p-0">
        {/* Top */}
        <div className="px-5 pt-5 pb-3 flex items-center justify-between">
          <Badge variant={isPPV ? "default" : "outline"} className="gap-1">
            {isPPV && <Trophy className="h-3 w-3" />}
            {isPPV ? "PPV Card" : "Fight Night"}
          </Badge>
          <div className="text-xs text-muted-foreground inline-flex items-center gap-1">
            <Calendar className="h-3 w-3" /> {dateStr}
          </div>
        </div>

        {/* Event title */}
        <div className="px-5">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Main Event
          </div>
          <h3 className="text-base font-semibold mt-1 leading-tight truncate" title={cardTitle}>
            {cardTitle}
          </h3>
        </div>

        {/* Main event fighters */}
        {event.mainEvent.fighterAName && event.mainEvent.fighterBName ? (
          <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 px-5 py-5">
            <FighterStub
              name={event.mainEvent.fighterAName}
              imageUrl={event.mainEvent.fighterAImage ?? getFighterImage(event.mainEvent.fighterAName)}
              align="right"
            />
            <div className="grid place-items-center text-[10px] font-bold text-muted-foreground tracking-widest">
              VS
            </div>
            <FighterStub
              name={event.mainEvent.fighterBName}
              imageUrl={event.mainEvent.fighterBImage ?? getFighterImage(event.mainEvent.fighterBName)}
              align="left"
            />
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 px-5 py-7 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed px-3 py-1.5">
              Main event TBA
            </span>
          </div>
        )}

        {/* Footer */}
        <div className="border-t bg-muted/20 px-5 py-3 flex items-center justify-between">
          <div className="text-xs text-muted-foreground inline-flex items-center gap-1 truncate">
            <MapPin className="h-3 w-3 shrink-0" />
            <span className="truncate">{event.city || event.venue}</span>
          </div>
          <Button asChild size="sm" variant="ghost" className="h-7 -mr-2 gap-1 text-xs shrink-0">
            <Link href={`/events/${event.id}`}>
              Full card <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
    </motion.div>
  );
}

function FighterStub({
  name,
  imageUrl,
  align,
}: {
  name: string;
  imageUrl?: string;
  align: "left" | "right";
}) {
  if (!name) {
    return (
      <div className="flex items-center gap-2 min-w-0">
        <FighterPhoto src={null} alt="TBA" size={48} className="border" />
        <div className="text-xs text-muted-foreground">TBA</div>
      </div>
    );
  }
  return (
    <div
      className={cn("flex items-center gap-3 min-w-0", align === "right" ? "flex-row-reverse text-right" : "")}
    >
      <FighterPhoto src={imageUrl} alt={name} size={48} className="border" />
      <div className="text-sm font-semibold truncate min-w-0">{name}</div>
    </div>
  );
}
