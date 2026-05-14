import { Card, CardContent } from "@/components/ui/card";
import { Users } from "lucide-react";

export default function FightersPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Fighters Database</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Searchable index of 4,012 enriched fighter profiles (UFC + Bellator + ONE).
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center text-center py-16 px-6">
          <div className="grid place-items-center h-12 w-12 rounded-full bg-secondary mb-3">
            <Users className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="text-sm font-medium">Database explorer coming soon</div>
          <p className="text-xs text-muted-foreground mt-1 max-w-md">
            Filterable by division, country, record. Each fighter card shows SLpM, StrAcc, TDAvg, recent form.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
