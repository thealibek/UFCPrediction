"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { upcomingFights } from "@/lib/fights";
import { FightCard } from "./fight-card";

export function FightGrid() {
  return (
    <section className="flex flex-col gap-5">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Upcoming Fights</h2>
          <p className="text-xs text-muted-foreground mt-1">
            {upcomingFights.length} matchups · AI predictions updated nightly
          </p>
        </div>
        <Link
          href="/upcoming"
          className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {upcomingFights.map((f) => (
          <FightCard key={f.id} fight={f} />
        ))}
      </div>
    </section>
  );
}
