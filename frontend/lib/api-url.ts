/** Build API paths without assuming the API base is an absolute browser URL. */
export function apiBaseUrl(value: string | undefined, fallback = "http://localhost:8000"): string {
  return (value ?? fallback).replace(/\/+$/, "");
}

export function apiEndpoint(base: string, path: string): string {
  return `${apiBaseUrl(base)}/api/v1/${path.replace(/^\/+/, "")}`;
}

/** Resolve relative Vercel proxy paths for server middleware fetches. */
export function middlewareApiEndpoint(base: string, requestUrl: string): string {
  const endpoint = apiEndpoint(base, "auth/me");
  return endpoint.startsWith("/") ? new URL(endpoint, requestUrl).toString() : endpoint;
}
