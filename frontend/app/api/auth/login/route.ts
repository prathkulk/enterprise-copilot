import { NextResponse } from "next/server";
import {
  AUTH_SESSION_COOKIE,
  AUTH_TOKEN_COOKIE,
  authCookieConfig,
  buildSafeSession,
  encodeSessionCookie,
  getBackendBaseUrl,
} from "@/lib/server/auth";

export async function POST(request: Request) {
  const response = await fetch(`${getBackendBaseUrl()}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: await request.text(),
    cache: "no-store",
  });

  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const session = buildSafeSession(payload);
  const nextResponse = NextResponse.json(session, {
    status: response.status,
    headers: { "Cache-Control": "no-store" },
  });

  nextResponse.cookies.set(
    AUTH_TOKEN_COOKIE,
    payload.access_token,
    authCookieConfig(payload.expires_in_seconds),
  );
  nextResponse.cookies.set(
    AUTH_SESSION_COOKIE,
    encodeSessionCookie(session),
    authCookieConfig(payload.expires_in_seconds),
  );

  return nextResponse;
}
