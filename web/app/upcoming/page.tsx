"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Calendar,
  Crown,
  Trophy,
  Sparkles,
  ChevronRight,
  Search,
  X,
  CalendarDays,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FighterPhoto } from "@/components/fighter-photo";
import type { Fight } from "@/lib/fights";
import { getFighterImage } from "@/lib/fighter-images";
import { cn } from "@/lib/utils";

interface ApiResp {
  source: string;
  count?: number;
  fights: Fight[];
  error?: string;
}

export default function UpcomingFightsPage() {
  const [data, setData] = useState<ApiResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/upcoming-fights")
      .then(async (r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json();
      })
      .then((d: ApiResp) => !cancelled && setData(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, []);

  const fights = data?.fights ?? [];

  // Filter
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return fights;
    return fights.filter(
      (f) =>
        f.fighterA.name.toLowerCase().includes(q) ||
        f.fighterB.name.toLowerCase().includes(q) ||
        f.eventName.toLowerCase().includes(q) ||
        f.weightClass.toLowerCase().includes(q)
    );
  }, [fights, query]);

  // Group by event name (preserves the API order — main event first per event)
  const grouped = useMemo(() => {
    const map = new Map<string, Fight[]>();
    for (const f of filtered) {
      if (!map.has(f.eventName)) map.set(f.eventName, []);
      map.get(f.eventName)!.push(f);
    }
    return [...map.entries()];
  }, [filtered]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
          Schedule
        </div>
        <h1 className="text-3xl font-semibold tracking-tight mt-1">Upcoming Fights</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Every announced UFC bout, grouped by event. Predictions update as the model refines.
        </p>
      </div>

      {/* Search + summary */}
      <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search fighter, event, weight class…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 pr-9"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 grid place-items-center h-6 w-6 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        <div className="text-xs text-muted-foreground tabular-nums">
          {data ? (
            <>
              <span className="font-medium text-foreground">{filtered.length}</span> /{" "}
              {fights.length} fights · <span className="font-medium text-foreground">{grouped.length}</span> events
            </>
          ) : (
            "Loading…"
          )}
        </div>
      </div>

      {/* States */}
      {error && (
        <Card>
          <CardContent className="py-12 text-center text-sm">
            <div className="font-medium">Failed to load schedule</div>
            <div className="text-muted-foreground mt-1">{error}</div>
          </CardContent>
        </Card>
      )}

      {!data && !error && <SkeletonGroups />}

      {data && fights.length === 0 && (
        <Card>
          <CardContent className="py-16 flex flex-col items-center text-center gap-2">
            <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary">
              <CalendarDays className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="text-sm font-medium">No upcoming fights</div>
            <div className="text-xs text-muted-foreground max-w-xs">
              ESPN hasn&apos;t announced new bouts yet. Check back soon — schedule typically refreshes weekly.
            </div>
          </CardContent>
        </Card>
      )}

      {data && fights.length > 0 && filtered.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No fights match &quot;{query}&quot;.
          </CardContent>
        </Card>
      )}

      {/* Grouped events */}
      {grouped.map(([eventName, list]) => (
        <EventGroup key={eventName} eventName={eventName} fights={list} />
      ))}
    </div>
  );
}

function EventGroup({ eventName, fights }: { eventName: string; fights: Fight[] }) {
  const eventDate = new Date(fights[0].date);
  const dateStr = eventDate.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  // Find a stable event id (fight id is "<eventId>-<idx>")
  const eventId = fights[0].id.split("-")[0];

  return (
    <section className="flex flex-col gap-2.5">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight truncate">{eventName}</h2>
          <div className="text-xs text-muted-foreground mt-0.5 inline-flex items-center gap-1.5">
            <Calendar className="h-3 w-3" /> {dateStr}
            <span className="text-muted-foreground/50">·</span>
            <span className="tabular-nums">{fights.length} bouts</span>
          </div>
        </div>
        <Button asChild size="sm" variant="ghost" className="gap-1 text-xs h-7">
          <Link href={`/events/${eventId}`}>
            Full card <ChevronRight className="h-3 w-3" />
          </Link>
        </Button>
      </div>

      <Card className="overflow-hidden">
        <CardContent className="p-0 divide-y">
          {fights.map((f) => (
            <FightRow key={f.id} fight={f} eventId={eventId} />
          ))}
        </CardContent>
      </Card>
    </section>
  );
}

function FightRow({ fight, eventId }: { fight: Fight; eventId: string }) {
  const boutId = fight.id.replace(`${eventId}-`, "");
  const href = `/events/${eventId}/${boutId}`;
  const winnerIsA = fight.prediction.winner === fight.fighterA.name;

  return (
    <Link
      href={href}
      className="group grid grid-cols-1 lg:grid-cols-[minmax(0,240px)_auto_minmax(0,240px)_1fr] gap-x-4 gap-y-2 items-center px-5 py-4 hover:bg-muted/30 transition-colors"
    >
      {/* Mobile tags */}
      <div className="lg:hidden flex items-center gap-1.5 flex-wrap">
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

      <FighterStub
        name={fight.fighterA.name}
        country={fight.fighterA.country}
        record={fight.fighterA.record}
      />
      <div className="hidden lg:grid place-items-center text-[10px] font-bold text-muted-foreground tracking-widest">
        VS
      </div>
      <div className="lg:hidden text-[10px] font-bold text-muted-foreground tracking-widest text-center">
        VS
      </div>
      <FighterStub
        name={fight.fighterB.name}
        country={fight.fighterB.country}
        record={fight.fighterB.record}
      />

      {/* Right: tags + prediction */}
      <div className="flex flex-col items-end gap-1.5 relative">
        <ChevronRight className="absolute -right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hidden lg:block" />
        <div className="hidden lg:flex items-center gap-1.5 flex-wrap justify-end">
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
          <Badge variant="outline" className="font-normal">
            {fight.weightClass}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Sparkles className="h-3 w-3 text-primary" />
          <span className="text-muted-foreground">Pick:</span>
          <span className="font-semibold truncate max-w-[160px]">{fight.prediction.winner}</span>
          <span
            className={cn(
              "tabular-nums font-semibold",
              fight.prediction.confidence >= 70
                ? "text-emerald-600"
                : fight.prediction.confidence >= 60
                  ? "text-foreground"
                  : "text-muted-foreground"
            )}
          >
            {fight.prediction.confidence}%
          </span>
        </div>
        <div className="text-[11px] text-muted-foreground">
          via {fight.prediction.method} · {winnerIsA ? "A" : "B"}-side
        </div>
      </div>
    </Link>
  );
}

function FighterStub({
  name,
  country,
  record,
}: {
  name: string;
  country: string;
  record: string;
}) {
  return (
    <div className="flex items-center gap-3 min-w-0">
      <FighterPhoto src={getFighterImage(name)} alt={name} size={44} className="border" />
      <div className="min-w-0">
        <div className="text-sm font-semibold truncate">{name}</div>
        <div className="text-[11px] text-muted-foreground tabular-nums">
          {country} · {record}
        </div>
      </div>
    </div>
  );
}

function SkeletonGroups() {
  return (
    <div className="flex flex-col gap-6">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex flex-col gap-2.5">
          <div className="h-5 w-64 rounded bg-muted animate-pulse" />
          <div className="rounded-lg border bg-card divide-y">
            {[0, 1, 2].map((j) => (
              <div key={j} className="h-20 bg-muted/20 animate-pulse" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

