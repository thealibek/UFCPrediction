"use client";

import { Card, CardContent } from "@/components/ui/card";
import { History, Lock } from "lucide-react";
import { useUser } from "@/lib/user";
import { Button } from "@/components/ui/button";

export default function HistoryPage() {
  const { hasFullAccess } = useUser();
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">My History</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Past predictions you&apos;ve viewed and bets you&apos;ve tracked.
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center text-center py-16 px-6">
          <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary mb-3">
            {hasFullAccess ? <History className="h-5 w-5" /> : <Lock className="h-5 w-5 text-muted-foreground" />}
          </div>
          <div className="text-sm font-medium">
            {hasFullAccess ? "No history yet" : "Subscribe to unlock History"}
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-md">
            {hasFullAccess
              ? "Predictions you view and bets you track will appear here with ROI calculations."
              : "Track your bet ROI over time and compare your picks against the AI."}
          </p>
          {!hasFullAccess && <Button size="sm" className="mt-4">Upgrade to Pro</Button>}
        </CardContent>
      </Card>
    </div>
  );
}
