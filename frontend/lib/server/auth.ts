import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { AuthSession } from "@/lib/types";

export const AUTH_TOKEN_COOKIE = "enterprise_copilot_token";
export const AUTH_SESSION_COOKIE = "enterprise_copilot_session";

export function getBackendBaseUrl() {
  return process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";
}

export function buildSafeSession(payload: {
  expires_in_seconds: number;
  tenant: AuthSession["tenant"];
  user: AuthSession["user"];
}): AuthSession {
  return {
    expires_in_seconds: payload.expires_in_seconds,
    tenant: payload.tenant,
    user: payload.user,
  };
}

export function encodeSessionCookie(session: AuthSession) {
  return Buffer.from(JSON.stringify(session), "utf-8").toString("base64url");
}

export function decodeSessionCookie(value: string | undefined): AuthSession | null {
  if (!value) {
    return null;
  }

  try {
    const decoded = Buffer.from(value, "base64url").toString("utf-8");
    return JSON.parse(decoded) as AuthSession;
  } catch {
    return null;
  }
}

export function authCookieConfig(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  };
}

export async function currentSessionFromCookies() {
  const cookieStore = await cookies();
  return decodeSessionCookie(cookieStore.get(AUTH_SESSION_COOKIE)?.value);
}

export async function currentAccessTokenFromCookies() {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_TOKEN_COOKIE)?.value ?? null;
}

export async function clearAuthCookies(response: NextResponse) {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_TOKEN_COOKIE);
  cookieStore.delete(AUTH_SESSION_COOKIE);
  response.cookies.delete(AUTH_TOKEN_COOKIE);
  response.cookies.delete(AUTH_SESSION_COOKIE);
}
