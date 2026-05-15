"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, MapPin, Ruler, Calendar, Award, Activity } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { FighterPhoto } from "@/components/fighter-photo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface FighterProfile {
  id: string;
  name: string;
  slug?: string;
  record: string;
  weight?: string;
  height?: string;
  age?: number;
  dateOfBirth?: string;
  country?: string;
  flagUrl?: string;
  imageUrl?: string;
  espnUrl?: string;
  stats: Record<string, string | number | undefined>;
}

const STAT_ORDER: Array<{ key: string; label: string; suffix?: string }> = [
  { key: "Sig Strk LPM", label: "Strikes Landed / Min" },
  { key: "Sig Strk Acc", label: "Strike Accuracy", suffix: "%" },
  { key: "Takedown Average", label: "Takedowns / 15 Min" },
  { key: "Takedown Accuracy", label: "Takedown Accuracy", suffix: "%" },
  { key: "Submission Average", label: "Submissions / 15 Min" },
  { key: "KO Percentage", label: "KO/TKO Win %", suffix: "%" },
  { key: "Decision Percentage", label: "Decision Win %", suffix: "%" },
];

export default function FighterProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<FighterProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`/api/fighters/${id}`)
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
        <div className="font-medium">Failed to load fighter</div>
        <div className="text-muted-foreground">{error}</div>
        <Button asChild variant="ghost" size="sm" className="mt-2">
          <Link href="/fighters">Back to database</Link>
        </Button>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col gap-6 max-w-4xl">
        <div className="h-6 w-40 rounded bg-muted animate-pulse" />
        <div className="h-48 rounded-lg border bg-card animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-24 rounded-lg border bg-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 max-w-4xl">
      <Link
        href="/fighters"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-fit"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back to database
      </Link>

      {/* Hero */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start">
            <FighterPhoto
              src={data.imageUrl}
              alt={data.name}
              size={128}
              className="border-2"
              priority
            />
            <div className="flex-1 min-w-0 text-center sm:text-left">
              <h1 className="text-3xl font-semibold tracking-tight">{data.name}</h1>
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mt-3">
                <Badge variant="secondary" className="gap-1.5 tabular-nums">
                  <Award className="h-3 w-3" />
                  {data.record}
                </Badge>
                {data.weight && <Badge variant="outline">{data.weight}</Badge>}
                {data.height && (
                  <Badge variant="outline" className="gap-1.5">
                    <Ruler className="h-3 w-3" />
                    {data.height}
                  </Badge>
                )}
                {data.age != null && (
                  <Badge variant="outline" className="gap-1.5">
                    <Calendar className="h-3 w-3" />
                    {data.age} yrs
                  </Badge>
                )}
                {data.country && (
                  <Badge variant="outline" className="gap-1.5">
                    <MapPin className="h-3 w-3" />
                    {data.country}
                  </Badge>
                )}
              </div>
              {data.espnUrl && (
                <Button asChild variant="ghost" size="sm" className="mt-3 gap-1.5 -ml-2">
                  <a href={data.espnUrl} target="_blank" rel="noreferrer">
                    ESPN profile <ExternalLink className="h-3 w-3" />
                  </a>
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground inline-flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5" /> Career Stats
          </h2>
          <div className="flex-1 h-px bg-border" />
        </div>

        {Object.keys(data.stats).length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No statistics available for this fighter.
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {STAT_ORDER.map(({ key, label, suffix }) => {
              const v = data.stats[key];
              if (v == null || v === "") return null;
              const display = typeof v === "number" ? v.toFixed(2) : String(v);
              return (
                <Card key={key}>
                  <CardContent className="p-4">
                    <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                      {label}
                    </div>
                    <div className="text-2xl font-semibold tabular-nums tracking-tight mt-1">
                      {display}
                      {suffix && <span className="text-base text-muted-foreground ml-0.5">{suffix}</span>}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
