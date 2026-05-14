import { AdminPageShell } from "@/components/admin/admin-page-shell";
import { Badge } from "@/components/ui/badge";

const lessons = [
  { id: 1, title: "Антропометрия + KO power > раздутый рекорд", active: true, fired: 14, delta: "+1.3pp" },
  { id: 2, title: "Home-country judge bias (AUS/UK/BR)", active: true, fired: 11, delta: "+5.1pp" },
  { id: 18, title: "Голодный challenger vs decline-чемпион", active: false, fired: 11, delta: "−3.3pp" },
  { id: 19, title: "Striker с реальной KO-силой бьёт TD-favourite-а", active: false, fired: 5, delta: "−8.2pp" },
];

export default function LessonsPage() {
  return (
    <AdminPageShell
      title="Lessons"
      description="Active lessons injected into LLM prompt at runtime. Ablation analysis identifies harmful lessons automatically."
    >
      <div className="space-y-2">
        {lessons.map((l) => (
          <div key={l.id} className="flex items-center justify-between py-2 border-b last:border-0">
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-8">#{l.id}</span>
              <span className="text-sm">{l.title}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground tabular-nums">fired {l.fired}×</span>
              <Badge variant={l.delta.startsWith("+") ? "success" : "destructive"}>{l.delta}</Badge>
              <Badge variant={l.active ? "default" : "outline"}>{l.active ? "Active" : "Disabled"}</Badge>
            </div>
          </div>
        ))}
      </div>
    </AdminPageShell>
  );
}
