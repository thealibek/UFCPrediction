import { AdminPageShell } from "@/components/admin/admin-page-shell";
import { Badge } from "@/components/ui/badge";

export default function TrainingPage() {
  return (
    <AdminPageShell
      title="Training & Backtesting"
      description="Mass blind-test runs across historical UFC events. Resume-safe, immutable JSON logs."
    >
      <div className="space-y-3">
        <Run name="V5-2025 mass-run" status="running" progress={31} note="16/52 events · ETA ~3.5h · acc 59.3%" />
        <Run name="V5 expanded lessons (2026)" status="done" progress={100} note="15/15 events · acc 66.1% · Brier 0.216" />
        <Run name="V4 baseline (2026)" status="done" progress={100} note="14/14 events · acc 63.7% · Brier 0.224" />
        <Run name="V6 calibrated (planned)" status="queued" progress={0} note="2024+2025+2026 backlog · ETA ~6h" />
      </div>
    </AdminPageShell>
  );
}

function Run({ name, status, progress, note }: { name: string; status: "running" | "done" | "queued"; progress: number; note: string }) {
  const variant: "warning" | "success" | "outline" = status === "running" ? "warning" : status === "done" ? "success" : "outline";
  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold">{name}</span>
        <Badge variant={variant} className="capitalize">{status}</Badge>
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
      </div>
      <div className="text-xs text-muted-foreground mt-2">{note}</div>
    </div>
  );
}
