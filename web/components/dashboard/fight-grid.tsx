"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { upcomingFights as fallbackFights, type Fight } from "@/lib/fights";
import { FightCard } from "./fight-card";
import { Badge } from "@/components/ui/badge";
import { StaggerContainer, StaggerItem } from "@/components/motion";

type Source = "loading" | "espn" | "fallback";

export function FightGrid() {
  const [fights, setFights] = useState<Fight[]>(fallbackFights);
  const [source, setSource] = useState<Source>("loading");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/upcoming-fights")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        if (data.source === "espn" && Array.isArray(data.fights) && data.fights.length > 0) {
          setFights(data.fights);
          setSource("espn");
        } else {
          setFights(fallbackFights);
          setSource("fallback");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setFights(fallbackFights);
          setSource("fallback");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="flex flex-col gap-5">
      <div className="flex items-end justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-semibold tracking-tight">Upcoming Fights</h2>
            <SourceBadge source={source} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {fights.length} matchups ·{" "}
            {source === "espn"
              ? "live data from ESPN, refreshed every 30 min"
              : source === "fallback"
              ? "showing cached data — live feed unavailable"
              : "loading live data..."}
          </p>
        </div>
        <Link
          href="/upcoming"
          className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      <StaggerContainer className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {fights.map((f) => (
          <StaggerItem key={f.id}>
            <FightCard fight={f} />
          </StaggerItem>
        ))}
      </StaggerContainer>
    </section>
  );
}

function SourceBadge({ source }: { source: Source }) {
  if (source === "loading") {
    return (
      <Badge variant="outline" className="gap-1 text-[10px] uppercase tracking-wider">
        <RefreshCw className="h-3 w-3 animate-spin" /> Loading
      </Badge>
    );
  }
  if (source === "espn") {
    return (
      <Badge variant="success" className="gap-1 text-[10px] uppercase tracking-wider">
        <Wifi className="h-3 w-3" /> Live
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1 text-[10px] uppercase tracking-wider">
      <WifiOff className="h-3 w-3" /> Cached
    </Badge>
  );
}
