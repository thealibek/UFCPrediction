import Link from "next/link";
import { Activity, BookOpen, Brain, LineChart, ChevronRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { RefreshFightersCard } from "@/components/admin/refresh-fighters-card";

const SECTIONS = [
  { href: "/admin/training", title: "Training & Backtesting", desc: "Mass blind-test runs", icon: Brain },
  { href: "/admin/model", title: "Model Versions", desc: "Active prediction model", icon: Activity },
  { href: "/admin/analytics", title: "Analytics", desc: "Accuracy and calibration", icon: LineChart },
  { href: "/admin/lessons", title: "Lessons", desc: "Heuristic library", icon: BookOpen },
];

export default function AdminDashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Admin</div>
        <h1 className="text-3xl font-semibold tracking-tight mt-1">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">
          Internal tools — model training, data sources, analytics.
        </p>
      </div>

      <RefreshFightersCard />

      <section className="flex flex-col gap-3">
        <h2 className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
          Sections
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {SECTIONS.map(({ href, title, desc, icon: Icon }) => (
            <Link key={href} href={href} className="group">
              <Card className="transition-all hover:shadow-md hover:-translate-y-0.5 duration-200">
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="grid place-items-center h-10 w-10 rounded-lg bg-secondary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold">{title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
