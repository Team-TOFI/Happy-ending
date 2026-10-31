import { NextRequest, NextResponse } from "next/server";
export async function POST(request: NextRequest) {
  if (request.headers.get("origin") !== request.nextUrl.origin)
    return NextResponse.json({ error: "origin" }, { status: 403 });
  const response = new NextResponse(null, { status: 204 });
  for (const cookie of request.cookies.getAll())
    if (cookie.name.startsWith("sb-"))
      response.cookies.set(cookie.name, "", { path: "/", maxAge: 0 });
  response.headers.set("Cache-Control", "no-store");
  return response;
}
