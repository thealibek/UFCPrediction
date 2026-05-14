"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EventCard } from "./event-card";
import type { EventSummary } from "@/lib/events";

type Source = "loading" | "espn" | "fallback";

export function EventsGrid() {
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [source, setSource] = useState<Source>("loading");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/events")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        const list = (data.events ?? []) as EventSummary[];
        setEvents(list);
        setSource(data.source === "espn" && list.length > 0 ? "espn" : "fallback");
      })
      .catch(() => {
        if (!cancelled) setSource("fallback");
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
            <h2 className="text-xl font-semibold tracking-tight">Upcoming Events</h2>
            <SourceBadge source={source} />
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            {source === "espn"
              ? `${events.length} events · live from ESPN, cached 30 min`
              : source === "fallback"
              ? "Live feed unavailable"
              : "Loading live data..."}
          </p>
        </div>
        <Link
          href="/upcoming"
          className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {source === "loading" ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-[230px] rounded-lg border bg-card animate-pulse" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
          No upcoming events found
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {events.map((e) => (
            <EventCard key={e.id} event={e} />
          ))}
        </div>
      )}
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
      <WifiOff className="h-3 w-3" /> Offline
    </Badge>
  );
}
