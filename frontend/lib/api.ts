import { apiBaseUrl, apiEndpoint } from "./api-url";

export type Dog = { id: string; name: string; breed: string; date_of_birth: string | null; weight_kg: number | null; body_size: string; coat_color: string | null; coat_length: string; brachycephalic: boolean; activity_level: string; fitness_level: string; notes: string | null; created_at: string; updated_at: string };
export type User = { id: string; email: string };
const API = apiBaseUrl(process.env.NEXT_PUBLIC_API_URL);

export function apiErrorMessage(body: unknown, fallback = "Something went wrong. Please try again."): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => typeof item === "string" ? item : item && typeof item === "object" && typeof (item as { msg?: unknown }).msg === "string" ? (item as { msg: string }).msg : null)
      .filter((item): item is string => Boolean(item));
    if (messages.length) return messages.join(" ");
  }
  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown; msg?: unknown }).message ?? (detail as { msg?: unknown }).msg;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

export async function request<T>(path: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const controller = new AbortController();
  const { timeoutMs = 35_000, ...fetchOptions } = options;
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiEndpoint(API, path), { credentials: "include", headers: { "Content-Type": "application/json", ...fetchOptions.headers }, ...fetchOptions, signal: fetchOptions.signal ?? controller.signal });
    if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(apiErrorMessage(body)); }
    return response.status === 204 ? undefined as T : response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw new Error(`The server did not respond within ${Math.round(timeoutMs / 1000)} seconds. Please try again.`);
    throw error;
  } finally { window.clearTimeout(timeout); }
}
