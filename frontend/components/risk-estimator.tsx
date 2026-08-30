"use client";

import { FormEvent, useState } from "react";
import { request } from "../lib/api";
import { LocationPicker } from "./location-picker";
import { HeatRisk, RiskCard } from "./risk-card";

export function RiskEstimator({ dogId, dogName }: { dogId: string; dogName: string }) {
  const [risk, setRisk] = useState<HeatRisk | null>(null); const [error, setError] = useState(""); const [checking, setChecking] = useState(false); const [latitude, setLatitude] = useState(""); const [longitude, setLongitude] = useState("");
  async function checkRisk(event: FormEvent) { event.preventDefault(); setChecking(true); setError(""); try { setRisk(await request<HeatRisk>(`/heat-risk/dogs/${dogId}/current`, { method: "POST", body: JSON.stringify({ latitude: Number(latitude), longitude: Number(longitude), wait_seconds: 20 }) })); } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not calculate the estimate."); } finally { setChecking(false); } }
  return <section className="mt-6 grid gap-6 lg:grid-cols-[.75fr_1.25fr]"><form onSubmit={checkRisk} className="rounded-3xl bg-white p-6 shadow-card"><p className="text-sm font-semibold text-moss">CURRENT CONDITIONS</p><h2 className="mt-1 text-xl font-bold">Estimate heat risk</h2><p className="mt-2 text-sm leading-6 text-ink/60">FortyGuard supplies the current environmental data automatically for {dogName}&apos;s profile.</p><LocationPicker latitude={latitude} longitude={longitude} onChange={(lat, lon) => { setLatitude(lat); setLongitude(lon); }} /><button disabled={checking} className="mt-5 w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{checking ? "Checking FortyGuard…" : "Check heat risk"}</button>{error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</form>{risk ? <RiskCard risk={risk} /> : <aside className="rounded-3xl border border-dashed border-moss/25 bg-mint/30 p-6"><p className="text-sm font-semibold text-moss">PERSONALIZED, NOT DIAGNOSTIC</p><p className="mt-3 text-sm leading-6 text-ink/65">PawGuard will show a transparent deterministic estimate after FortyGuard completes the location analysis.</p></aside>}</section>;
}
