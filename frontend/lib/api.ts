export type Dog = { id: string; name: string; breed: string; date_of_birth: string | null; weight_kg: number | null; body_size: string; coat_color: string | null; coat_length: string; brachycephalic: boolean; activity_level: string; fitness_level: string; notes: string | null; created_at: string; updated_at: string };
export type User = { id: string; email: string };
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function request<T>(path: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const controller = new AbortController();
  const { timeoutMs = 35_000, ...fetchOptions } = options;
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API}/api/v1${path}`, { credentials: "include", headers: { "Content-Type": "application/json", ...fetchOptions.headers }, ...fetchOptions, signal: fetchOptions.signal ?? controller.signal });
    if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail ?? "Something went wrong. Please try again."); }
    return response.status === 204 ? undefined as T : response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw new Error(`The server did not respond within ${Math.round(timeoutMs / 1000)} seconds. Please try again.`);
    throw error;
  } finally { window.clearTimeout(timeout); }
}
