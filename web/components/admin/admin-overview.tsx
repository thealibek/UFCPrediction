"use client";

import Link from "next/link";
import { ArrowRight, BookOpen, Brain, FlaskConical, BarChart3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const sections = [
  {
    href: "/admin/lessons",
    icon: BookOpen,
    title: "Lessons",
    desc: "18 active · 2 deactivated. Manage prompt lessons and ablation analysis.",
    stat: "18",
    statLabel: "active",
  },
  {
    href: "/admin/model",
    icon: Brain,
    title: "Model Management",
    desc: "Current: V5 GPT-OSS-120B + 18 lessons. Deploy, rollback, A/B test.",
    stat: "V5",
    statLabel: "production",
  },
  {
    href: "/admin/training",
    icon: FlaskConical,
    title: "Training & Backtesting",
    desc: "V5-2025 mass-run in progress (16/52 events). Brier 0.237, ETA ~3.5h.",
    stat: "31%",
    statLabel: "running",
  },
  {
    href: "/admin/analytics",
    icon: BarChart3,
    title: "Analytics & Performance",
    desc: "351 graded predictions. Reliability bins, ROC-AUC, per-division breakdown.",
    stat: "66.1%",
    statLabel: "accuracy",
  },
];

export function AdminOverview() {
  return (
    <section className="grid gap-4 md:grid-cols-2">
      {sections.map((s) => {
        const Icon = s.icon;
        return (
          <Link key={s.href} href={s.href} className="group">
            <Card className="h-full transition-all group-hover:shadow-md group-hover:border-foreground/20">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="grid place-items-center h-10 w-10 rounded-lg bg-secondary">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-base font-semibold">{s.title}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{s.statLabel}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-semibold tabular-nums">{s.stat}</div>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground mt-4">{s.desc}</p>
                <div className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-foreground/70 group-hover:text-foreground">
                  Open <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                </div>
              </CardContent>
            </Card>
          </Link>
        );
      })}
    </section>
  );
}
