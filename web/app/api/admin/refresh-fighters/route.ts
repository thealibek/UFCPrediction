import { NextResponse } from "next/server";
import { refreshFighterDatabase, readFighterMeta } from "@/lib/admin/refresh-fighters";

// Force Node runtime (fs access) and longer timeout for first-run scenarios.
export const runtime = "nodejs";
export const maxDuration = 300;
export const dynamic = "force-dynamic";

// GET — current meta (cheap, no network)
export async function GET() {
  const meta = readFighterMeta();
  if (!meta) {
    return NextResponse.json({ error: "No metadata yet. Run refresh first." }, { status: 404 });
  }
  return NextResponse.json(meta);
}

// POST — trigger a refresh. Returns final stats.
// On a warm cache this completes in seconds; cold first-run can take minutes.
export async function POST(req: Request) {
  let opts: Record<string, unknown> = {};
  try {
    opts = await req.json();
  } catch {
    /* empty body */
  }

  try {
    const result = await refreshFighterDatabase({
      monthsBack: typeof opts.monthsBack === "number" ? opts.monthsBack : 6,
      monthsFwd: typeof opts.monthsFwd === "number" ? opts.monthsFwd : 6,
      retryMisses: !!opts.retryMisses,
    });
    return NextResponse.json(result);
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "unknown" },
      { status: 500 }
    );
  }
}
