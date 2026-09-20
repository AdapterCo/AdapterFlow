import { NextRequest, NextResponse } from "next/server";

async function equal(a: string, b: string) {
  const hash = async (value: string) => new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
  const [left, right] = await Promise.all([hash(a), hash(b)]);
  return left.reduce((diff, value, index) => diff | (value ^ right[index]), 0) === 0;
}

export async function middleware(request: NextRequest) {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  if (!username || !password) return new NextResponse("Acesso administrativo não configurado no servidor.", { status: 503 });
  let valid = false;
  const authorization = request.headers.get("authorization");
  if (authorization?.startsWith("Basic ")) {
    try {
      const decoded = atob(authorization.slice(6));
      const separator = decoded.indexOf(":");
      const userMatches = await equal(decoded.slice(0, separator), username);
      const passwordMatches = await equal(decoded.slice(separator + 1), password);
      valid = separator >= 0 && userMatches && passwordMatches;
    } catch { valid = false; }
  }
  if (!valid) return new NextResponse("Autenticação necessária.", { status: 401, headers: { "WWW-Authenticate": 'Basic realm="AdapterFlow", charset="UTF-8"' } });
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const origin = request.headers.get("origin");
    const allowed = process.env.APP_ORIGIN || request.nextUrl.origin;
    if (origin && origin !== allowed) return new NextResponse("Origem não autorizada.", { status: 403 });
  }
  return NextResponse.next();
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
