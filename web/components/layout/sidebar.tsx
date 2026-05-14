"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Swords,
  History,
  Settings,
  BookOpen,
  Brain,
  FlaskConical,
  BarChart3,
  Sparkles,
  Users,
  Lightbulb,
  ShieldCheck,
  Boxes,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUser } from "@/lib/user";
import { Badge } from "@/components/ui/badge";

type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  paidOnly?: boolean;
};

const userNav: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upcoming", label: "Upcoming Fights", icon: Swords },
  { href: "/fighters", label: "Fighters Database", icon: Users },
  { href: "/history", label: "My History", icon: History, paidOnly: true },
  { href: "/insights", label: "Insights", icon: Lightbulb, paidOnly: true },
  { href: "/settings", label: "Settings", icon: Settings },
];

const adminNav: NavItem[] = [
  { href: "/admin", label: "Admin Dashboard", icon: ShieldCheck },
  { href: "/admin/training", label: "Model Training", icon: FlaskConical },
  { href: "/admin/backtesting", label: "Backtesting", icon: BarChart3 },
  { href: "/admin/analytics", label: "Analytics", icon: Brain },
  { href: "/admin/lessons", label: "Content Management", icon: BookOpen },
  { href: "/admin/model", label: "Model Versions", icon: Boxes },
];

export function Sidebar() {
  const pathname = usePathname();
  const { isAdmin, hasFullAccess } = useUser();

  return (
    <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r bg-card/30 px-4 py-6">
      <Link href="/" className="flex items-center gap-2 px-2 mb-8">
        <div className="grid place-items-center h-8 w-8 rounded-lg bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight">Octagon AI</div>
          <div className="text-[10px] text-muted-foreground -mt-0.5">UFC Prediction Engine</div>
        </div>
      </Link>

      <nav className="flex flex-col gap-0.5">
        <NavSection items={userNav} pathname={pathname} hasFullAccess={hasFullAccess} />

        {isAdmin && (
          <>
            <div className="my-4 px-3">
              <div className="border-t" />
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mt-3 mb-1.5">
                Admin
              </div>
            </div>
            <NavSection items={adminNav} pathname={pathname} hasFullAccess={hasFullAccess} />
          </>
        )}
      </nav>

      <div className="mt-auto px-2 pt-6">
        <div className="text-[11px] text-muted-foreground leading-relaxed">
          <span className="font-medium text-foreground">v6.0</span> · 66.1% accuracy<br />
          on 351 graded fights
        </div>
      </div>
    </aside>
  );
}

function NavSection({
  items,
  pathname,
  hasFullAccess,
}: {
  items: NavItem[];
  pathname: string;
  hasFullAccess: boolean;
}) {
  return (
    <>
      {items.map((item) => {
        const Icon = item.icon;
        const active = pathname === item.href;
        const locked = item.paidOnly && !hasFullAccess;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-secondary text-secondary-foreground"
                : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="flex-1 truncate">{item.label}</span>
            {locked && <Lock className="h-3 w-3 opacity-60" />}
          </Link>
        );
      })}
    </>
  );
}
