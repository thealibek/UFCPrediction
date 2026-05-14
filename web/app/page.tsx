"use client";

import { useUser } from "@/lib/user";
import { DashboardHero } from "@/components/dashboard/dashboard-hero";
import { FightGrid } from "@/components/dashboard/fight-grid";
import { AdminOverview } from "@/components/admin/admin-overview";

export default function DashboardPage() {
  const { showAdminUI } = useUser();

  if (showAdminUI) {
    return (
      <div className="flex flex-col gap-10">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Admin</div>
          <h1 className="text-3xl font-semibold tracking-tight mt-1">Admin Console</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Manage lessons, monitor model performance, and run training pipelines.
          </p>
        </div>
        <AdminOverview />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-10">
      <DashboardHero />
      <FightGrid />
    </div>
  );
}
