"use client";

import { FormEvent, useEffect, useState } from "react";

import { AuthGate } from "../../components/auth-gate";
import { HeatmapCanvas } from "../../components/heatmap-canvas";
import { Sidebar } from "../../components/sidebar";
import { request } from "../../lib/api";

type HeatmapView = { state: "processing" | "completed" | "failed" | "no_data"; activity_id: string | null; message: string; map_data: Record<string, unknown> | null; stats_data: Record<string, unknown> | null };
const HEATMAP_TIMEOUT_MS = 120_000;

export default function HeatMapPage() {
  const [latitude, setLatitude] = useState(""); const [longitude, setLongitude] = useState(""); const [view, setView] = useState<HeatmapView | null>(null); const [error, setError] = useState(""); const [busy, setBusy] = useState(false); const [locationMessage, setLocationMessage] = useState(""); const [pollCycle, setPollCycle] = useState(0); const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const load = async () => { setBusy(true); setError(""); setView(null); setPollCycle(0); setAnalysisStartedAt(null); try { const started = await request<HeatmapView>("/fortyguard/heatmap-view", { method: "POST", body: JSON.stringify({ latitude: Number(latitude), longitude: Number(longitude), wait_seconds: 20 }) }); setView(started); if (started.state === "processing" && started.activity_id) setAnalysisStartedAt(Date.now()); } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to request a FortyGuard heatmap."); } finally { setBusy(false); } };
  useEffect(() => {
    if (view?.state !== "processing" || !view.activity_id) return;
    if (analysisStartedAt !== null && Date.now() - analysisStartedAt >= HEATMAP_TIMEOUT_MS) {
      setView({ state: "failed", activity_id: view.activity_id, message: "FortyGuard did not complete this heatmap within two minutes. No map values were used.", map_data: null, stats_data: null });
      setAnalysisStartedAt(null);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await request<HeatmapView>(`/fortyguard/heatmap-view/activities/${view.activity_id}`, { timeoutMs: 15_000 });
        if (cancelled) return;
        setView(next);
        if (next.state === "processing") setPollCycle((value) => value + 1); else setAnalysisStartedAt(null);
      } catch (caught) {
        if (!cancelled) { setError(caught instanceof Error ? caught.message : "Unable to check the heatmap status."); setAnalysisStartedAt(null); }
      }
    }, 2_500);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [view?.activity_id, view?.state, pollCycle, analysisStartedAt]);
  function useLocation() { if (!navigator.geolocation) { setLocationMessage("This browser cannot provide your location. Enter coordinates instead."); return; } setLocationMessage("Getting your location…"); navigator.geolocation.getCurrentPosition((position) => { setLatitude(String(position.coords.latitude)); setLongitude(String(position.coords.longitude)); setLocationMessage("Current location selected. Request the map when ready."); }, () => setLocationMessage("Location access was unavailable. Enter coordinates instead."), { enableHighAccuracy: false, timeout: 10_000 }); }
  function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); load(); }
  const stateMessage = view && view.state !== "completed" ? view.message : "";
  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-6xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><header className="mb-8"><p className="text-sm font-semibold text-moss">INTERACTIVE HEAT MAP</p><h1 className="mt-1 text-3xl font-bold">See real neighborhood heat variation</h1><p className="mt-2 max-w-3xl text-ink/60">PawGuard displays completed FortyGuard GeoJSON temperature tiles for a small area around your selected location. Tile colors are relative to the provider&apos;s returned values; select an area for the available raw environmental details.</p></header><section className="grid gap-6 lg:grid-cols-[.78fr_1.22fr]"><form onSubmit={submit} className="rounded-3xl bg-white p-6 shadow-card"><h2 className="text-xl font-bold">Choose a location</h2><button type="button" onClick={useLocation} className="mt-4 w-full rounded-xl bg-mint px-4 py-3 text-sm font-semibold text-moss">Use my current location</button>{locationMessage && <p className="mt-2 text-xs leading-5 text-ink/60">{locationMessage}</p>}<div className="mt-5 space-y-3"><label className="block text-sm font-medium">Latitude<input required value={latitude} onChange={(event) => setLatitude(event.target.value)} type="number" step="any" min="-90" max="90" placeholder="40.7128" className="mt-1 w-full rounded-xl border border-ink/15 px-3 py-2.5" /></label><label className="block text-sm font-medium">Longitude<input required value={longitude} onChange={(event) => setLongitude(event.target.value)} type="number" step="any" min="-180" max="180" placeholder="-74.0060" className="mt-1 w-full rounded-xl border border-ink/15 px-3 py-2.5" /></label></div><button disabled={busy} className="mt-6 w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Requesting FortyGuard tiles…" : "Load interactive heat map"}</button><p className="mt-4 text-xs leading-5 text-ink/50">FortyGuard currently supports U.S. locations. The provider key remains on the PawGuard server.</p>{error && <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm leading-6 text-red-700">{error}</div>}</form><section className="rounded-3xl bg-white p-6 shadow-card">{view?.state === "completed" && view.map_data ? <HeatmapCanvas mapData={view.map_data} statsData={view.stats_data} /> : view?.state === "processing" ? <div className="grid min-h-80 place-items-center rounded-2xl bg-mint/30 p-8 text-center"><div><span className="text-3xl">◌</span><p className="mt-3 font-semibold text-ink">FortyGuard is generating your map</p><p className="mt-2 max-w-sm text-sm leading-6 text-ink/60">{stateMessage} PawGuard will check this same activity again shortly.</p></div></div> : view?.state === "no_data" ? <div className="rounded-2xl bg-amber-50 p-6 text-sm leading-6 text-amber-900"><p className="font-semibold">No map tiles available</p><p className="mt-2">{stateMessage}</p></div> : view?.state === "failed" ? <div className="rounded-2xl bg-red-50 p-6 text-sm leading-6 text-red-800"><p className="font-semibold">Heatmap generation failed</p><p className="mt-2">{stateMessage}</p></div> : <div className="grid min-h-80 place-items-center rounded-2xl border border-dashed border-moss/25 bg-mint/30 p-8 text-center"><div><span className="text-4xl">◉</span><p className="mt-4 font-semibold text-ink">Your map will appear here</p><p className="mt-2 max-w-sm text-sm leading-6 text-ink/60">Use your current location or enter coordinates to request real FortyGuard heatmap tiles.</p></div></div>}</section></section></div></main></AuthGate>;
}
