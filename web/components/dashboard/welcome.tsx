"use client";

import { useUser } from "@/lib/user";
import { Card, CardContent } from "@/components/ui/card";
import { Sparkles, TrendingUp, Target } from "lucide-react";

export function Welcome() {
  const { name, role, hasFullAccess, showAdminUI } = useUser();
  const firstName = name.split(" ")[0];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">
          {showAdminUI ? "Admin Console" : `Welcome back, ${firstName}`}
        </h1>
        <p className="text-muted-foreground mt-1.5 text-sm">
          {showAdminUI
            ? "Manage lessons, monitor model performance, and run training pipelines."
            : hasFullAccess
              ? "AI-powered UFC predictions, calibrated on 351+ historical fights."
              : "Preview AI predictions for upcoming UFC fights. Subscribe to unlock full access."}
        </p>
      </div>

      {!showAdminUI && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Stat icon={<Target className="h-4 w-4" />} label="Model Accuracy" value="66.1%" hint="vs Vegas ~65-67%" />
          <Stat icon={<TrendingUp className="h-4 w-4" />} label="High-Conf Wins" value="85.4%" hint="On 41 picks ≥70%" />
          <Stat icon={<Sparkles className="h-4 w-4" />} label="Active Lessons" value="18" hint="Pruned from 20" />
        </div>
      )}
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 text-muted-foreground text-xs font-medium">
          {icon}
          {label}
        </div>
        <div className="text-2xl font-semibold mt-2 tracking-tight">{value}</div>
        <div className="text-xs text-muted-foreground mt-1">{hint}</div>
      </CardContent>
    </Card>
  );
}
