import { NextResponse } from "next/server";
import { clearAuthCookies } from "@/lib/server/auth";

export async function POST() {
  const response = NextResponse.json(
    { ok: true },
    { headers: { "Cache-Control": "no-store" } },
  );
  await clearAuthCookies(response);
  return response;
}
