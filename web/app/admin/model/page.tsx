import { AdminPageShell } from "@/components/admin/admin-page-shell";

const versions = [
  { v: "V5", model: "openai/gpt-oss-120b:free", acc: "66.1%", brier: "0.216", status: "production" },
  { v: "V4", model: "openai/gpt-oss-120b:free", acc: "63.7%", brier: "0.224", status: "archived" },
  { v: "V3", model: "groq/llama-3.3-70b", acc: "59.0%", brier: "0.241", status: "archived" },
  { v: "V2", model: "groq/llama-3.3-70b", acc: "52.0%", brier: "0.258", status: "archived" },
];

export default function ModelPage() {
  return (
    <AdminPageShell title="Model Management" description="Production model versions, accuracy, and rollback controls.">
      <table className="w-full text-sm">
        <thead className="text-xs text-muted-foreground">
          <tr className="text-left border-b">
            <th className="py-2 font-medium">Version</th>
            <th className="py-2 font-medium">Model</th>
            <th className="py-2 font-medium text-right">Accuracy</th>
            <th className="py-2 font-medium text-right">Brier</th>
            <th className="py-2 font-medium text-right">Status</th>
          </tr>
        </thead>
        <tbody>
          {versions.map((v) => (
            <tr key={v.v} className="border-b last:border-0">
              <td className="py-3 font-semibold">{v.v}</td>
              <td className="py-3 text-muted-foreground font-mono text-xs">{v.model}</td>
              <td className="py-3 text-right tabular-nums">{v.acc}</td>
              <td className="py-3 text-right tabular-nums">{v.brier}</td>
              <td className="py-3 text-right">
                <span className={v.status === "production" ? "text-emerald-600 font-medium" : "text-muted-foreground"}>
                  {v.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </AdminPageShell>
  );
}
