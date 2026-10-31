import { NextResponse, type NextRequest } from "next/server";
import { getServerSupabase } from "@/lib/supabase/server";
import { safeReturnPath } from "@/lib/supabase/redirect";
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const supabase = await getServerSupabase();
  if (code && supabase) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      const { data, error: identityError } = await supabase.auth.getUser();
      if (!identityError && data.user) {
        const response = NextResponse.redirect(
          new URL(
            safeReturnPath(request.nextUrl.searchParams.get("next")),
            request.url,
          ),
        );
        response.headers.set("Cache-Control", "no-store");
        return response;
      }
    }
  }
  const response = NextResponse.redirect(
    new URL("/login?error=google", request.url),
  );
  response.headers.set("Cache-Control", "no-store");
  return response;
}
