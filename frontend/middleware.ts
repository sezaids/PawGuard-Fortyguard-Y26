import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PUBLIC_PATHS = new Set(["/login", "/signup"]);

/**
 * Keep protected pages from initially rendering an indefinite client-side
 * session check. The API remains the source of truth for the session.
 */
export async function middleware(request: NextRequest) {
  if (PUBLIC_PATHS.has(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const session = request.cookies.get("pawguard_session");
  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const response = await fetch(`${API_URL}/api/v1/auth/me`, {
      headers: { cookie: `pawguard_session=${session.value}` },
      cache: "no-store",
      signal: AbortSignal.timeout(5_000),
    });

    if (response.ok) {
      return NextResponse.next();
    }
  } catch {
    // Treat an unreachable auth service as an unavailable session rather than
    // serving a page that waits forever.
  }

  const response = NextResponse.redirect(new URL("/login?session=unavailable", request.url));
  response.cookies.delete("pawguard_session");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
