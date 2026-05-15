"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Database, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface Meta {
  lastUpdated: string;
  totalFighters: number;
  withImage: number;
  withWeight: number;
}

interface RefreshResult extends Meta {
  newlyResolvedImages: number;
  newlyEnriched: number;
  durationMs: number;
}

function timeAgo(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  const min = Math.floor(ms / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function RefreshFightersCard({
  compact = false,
}: {
  /** Compact variant for Dashboard inline use. */
  compact?: boolean;
}) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(false);

  // Initial meta fetch
  useEffect(() => {
    fetch("/api/admin/refresh-fighters")
      .then(async (r) => (r.ok ? r.json() : null))
      .then((d: Meta | null) => d && setMeta(d))
      .catch(() => {});
  }, []);

  async function handleRefresh() {
    setLoading(true);
    const toastId = toast.loading("Refreshing fighter database…", {
      description: "Pulling latest roster from ESPN",
    });
    try {
      const res = await fetch("/api/admin/refresh-fighters", { method: "POST" });
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data: RefreshResult = await res.json();
      setMeta(data);
      toast.success("Fighter database updated", {
        id: toastId,
        description: `${data.totalFighters} fighters · +${data.newlyResolvedImages} new photos · +${data.newlyEnriched} enriched · ${(data.durationMs / 1000).toFixed(1)}s`,
      });
    } catch (e) {
      toast.error("Refresh failed", {
        id: toastId,
        description: e instanceof Error ? e.message : "Unknown error",
      });
    } finally {
      setLoading(false);
    }
  }

  if (compact) {
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border bg-card px-4 py-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="grid place-items-center h-7 w-7 rounded bg-secondary shrink-0">
            <Database className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-medium truncate">
              {meta ? `${meta.totalFighters.toLocaleString()} fighters` : "Fighter database"}
            </div>
            <div className="text-[11px] text-muted-foreground truncate">
              {meta ? `Updated ${timeAgo(meta.lastUpdated)}` : "Not initialized"}
            </div>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={handleRefresh}
          disabled={loading}
          className="gap-1.5 shrink-0"
        >
          <RefreshCw className={loading ? "h-3 w-3 animate-spin" : "h-3 w-3"} />
          {loading ? "Refreshing" : "Refresh"}
        </Button>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-4 w-4" />
          Fighters Database
        </CardTitle>
        <CardDescription>
          Pulls active UFC roster from ESPN (last 6 months + next 6 months) and enriches with weight,
          country, and stats. Idempotent — only fetches new data.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Fighters" value={meta?.totalFighters.toLocaleString() ?? "—"} />
          <Stat label="With photo" value={meta?.withImage.toLocaleString() ?? "—"} />
          <Stat label="With weight" value={meta?.withWeight.toLocaleString() ?? "—"} />
          <Stat
            label="Last updated"
            value={meta ? timeAgo(meta.lastUpdated) : "Never"}
            mono={!!meta}
          />
        </div>
        <div className="flex items-center gap-3">
          <Button onClick={handleRefresh} disabled={loading} className="gap-1.5">
            <RefreshCw className={loading ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
            {loading ? "Refreshing…" : "Refresh Fighters Database"}
          </Button>
          {meta && !loading && (
            <span className="text-xs text-muted-foreground inline-flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3 text-emerald-600" />
              Source: ESPN public API
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function Stat({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border bg-muted/30 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div className={`text-base font-semibold mt-0.5 ${mono ? "tabular-nums" : ""}`}>{value}</div>
    </div>
  );
}
