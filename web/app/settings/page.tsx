"use client";

import { useUser } from "@/lib/user";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Crown, ShieldCheck } from "lucide-react";
import { NotificationPreferences } from "@/components/notifications/notification-preferences";
import { NotificationDemoTriggers } from "@/components/notifications/notification-demo-triggers";

export default function SettingsPage() {
  const { name, email, role, isSubscribed, hasFullAccess, setRole, setSubscribed } = useUser();

  const planName = role === "admin" ? "Admin" : role === "paid" ? "Pro" : "Free";

  return (
    <div className="flex flex-col gap-8 max-w-3xl">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1.5">Manage your account, subscription and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Personal information shown across the platform.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field label="Name" value={name} />
          <Field label="Email" value={email} />
          <Field label="Role" value={<Badge variant="outline" className="capitalize">{role}</Badge>} />
          <Field
            label="Status"
            value={
              <Badge variant={hasFullAccess ? "success" : "warning"}>
                {hasFullAccess ? "Active" : "Limited"}
              </Badge>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Subscription</CardTitle>
          <CardDescription>Your current plan and billing.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="grid place-items-center h-10 w-10 rounded-lg bg-secondary">
              {role === "paid" || role === "admin" ? (
                <Crown className="h-4 w-4" />
              ) : (
                <ShieldCheck className="h-4 w-4" />
              )}
            </div>
            <div className="flex-1">
              <div className="text-sm font-semibold">Octagon {planName}</div>
              <div className="text-xs text-muted-foreground">
                {role === "paid"
                  ? "Renews on Jul 14, 2026 · $19/month"
                  : role === "admin"
                    ? "Internal account · no billing"
                    : "Free tier · upgrade for full access"}
              </div>
            </div>
            {role !== "admin" && (
              <Button
                size="sm"
                variant={isSubscribed ? "outline" : "default"}
                onClick={() => {
                  if (isSubscribed) {
                    setSubscribed(false);
                    setRole("free");
                  } else {
                    setSubscribed(true);
                    setRole("paid");
                  }
                }}
              >
                {isSubscribed ? "Cancel" : "Upgrade"}
              </Button>
            )}
          </div>

          <Separator className="my-4" />

          <div className="text-xs text-muted-foreground">
            Demo mode: this toggle simulates a Stripe webhook. In production, billing is managed via Stripe Customer Portal.
          </div>
        </CardContent>
      </Card>

      <NotificationPreferences />
      <NotificationDemoTriggers />
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium mt-0.5">{value}</div>
    </div>
  );
}
