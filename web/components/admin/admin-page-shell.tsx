import { Card, CardContent } from "@/components/ui/card";

export function AdminPageShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Admin</div>
        <h1 className="text-3xl font-semibold tracking-tight mt-1">{title}</h1>
        <p className="text-sm text-muted-foreground mt-1.5 max-w-2xl">{description}</p>
      </div>
      <Card>
        <CardContent className="p-6">{children}</CardContent>
      </Card>
    </div>
  );
}
