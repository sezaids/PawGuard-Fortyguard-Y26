"use client";

import { AuthGate } from "../../components/auth-gate";
import { Sidebar } from "../../components/sidebar";

export default function SettingsPage() {
  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-4xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><p className="text-sm font-semibold text-moss">SETTINGS</p><h1 className="mt-1 text-3xl font-bold">Account & privacy</h1><section className="mt-6 rounded-3xl bg-white p-6 shadow-card"><h2 className="text-xl font-bold">Your PawGuard data</h2><p className="mt-3 text-sm leading-6 text-ink/65">Dog profiles and completed walks are private to your signed-in account. PawGuard keeps provider credentials on the server and does not save an Active Walk until you explicitly choose “Save completed walk.”</p><p className="mt-4 text-sm leading-6 text-ink/65">More account preferences can be added here in a future update. Use the sidebar to sign out securely.</p></section></div></main></AuthGate>;
}
