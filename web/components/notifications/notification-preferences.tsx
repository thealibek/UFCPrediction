"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  NOTIFICATION_TYPE_LABELS,
  useNotifications,
  type NotificationType,
} from "@/lib/notifications";
import { useUser } from "@/lib/user";

export function NotificationPreferences() {
  const { prefs, togglePref } = useNotifications();
  const { isAdmin } = useUser();

  const types = (Object.keys(NOTIFICATION_TYPE_LABELS) as NotificationType[]).filter(
    (t) => t !== "admin" || isAdmin
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Уведомления</CardTitle>
        <CardDescription>
          Управляй каналами доставки. Изменения сохраняются автоматически.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-6 gap-y-1 items-center">
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium pb-2">
            Тип
          </div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium pb-2 text-center">
            In-app
          </div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium pb-2 text-center">
            Email
          </div>

          <div className="col-span-3">
            <Separator />
          </div>

          {types.map((t) => (
            <Row
              key={t}
              label={NOTIFICATION_TYPE_LABELS[t]}
              inApp={prefs.inApp[t]}
              email={prefs.email[t]}
              onToggleInApp={() => togglePref("inApp", t)}
              onToggleEmail={() => togglePref("email", t)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function Row({
  label,
  inApp,
  email,
  onToggleInApp,
  onToggleEmail,
}: {
  label: string;
  inApp: boolean;
  email: boolean;
  onToggleInApp: () => void;
  onToggleEmail: () => void;
}) {
  return (
    <>
      <div className="text-sm py-2.5">{label}</div>
      <div className="grid place-items-center py-2.5">
        <Switch checked={inApp} onCheckedChange={onToggleInApp} />
      </div>
      <div className="grid place-items-center py-2.5">
        <Switch checked={email} onCheckedChange={onToggleEmail} />
      </div>
    </>
  );
}
