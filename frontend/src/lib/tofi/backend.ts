export function getBackendUrl(
  value = process.env.NEXT_PUBLIC_API_BASE_URL,
): string {
  return (
    value?.trim() ||
    (process.env.NODE_ENV === "production"
      ? "https://api.gomin.today"
      : "http://127.0.0.1:8000")
  ).replace(/\/+$/, "");
}
