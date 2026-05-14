import { AdminPageShell } from "@/components/admin/admin-page-shell";

const bins = [
  { range: "55-60%", n: 53, real: 49.1, conf: 57.8, bias: "+8.8pp", flag: "🔴" },
  { range: "60-65%", n: 112, real: 57.1, conf: 62.0, bias: "+4.9pp", flag: "✅" },
  { range: "65-70%", n: 145, real: 71.0, conf: 67.5, bias: "−3.5pp", flag: "✅" },
  { range: "70-75%", n: 33, real: 87.9, conf: 72.1, bias: "−15.8pp", flag: "🟢" },
  { range: "75-80%", n: 8, real: 75.0, conf: 78.0, bias: "+3.0pp", flag: "✅" },
];

export default function AnalyticsPage() {
  return (
    <AdminPageShell title="Analytics & Performance" description="Reliability diagram of 351 graded predictions across V4 + V5.">
      <div className="space-y-2">
        <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 text-xs uppercase tracking-wider text-muted-foreground font-medium pb-2 border-b">
          <span>Confidence</span>
          <span className="text-right">N</span>
          <span className="text-right">Real Acc</span>
          <span className="text-right">Avg Conf</span>
          <span className="text-right">Bias</span>
          <span></span>
        </div>
        {bins.map((b) => (
          <div key={b.range} className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 items-center py-2 text-sm">
            <span className="font-mono">{b.range}</span>
            <span className="text-right tabular-nums text-muted-foreground">{b.n}</span>
            <span className="text-right tabular-nums font-medium">{b.real}%</span>
            <span className="text-right tabular-nums text-muted-foreground">{b.conf}%</span>
            <span className="text-right tabular-nums">{b.bias}</span>
            <span>{b.flag}</span>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground mt-6">
        Insight: модель <strong>underconfident</strong> в bin 70-75% (real 88% vs avg 72%) — это огромный edge для betting.
        В bin 55-60% — overconfident (49% vs 58%) — V6 prompt сжимает этот диапазон в no-bet zone.
      </p>
    </AdminPageShell>
  );
}
