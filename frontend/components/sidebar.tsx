"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { request } from "../lib/api";
import { Icon } from "./icons";
import { SafetyAssistant } from "./safety-assistant";

const navigation = ["Dashboard", "My Dogs", "Active Walk", "Walk Planner", "Route Planner", "Daily Schedule", "Walk Match", "Heat Map", "Safety", "History", "Settings"];

export function Sidebar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname(); const router = useRouter();
  const links: Record<string, string> = { Dashboard: "/", "My Dogs": "/dogs", "Active Walk": "/active-walk", "Walk Planner": "/walk-planner", "Route Planner": "/route-planner", "Daily Schedule": "/walk-scheduler", "Walk Match": "/walk-match", "Heat Map": "/heat-map", Safety: "/safety", History: "/history", Settings: "/settings" };
  async function logout() { await request("/auth/logout", { method: "POST" }); router.push("/login"); }

  return <>
    <button onClick={() => setOpen(true)} className="fixed left-4 top-4 z-30 rounded-xl bg-ink p-3 text-white shadow-card md:hidden" aria-label="Open navigation">☰</button>
    {open && <button aria-label="Close navigation" onClick={() => setOpen(false)} className="fixed inset-0 z-20 bg-ink/30 md:hidden" />}
    <aside className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col bg-ink px-5 py-7 text-white transition-transform md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="mb-12 flex items-center gap-3 px-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-mint text-2xl">🐾</div>
        <div><p className="text-xl font-bold tracking-tight">PawGuard</p><p className="text-xs text-mint/70">Walk smart. Stay cool.</p></div>
      </div>
      <nav className="space-y-1" aria-label="Main navigation">
        {navigation.map((item) => <Link key={item} href={links[item]} onClick={() => setOpen(false)} className={`flex items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-medium transition ${pathname === links[item] ? "bg-white text-ink shadow-lg" : "text-white/70 hover:bg-white/10 hover:text-white"}`}><Icon name={item} />{item}</Link>)}
      </nav>
      <div className="mt-auto rounded-2xl bg-white/10 p-4 text-sm text-white/75"><p className="font-semibold text-white">Built for better days</p><p className="mt-1 text-xs leading-5">Your dog&apos;s comfort is always the priority.</p><button onClick={logout} className="mt-4 text-xs font-semibold text-mint hover:text-white">Sign out →</button></div>
    </aside><SafetyAssistant />
  </>;
}
