"use client";

import { FormEvent, useEffect, useState } from "react";

import { AuthGate } from "../../components/auth-gate";
import { LocationPicker } from "../../components/location-picker";
import { Sidebar } from "../../components/sidebar";
import { WalkPlanTimeline, WalkPlan } from "../../components/walk-plan-timeline";
import { Dog, request } from "../../lib/api";

const surfaces = [["", "No surface estimate"], ["asphalt", "Asphalt"], ["concrete", "Concrete"], ["grass", "Grass"], ["sand", "Sand"], ["soil_dirt", "Soil / dirt"]];
const ANALYSIS_TIMEOUT_MS = 120_000;

type ForecastAnalysis = {
  state: "processing" | "completed" | "failed";
  analysis_id: string;
  stage: string;
  message?: string;
  completed_intervals?: number;
  total_intervals?: number;
  result?: WalkPlan;
};

export default function WalkPlannerPage() {
  const [dogs, setDogs] = useState<Dog[]>([]);
  const [plan, setPlan] = useState<WalkPlan | null>(null);
  const [analysis, setAnalysis] = useState<ForecastAnalysis | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");

  useEffect(() => {
    request<Dog[]>("/dogs/").then(setDogs).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!analysis || analysis.state !== "processing") return;
    if (analysisStartedAt !== null && Date.now() - analysisStartedAt >= ANALYSIS_TIMEOUT_MS) {
      setError("FortyGuard is taking longer than expected to generate this forecast. No walk window was ranked; please try again shortly.");
      setAnalysis(null);
      setBusy(false);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await request<ForecastAnalysis>(`/walk-planner/forecast-analyses/${analysis.analysis_id}`, { timeoutMs: 15_000 });
        if (cancelled) return;
        if (next.state === "completed" && next.result) {
          setPlan(next.result);
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        } else if (next.state === "failed") {
          setError(next.message ?? "The forecast analysis could not be completed.");
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        } else {
          setAnalysis(next);
        }
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : "Forecast status is temporarily unavailable.");
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        }
      }
    }, 1_500);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [analysis]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const dogId = String(form.get("dog_id"));
    if (!dogId) { setError("Add or select a dog first."); return; }
    if (!lat || !lon) { setError("Use your location or enter latitude and longitude first."); return; }
    setBusy(true);
    setError("");
    setPlan(null);
    setAnalysisStartedAt(Date.now());
    try {
      const started = await request<ForecastAnalysis>(`/walk-planner/dogs/${dogId}/forecast-analyses`, {
        method: "POST",
        body: JSON.stringify({ latitude: Number(lat), longitude: Number(lon), surface: form.get("surface") || null, horizon_hours: 12, interval_hours: 3 }),
      });
      setAnalysis(started);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Forecast planning is unavailable.");
      setAnalysisStartedAt(null);
      setBusy(false);
    }
  }

  const progress = analysis?.completed_intervals !== undefined && analysis.total_intervals
    ? ` ${analysis.completed_intervals} of ${analysis.total_intervals} forecast intervals are ready.`
    : "";

  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-5xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><header className="mb-8"><p className="text-sm font-semibold text-moss">WALK PLANNER</p><h1 className="mt-1 text-3xl font-bold">Find a lower-risk walk window</h1><p className="mt-2 max-w-2xl text-ink/60">PawGuard uses real FortyGuard forecast tiles automatically for your location.</p></header><section className="grid gap-6 lg:grid-cols-[.8fr_1.2fr]"><form onSubmit={submit} className="rounded-3xl bg-white p-6 shadow-card"><h2 className="text-xl font-bold">Plan the next 12 hours</h2><div className="mt-5 space-y-3"><select required name="dog_id" defaultValue="" className="w-full rounded-xl border border-ink/15 px-3 py-2.5"><option value="" disabled>Select a dog</option>{dogs.map((dog) => <option key={dog.id} value={dog.id}>{dog.name} · {dog.breed}</option>)}</select><select name="surface" className="w-full rounded-xl border border-ink/15 px-3 py-2.5">{surfaces.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><LocationPicker latitude={lat} longitude={lon} onChange={(latitude, longitude) => { setLat(latitude); setLon(longitude); }} /><button disabled={busy} className="mt-5 w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? (analysis?.message ?? "Analyzing the next 12 hours…") : "Find best walk time"}</button>{analysis && <p className="mt-4 rounded-xl bg-mint/50 p-3 text-sm text-ink/75" role="status">{analysis.message ?? "Analyzing the next 12 hours…"}{progress}</p>}{error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</form>{plan ? <WalkPlanTimeline plan={plan} /> : <aside className="rounded-3xl border border-dashed border-moss/25 bg-mint/30 p-6"><p className="text-sm font-semibold text-moss">REAL FORECASTS ONLY</p><p className="mt-3 text-sm leading-6 text-ink/65">PawGuard ranks only completed FortyGuard forecast intervals. Forecast generation continues in the background while this page checks its status.</p></aside>}</section></div></main></AuthGate>;
}
