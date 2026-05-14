"use client";

import { Sparkles, Target, TrendingUp, Trophy, Database } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useUser } from "@/lib/user";

export function DashboardHero() {
  const { name, hasFullAccess } = useUser();
  const firstName = name.split(" ")[0];

  return (
    <div className="flex flex-col gap-6">
      {/* Hero card */}
      <div className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-primary via-primary to-zinc-700 text-primary-foreground p-8 md:p-10">
        <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
        <div className="absolute -right-10 -bottom-20 h-48 w-48 rounded-full bg-white/5 blur-3xl" />

        <div className="relative flex flex-col md:flex-row md:items-end md:justify-between gap-6">
          <div>
            <Badge variant="secondary" className="bg-white/10 text-white border-white/20 hover:bg-white/15 gap-1">
              <Sparkles className="h-3 w-3" /> v6.0 calibrated
            </Badge>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight mt-4">
              Welcome back, {firstName}
            </h1>
            <p className="text-sm md:text-base text-white/70 mt-2 max-w-lg">
              {hasFullAccess
                ? "Your AI predictor is calibrated on 351 historical fights. Outperforming Vegas closing odds on high-confidence picks."
                : "Subscribe to unlock full predictions, betting recommendations and history."}
            </p>
          </div>
          <div className="flex items-end gap-2">
            <div className="text-5xl md:text-6xl font-semibold tabular-nums tracking-tight leading-none">
              66.1<span className="text-3xl text-white/60">%</span>
            </div>
            <div className="pb-1.5">
              <div className="text-xs text-white/60 uppercase tracking-wider">Model accuracy</div>
              <div className="text-xs text-emerald-300 font-medium mt-0.5">+3.2pp vs V4</div>
            </div>
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat icon={<Target className="h-4 w-4" />} label="Moneyline accuracy" value="66.1%" hint="N=351" tone="text-emerald-600" />
        <Stat icon={<TrendingUp className="h-4 w-4" />} label="High-conf wins (≥70%)" value="85.4%" hint="41 picks · +20pp edge" tone="text-emerald-600" />
        <Stat icon={<Trophy className="h-4 w-4" />} label="Best event" value="UFC 324" hint="9/11 · 81.8%" />
        <Stat icon={<Database className="h-4 w-4" />} label="Fighters in DB" value="4,012" hint="UFC + Bellator + ONE" />
      </div>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint: string;
  tone?: string;
}) {
  return (
    <Card className="transition-all hover:shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-muted-foreground text-xs font-medium">
          {icon}
          {label}
        </div>
        <div className={`text-2xl font-semibold mt-2 tracking-tight tabular-nums ${tone ?? ""}`}>{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{hint}</div>
      </CardContent>
    </Card>
  );
}
