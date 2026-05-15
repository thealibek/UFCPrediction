"use client";

import * as React from "react";
import { useMemo, useState } from "react";
import Link from "next/link";
import { Search, Users, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { FighterPhoto } from "@/components/fighter-photo";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { getAllFighters, WEIGHT_CLASSES } from "@/lib/fighter-images";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 60;

export default function FightersPage() {
  const all = useMemo(() => getAllFighters(), []);
  const [query, setQuery] = useState("");
  const [weightClass, setWeightClass] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // Count fighters per weight class for chip badges
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const f of all) {
      if (f.weightClass) c[f.weightClass] = (c[f.weightClass] ?? 0) + 1;
    }
    return c;
  }, [all]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return all.filter((f) => {
      if (weightClass && f.weightClass !== weightClass) return false;
      if (q && !f.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [all, query, weightClass]);

  const visible = filtered.slice(0, (page + 1) * PAGE_SIZE);
  const hasMore = visible.length < filtered.length;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Fighters Database</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Searchable index of {all.length.toLocaleString()} active UFC fighters. Click any card for full
          stats.
        </p>
      </div>

      {/* Search bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search fighters by name..."
          value={query}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          className="pl-9 pr-9"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setPage(0);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 grid place-items-center h-6 w-6 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Weight class filter chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-thin">
        <FilterChip
          label="All"
          count={all.length}
          active={weightClass === null}
          onClick={() => {
            setWeightClass(null);
            setPage(0);
          }}
        />
        {WEIGHT_CLASSES.map((wc) => {
          const count = counts[wc] ?? 0;
          if (count === 0) return null;
          return (
            <FilterChip
              key={wc}
              label={wc}
              count={count}
              active={weightClass === wc}
              onClick={() => {
                setWeightClass(weightClass === wc ? null : wc);
                setPage(0);
              }}
            />
          );
        })}
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Showing <span className="font-medium text-foreground tabular-nums">{visible.length}</span> of{" "}
          <span className="tabular-nums">{filtered.length}</span>
          {query && ` matching "${query}"`}
          {weightClass && ` in ${weightClass}`}
        </span>
      </div>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center text-center py-16 px-6">
            <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary mb-3">
              <Users className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="text-sm font-medium">No fighters match "{query}"</div>
            <p className="text-xs text-muted-foreground mt-1">Try a different name or partial match.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {visible.map((f) => (
              <Link
                key={f.name}
                href={f.id ? `/fighters/${f.id}` : "#"}
                className="group"
                aria-disabled={!f.id}
              >
                <Card className="overflow-hidden h-full transition-all hover:shadow-md hover:-translate-y-0.5 duration-200">
                  <CardContent className="p-3 flex flex-col items-center text-center gap-2">
                    <FighterPhoto
                      src={f.imageUrl}
                      alt={f.name}
                      size={80}
                      className="border"
                    />
                    <div className="text-xs font-medium leading-tight line-clamp-2 min-h-[2lh]">
                      {f.name}
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button variant="outline" onClick={() => setPage((p) => p + 1)}>
                Load more ({filtered.length - visible.length} remaining)
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FilterChip({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "shrink-0 inline-flex items-center gap-1.5 px-3 h-8 rounded-full border text-xs font-medium transition-colors",
        active
          ? "bg-foreground text-background border-foreground"
          : "bg-background hover:bg-muted text-foreground border-border"
      )}
    >
      <span>{label}</span>
      <span
        className={cn(
          "tabular-nums text-[10px] px-1.5 py-0.5 rounded-full",
          active ? "bg-background/20 text-background" : "bg-muted text-muted-foreground"
        )}
      >
        {count}
      </span>
    </button>
  );
}
