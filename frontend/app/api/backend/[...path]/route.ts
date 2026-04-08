import { NextResponse } from "next/server";
import { currentAccessTokenFromCookies, getBackendBaseUrl } from "@/lib/server/auth";

async function proxy(request: Request, path: string[]) {
  const token = await currentAccessTokenFromCookies();
  if (!token) {
    return NextResponse.json(
      { detail: "Authentication is required." },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const backendUrl = new URL(`${getBackendBaseUrl()}/${path.join("/")}`);
  const incomingUrl = new URL(request.url);
  backendUrl.search = incomingUrl.search;

  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    const lower = key.toLowerCase();
    if (
      lower === "host" ||
      lower === "cookie" ||
      lower === "authorization" ||
      lower === "content-length" ||
      lower === "connection"
    ) {
      continue;
    }
    headers.set(key, value);
  }
  headers.set("Authorization", `Bearer ${token}`);
  headers.set("Cache-Control", "no-store");

  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : Buffer.from(await request.arrayBuffer());

  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  const proxiedHeaders = new Headers();
  const contentType = response.headers.get("content-type");
  const requestId = response.headers.get("x-request-id");
  if (contentType) {
    proxiedHeaders.set("Content-Type", contentType);
  }
  if (requestId) {
    proxiedHeaders.set("X-Request-ID", requestId);
  }
  proxiedHeaders.set("Cache-Control", "no-store");

  return new NextResponse(response.body, {
    status: response.status,
    headers: proxiedHeaders,
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxy(request, path);
}
