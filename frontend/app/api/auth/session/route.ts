import { NextResponse } from "next/server";
import { currentSessionFromCookies } from "@/lib/server/auth";

export async function GET() {
  const session = await currentSessionFromCookies();
  return NextResponse.json(session, {
    headers: { "Cache-Control": "no-store" },
  });
}
