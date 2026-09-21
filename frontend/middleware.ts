import { NextRequest, NextResponse } from "next/server";

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (request.method === "POST" && path === "/api/v1/marketplaces/mercadolivre/notifications") return NextResponse.next();
  if (["/login", "/register", "/api/v1/auth/login", "/api/v1/auth/logout"].includes(path)) return NextResponse.next();
  const origin = request.headers.get("origin");
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method) && origin && origin !== (process.env.APP_ORIGIN || request.nextUrl.origin)) {
    return NextResponse.json({ detail: "Origem não autorizada." }, { status: 403 });
  }
  const cookie = request.headers.get("cookie");
  const authorization = request.headers.get("authorization");
  if (cookie || authorization) {
    // Forward caller credentials only. Never inject the administrative password.
    const headers = new Headers();
    if (cookie) headers.set("cookie", cookie);
    if (authorization) headers.set("authorization", authorization);
    try {
      const backend = process.env.INTERNAL_BACKEND_URL || "http://localhost:8000";
      const result = await fetch(`${backend}/api/v1/auth/me`, { headers, cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(10000) });
      if (result.ok) return NextResponse.next();
      if (result.status >= 500) return NextResponse.json({ detail: "Serviço de autenticação indisponível." }, { status: 503 });
    } catch {
      return NextResponse.json({ detail: "Serviço de autenticação indisponível." }, { status: 503 });
    }
  }
  if (path.startsWith("/api/")) return NextResponse.json({ detail: "Autenticação necessária." }, { status: 401 });
  const response = NextResponse.redirect(new URL("/login", request.url));
  response.cookies.delete("adapterflow_session");
  return response;
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
