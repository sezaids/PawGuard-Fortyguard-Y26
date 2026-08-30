"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { request, User } from "../lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter(); const [state, setState] = useState<"checking" | "authenticated" | "failed">("checking");
  useEffect(() => {
    let active = true;
    const redirectToLogin = () => {
      if (!active) return;
      setState("failed");
      router.replace("/login?session=unavailable");
    };
    const fallback = window.setTimeout(redirectToLogin, 16_000);
    request<User>("/auth/me").then(() => { if (active) setState("authenticated"); }).catch(redirectToLogin).finally(() => window.clearTimeout(fallback));
    return () => { active = false; window.clearTimeout(fallback); };
  }, [router]);
  if (state === "checking") return <main className="grid min-h-screen place-items-center bg-sand text-ink/60">Checking your PawGuard session…</main>;
  if (state === "failed") return <main className="grid min-h-screen place-items-center bg-sand px-5 text-center"><div><p className="text-lg font-semibold text-ink">Your session is unavailable.</p><p className="mt-2 text-sm text-ink/60">Redirecting you to sign in…</p><Link href="/login" className="mt-5 inline-block rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white">Go to sign in</Link></div></main>;
  return <>{children}</>;
}
