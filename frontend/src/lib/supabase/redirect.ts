export function safeReturnPath(value: string | null): string {
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\")
  )
    return "/wardrobe";
  const parsed = new URL(value, "https://tofi.invalid");
  if (
    parsed.origin !== "https://tofi.invalid" ||
    parsed.pathname.startsWith("/login") ||
    parsed.pathname.startsWith("/auth/")
  )
    return "/wardrobe";
  return parsed.pathname + parsed.search + parsed.hash;
}
