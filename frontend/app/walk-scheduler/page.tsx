"use client";

import { FormEvent, useEffect, useState } from "react";
import { AuthGate } from "../../components/auth-gate";
import { DailySchedule, DailyScheduleTimeline } from "../../components/daily-schedule";
import { LocationPicker } from "../../components/location-picker";
import { Sidebar } from "../../components/sidebar";
import { request } from "../../lib/api";

type Block = { start: string; end: string };
type ScheduleAnalysis = { state: "processing" | "completed" | "failed"; analysis_id: string; stage: string; message?: string; completed_intervals?: number; total_intervals?: number; result?: DailySchedule };
const surfaces = [["", "No surface estimate"], ["asphalt", "Asphalt"], ["concrete", "Concrete"], ["grass", "Grass"], ["sand", "Sand"], ["soil_dirt", "Soil / dirt"]];
const ANALYSIS_TIMEOUT_MS = 120_000;

export default function WalkSchedulerPage() {
  const [blocks, setBlocks] = useState<Block[]>([{ start: "", end: "" }]);
  const [schedule, setSchedule] = useState<DailySchedule | null>(null);
  const [analysis, setAnalysis] = useState<ScheduleAnalysis | null>(null);
  const [analysisStartedAt, setAnalysisStartedAt] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const update = (index: number, field: keyof Block, value: string) => setBlocks((current) => current.map((block, item) => item === index ? { ...block, [field]: value } : block));

  useEffect(() => {
    if (!analysis || analysis.state !== "processing") return;
    if (analysisStartedAt !== null && Date.now() - analysisStartedAt >= ANALYSIS_TIMEOUT_MS) {
      setError("FortyGuard is taking longer than expected to generate this schedule. No slots were assigned; please try again shortly.");
      setAnalysis(null);
      setBusy(false);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const next = await request<ScheduleAnalysis>(`/walk-scheduler/analyses/${analysis.analysis_id}`, { timeoutMs: 15_000 });
        if (cancelled) return;
        if (next.state === "completed" && next.result) {
          setSchedule(next.result);
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        } else if (next.state === "failed") {
          setError(next.message ?? "The schedule analysis could not be completed.");
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        } else {
          setAnalysis(next);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "Schedule status is temporarily unavailable.");
          setAnalysis(null);
          setAnalysisStartedAt(null);
          setBusy(false);
        }
      }
    }, 1_500);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [analysis, analysisStartedAt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (blocks.some((block) => !block.start || !block.end)) { setError("Give every availability block a start and end time."); return; }
    if (!latitude || !longitude) { setError("Use your location or enter latitude and longitude first."); return; }
    setBusy(true);
    setError("");
    setSchedule(null);
    setAnalysis(null);
    setAnalysisStartedAt(Date.now());
    try {
      const started = await request<ScheduleAnalysis>("/walk-scheduler/analyses", {
        method: "POST",
        body: JSON.stringify({ latitude: Number(latitude), longitude: Number(longitude), surface: form.get("surface") || null, availability: blocks.map((block) => ({ start: new Date(block.start).toISOString(), end: new Date(block.end).toISOString() })), wait_seconds: 1 }),
      });
      setAnalysis(started);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Daily scheduling is unavailable.");
      setAnalysisStartedAt(null);
      setBusy(false);
    }
  }

  const progress = analysis?.completed_intervals !== undefined && analysis.total_intervals ? ` ${analysis.completed_intervals} of ${analysis.total_intervals} forecast intervals are ready.` : "";
  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-6xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><header className="mb-8"><p className="text-sm font-semibold text-moss">SMART DAILY SCHEDULER</p><h1 className="mt-1 text-3xl font-bold">Plan a safer walk for every dog</h1><p className="mt-2 max-w-3xl text-ink/60">PawGuard checks real FortyGuard forecast intervals and never forces an unsafe slot.</p></header><section className="grid gap-6 lg:grid-cols-[.85fr_1.15fr]"><form onSubmit={submit} className="rounded-3xl bg-white p-6 shadow-card"><h2 className="text-xl font-bold">Your available time</h2><div className="mt-5 space-y-3"><select name="surface" className="w-full rounded-xl border border-ink/15 px-3 py-2.5">{surfaces.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><LocationPicker latitude={latitude} longitude={longitude} onChange={(lat, lon) => { setLatitude(lat); setLongitude(lon); }} /><div className="mt-5 space-y-3">{blocks.map((block, index) => <div key={index} className="rounded-2xl bg-sand p-3"><div className="flex items-center justify-between"><p className="text-xs font-semibold text-moss">BLOCK {index + 1}</p>{blocks.length > 1 && <button type="button" onClick={() => setBlocks((current) => current.filter((_, item) => item !== index))} className="text-xs font-semibold text-red-600">Remove</button>}</div><label className="mt-2 block text-xs text-ink/60">Start<input required value={block.start} onChange={(event) => update(index, "start", event.target.value)} type="datetime-local" className="mt-1 w-full rounded-xl border border-ink/15 bg-white px-3 py-2" /></label><label className="mt-2 block text-xs text-ink/60">End<input required value={block.end} onChange={(event) => update(index, "end", event.target.value)} type="datetime-local" className="mt-1 w-full rounded-xl border border-ink/15 bg-white px-3 py-2" /></label></div>)}</div><button type="button" onClick={() => setBlocks((current) => [...current, { start: "", end: "" }])} className="mt-4 text-sm font-semibold text-moss">+ Add another time block</button><button disabled={busy} className="mt-5 w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? analysis?.message ?? "Analyzing available forecast intervals…" : "Build today’s schedule"}</button>{analysis && <p role="status" className="mt-4 rounded-xl bg-mint/50 p-3 text-sm text-ink/75">{analysis.message ?? "Analyzing available forecast intervals…"}{progress}</p>}{error && <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}</form>{schedule ? <DailyScheduleTimeline schedule={schedule} /> : <aside className="rounded-3xl border border-dashed border-moss/25 bg-mint/30 p-6"><p className="text-sm font-semibold text-moss">REAL FORECASTS ONLY</p><p className="mt-3 text-sm leading-6 text-ink/65">{analysis?.message ?? "Scheduling is limited to completed intervals within the provider’s available forecast horizon."}</p></aside>}</section></div></main></AuthGate>;
}
