import { frontendConfig } from "@/lib/config";

type QueryPrimitive = string | number | boolean | null | undefined;
type QueryValue = QueryPrimitive | QueryPrimitive[];

export function buildApiUrl(
  path: string,
  query: Record<string, QueryValue> = {},
): string {
  const baseUrl = frontendConfig.apiBaseUrl.endsWith("/")
    ? frontendConfig.apiBaseUrl
    : `${frontendConfig.apiBaseUrl}/`;
  const url = new URL(path.replace(/^\//, ""), baseUrl);

  for (const [key, value] of Object.entries(query)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item === null || item === undefined || item === "") {
          continue;
        }
        url.searchParams.append(key, String(item));
      }
      continue;
    }

    if (value === null || value === undefined || value === "") {
      continue;
    }
    url.searchParams.set(key, String(value));
  }

  return url.toString();
}

export function buildWebSocketUrl(
  path: string,
  query: Record<string, QueryValue> = {},
): string {
  const url = new URL(buildApiUrl(path, query));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
