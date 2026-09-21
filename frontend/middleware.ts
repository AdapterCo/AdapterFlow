import { NextRequest, NextResponse } from "next/server";

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // 1. Webhook de notificações do Mercado Livre (aberto para o ML)
  if (
    request.method === "POST" &&
    pathname === "/api/v1/marketplaces/mercadolivre/notifications"
  ) {
    return NextResponse.next();
  }

  // 2. Rotas públicas de autenticação da aplicação
  const isAuthRoute =
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/api/v1/auth/login" ||
    pathname === "/api/v1/auth/logout";

  const sessionCookie = request.cookies.get("adapterflow_session")?.value;
  const hasSession = Boolean(sessionCookie && sessionCookie.length > 10);

  // Se já estiver autenticado e tentar acessar /login ou /register, redireciona para o dashboard
  if (hasSession && (pathname === "/login" || pathname === "/register")) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  // Se for rota pública de auth, permite acesso livre
  if (isAuthRoute) {
    return NextResponse.next();
  }

  // 3. Verificação de sessão
  // Compatibilidade com Basic auth de ferramentas legadas ou scripts de teste
  const authorization = request.headers.get("authorization");
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;

  const isBasicAuth = Boolean(
    authorization?.startsWith("Basic ") && username && password
  );

  const isAuthenticated = hasSession || isBasicAuth;

  if (!isAuthenticated) {
    // Se for chamada de API, retorna JSON 401 SEM cabeçalho WWW-Authenticate (impede o popup cinza do navegador)
    if (pathname.startsWith("/api/")) {
      return NextResponse.json(
        { detail: "Autenticação necessária." },
        { status: 401 }
      );
    }

    // Se for navegação de página no navegador, redireciona diretamente para a tela bonita de /login
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // 4. Se autenticado e for requisição para a API backend:
  // Injeta credenciais administrativas nas chamadas reescritas ao backend para que passem 100% transparentes
  if (pathname.startsWith("/api/") && username && password) {
    const requestHeaders = new Headers(request.headers);
    const basicToken = Buffer.from(`${username}:${password}`).toString("base64");
    requestHeaders.set("authorization", `Basic ${basicToken}`);
    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
