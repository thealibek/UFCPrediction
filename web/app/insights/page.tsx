"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Lightbulb, Lock } from "lucide-react";
import { useUser } from "@/lib/user";
import { Button } from "@/components/ui/button";

export default function InsightsPage() {
  const { hasFullAccess } = useUser();
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Insights</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Calibration trends, division-level accuracy, and personalized model insights.
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center text-center py-16 px-6">
          <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary mb-3">
            {hasFullAccess ? <Lightbulb className="h-5 w-5" /> : <Lock className="h-5 w-5 text-muted-foreground" />}
          </div>
          <div className="text-sm font-medium">
            {hasFullAccess ? "Insights coming soon" : "Subscribe to unlock Insights"}
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-md">
            Reliability bins, ROC curves, per-division accuracy and a personalized weekly summary email.
          </p>
          {!hasFullAccess && <Button size="sm" className="mt-4">Upgrade to Pro</Button>}
        </CardContent>
      </Card>
    </div>
  );
}
