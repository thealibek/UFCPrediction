"use client";

import { Check, X, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FighterPhoto } from "@/components/fighter-photo";
import { pastFights } from "@/lib/fights";
import { getFighterImage } from "@/lib/fighter-images";
import { cn } from "@/lib/utils";

export function PastFights() {
  const correct = pastFights.filter((f) => f.predictedWinner === f.actualWinner).length;
  const accuracy = Math.round((correct / pastFights.length) * 100);

  return (
    <section className="flex flex-col gap-5">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Recent Results</h2>
          <p className="text-xs text-muted-foreground mt-1">
            Last {pastFights.length} graded fights · {correct}/{pastFights.length} correct ({accuracy}%)
          </p>
        </div>
        <Link
          href="/upcoming"
          className="text-xs font-medium text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="divide-y">
            {pastFights.map((f) => {
              const isCorrect = f.predictedWinner === f.actualWinner;
              const date = new Date(f.date).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
              });
              return (
                <div
                  key={f.id}
                  className="grid grid-cols-[auto_auto_1fr_auto_auto] gap-3 items-center px-5 py-4 hover:bg-muted/30 transition-colors"
                >
                  {/* Status icon */}
                  <div
                    className={cn(
                      "grid place-items-center h-8 w-8 rounded-full shrink-0",
                      isCorrect
                        ? "bg-emerald-500/10 text-emerald-600"
                        : "bg-red-500/10 text-red-600"
                    )}
                  >
                    {isCorrect ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                  </div>

                  {/* Fighter avatars */}
                  <div className="flex -space-x-2 shrink-0">
                    <FighterPhoto
                      src={getFighterImage(f.fighterA.name)}
                      alt={f.fighterA.name}
                      size={36}
                      className="border-2 border-background"
                    />
                    <FighterPhoto
                      src={getFighterImage(f.fighterB.name)}
                      alt={f.fighterB.name}
                      size={36}
                      className="border-2 border-background"
                    />
                  </div>

                  {/* Fighters + meta */}
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">
                      {f.fighterA.name} <span className="text-muted-foreground font-normal">vs</span>{" "}
                      {f.fighterB.name}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-2 flex-wrap">
                      <span>{f.eventName}</span>
                      <span className="opacity-50">·</span>
                      <span>{date}</span>
                      <span className="opacity-50">·</span>
                      <span>{f.weightClass}</span>
                    </div>
                  </div>

                  {/* Prediction vs Actual */}
                  <div className="hidden sm:flex flex-col items-end gap-0.5 text-xs tabular-nums">
                    <div className="text-muted-foreground">
                      Predicted: <span className="text-foreground font-medium">{f.predictedWinner}</span>{" "}
                      <span className="opacity-60">@ {f.predictedConfidence}%</span>
                    </div>
                    <div className="text-muted-foreground">
                      Actual:{" "}
                      <span className="text-foreground font-medium">{f.actualWinner}</span>{" "}
                      <span className="opacity-60">
                        · {f.actualMethod}
                        {f.actualRound ? ` R${f.actualRound}` : ""}
                      </span>
                    </div>
                  </div>

                  {/* Result badge */}
                  <Badge
                    variant={isCorrect ? "success" : "destructive"}
                    className="shrink-0 tabular-nums"
                  >
                    {isCorrect ? "Hit" : "Miss"}
                  </Badge>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
