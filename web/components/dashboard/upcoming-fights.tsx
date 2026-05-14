"use client";

import { useState } from "react";
import { upcomingFights } from "@/lib/fights";
import { useUser } from "@/lib/user";
import { PredictionCard } from "./prediction-card";
import { UpgradeModal } from "@/components/upgrade-modal";

export function UpcomingFights() {
  const { hasFullAccess } = useUser();
  const [open, setOpen] = useState(false);

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Upcoming Fights</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            {upcomingFights.length} matchups · AI predictions updated nightly
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {upcomingFights.map((f) => (
          <PredictionCard key={f.id} fight={f} unlocked={hasFullAccess} onUpgrade={() => setOpen(true)} />
        ))}
      </div>

      <UpgradeModal open={open} onOpenChange={setOpen} />
    </section>
  );
}
