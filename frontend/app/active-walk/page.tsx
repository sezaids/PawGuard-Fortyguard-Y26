"use client";

import { FormEvent, useEffect, useState } from "react";
import { AuthGate } from "../../components/auth-gate";
import { LocationPicker } from "../../components/location-picker";
import { Sidebar } from "../../components/sidebar";
import { durationWarning, formatElapsed } from "../../lib/active-walk-time";
import { ActiveWalkStatus, isActiveWalkStatus, isActiveWalkUnavailableStatus } from "../../lib/active-walk-status";
import { Dog, request } from "../../lib/api";

const surfaces = [["asphalt", "Asphalt"], ["concrete", "Concrete"], ["grass", "Grass"], ["sand", "Sand"], ["soil_dirt", "Soil / dirt"]];
const unavailableStatusMessage = "Current walk estimates are unavailable. PawGuard could not confirm live conditions, so no risk score or duration limit is shown. Please try again shortly.";

export default function ActiveWalkPage() {
  const [dogs, setDogs] = useState<Dog[]>([]);
  const [dogId, setDogId] = useState("");
  const [surface, setSurface] = useState("asphalt");
  const [status, setStatus] = useState<ActiveWalkStatus | null>(null);
  const [started, setStarted] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");

  useEffect(() => {
    request<Dog[]>("/dogs/")
      .then(setDogs)
      .catch(() => setError("Could not load your dog profiles."));
  }, []);

  useEffect(() => {
    if (!started) return;
    const timer = window.setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [started]);

  async function start(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!dogId) {
      setError("Select a dog before starting a walk.");
      return;
    }

    // Do not show an older estimate as if it were a fresh live result while a
    // FortyGuard-backed refresh is pending or fails.
    setStatus(null);
    setStarted(false);
    setElapsed(0);
    setSaved(false);
    setBusy(true);
    setError("");
    try {
      const next = await request<unknown>(`/active-walk/dogs/${dogId}/status`, {
        method: "POST",
        body: JSON.stringify({
          latitude: Number(latitude),
          longitude: Number(longitude),
          surface,
          walk_time: form.get("walk_time") || null,
          wait_seconds: 20,
        }),
      });

      if (isActiveWalkUnavailableStatus(next)) {
        setError(next.unavailable_reason);
        return;
      }

      if (!isActiveWalkStatus(next)) {
        throw new Error(unavailableStatusMessage);
      }

      setStatus(next);
      setStarted(true);
    } catch (caught) {
      setStatus(null);
      setStarted(false);
      setError(caught instanceof Error ? caught.message : unavailableStatusMessage);
    } finally {
      setBusy(false);
    }
  }

  async function saveCompletedWalk() {
    if (!dogId || !isActiveWalkStatus(status)) {
      setStatus(null);
      setStarted(false);
      setError(unavailableStatusMessage);
      return;
    }

    setBusy(true);
    setError("");
    try {
      await request("/walks/", {
        method: "POST",
        body: JSON.stringify({
          dog_id: dogId,
          duration_minutes: Math.max(1, Math.round(elapsed / 60)),
          surface: status.surface_risk.surface,
          heat_risk_score: status.heat_risk.score,
          heat_risk_status: status.heat_risk.status,
          surface_risk_score: status.surface_risk.score,
          surface_risk_status: status.surface_risk.level,
        }),
      });
      setSaved(true);
      setStarted(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save this completed walk.");
    } finally {
      setBusy(false);
    }
  }

  const hasStatus = isActiveWalkStatus(status);
  const warning = hasStatus && (durationWarning(elapsed, status.recommended_duration_minutes) || status.heat_risk.score >= 50 || status.surface_risk.score >= 50);

  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-6xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><header className="mb-8"><p className="text-sm font-semibold text-moss">ACTIVE WALK</p><h1 className="mt-1 text-3xl font-bold">Keep a calm eye on today&apos;s walk</h1><p className="mt-2 max-w-3xl text-ink/60">Current FortyGuard conditions are loaded automatically; your own observation comes first.</p></header><section className="grid gap-6 lg:grid-cols-[.72fr_1.28fr]"><form onSubmit={start} className="rounded-3xl bg-white p-6 shadow-card"><h2 className="text-xl font-bold">Start a walk</h2><div className="mt-5 space-y-3"><select required value={dogId} onChange={(event) => setDogId(event.target.value)} className="w-full rounded-xl border border-ink/15 px-3 py-2.5"><option value="" disabled>Select a dog</option>{dogs.map((dog) => <option key={dog.id} value={dog.id}>{dog.name} · {dog.breed}</option>)}</select><select value={surface} onChange={(event) => setSurface(event.target.value)} className="w-full rounded-xl border border-ink/15 px-3 py-2.5">{surfaces.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input name="walk_time" type="time" className="w-full rounded-xl border border-ink/15 px-3 py-2.5" /></div><LocationPicker latitude={latitude} longitude={longitude} onChange={(lat, lon) => { setLatitude(lat); setLongitude(lon); }} /><button disabled={busy} className="mt-5 w-full rounded-xl bg-ink px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Checking current conditions…" : started ? "Refresh walk status" : "Start Active Walk"}</button>{started && <button type="button" onClick={() => { setStarted(false); setElapsed(0); }} className="mt-3 w-full rounded-xl border border-ink/15 px-4 py-3 text-sm font-semibold text-ink">End local timer without saving</button>}{error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm leading-6 text-red-700">{error}</p>}</form>{hasStatus ? <section className="rounded-3xl bg-white p-6 shadow-card"><div className="flex flex-wrap items-start justify-between gap-5"><div><p className="text-sm font-semibold text-moss">WALK ELAPSED</p><p className="mt-2 text-5xl font-bold tracking-tight">{formatElapsed(elapsed)}</p><p className="mt-2 text-sm text-ink/60">Cautious limit: {status.recommended_duration_minutes === 0 ? "No outdoor duration recommended" : `${status.recommended_duration_minutes} minutes`}</p></div><div className="rounded-2xl bg-mint p-4 text-right"><p className="text-xs font-semibold text-moss">CURRENT ESTIMATES</p><p className="mt-2 text-sm font-bold">Heat: {status.heat_risk.status} · {status.heat_risk.score}/100</p><p className="mt-1 text-sm font-bold">Surface: {status.surface_risk.level} · {status.surface_risk.score}/100</p></div></div>{warning && <div className="mt-5 rounded-2xl bg-red-50 p-5 text-sm leading-6 text-red-900"><p className="font-bold">Time to pause or end the walk</p><p className="mt-1">{status.caution}</p><a href="/safety" className="mt-3 inline-block font-semibold underline">Open Safety Center</a></div>}<div className="mt-5 grid gap-4 md:grid-cols-2"><article className="rounded-2xl bg-sand p-4"><p className="text-xs font-semibold uppercase tracking-wide text-moss">HYDRATION & REST</p><ul className="mt-3 space-y-2 text-sm leading-5 text-ink/70">{status.reminders.map((reminder) => <li key={reminder}>• {reminder}</li>)}</ul></article><article className="rounded-2xl bg-sand p-4"><p className="text-xs font-semibold uppercase tracking-wide text-moss">WHY PAWGUARD IS CAUTIOUS</p><p className="mt-3 text-sm leading-6 text-ink/70">{status.heat_risk.recommendation}</p><p className="mt-3 text-sm leading-6 text-ink/70">{status.surface_risk.reason}</p></article></div><div className="mt-5 flex flex-wrap gap-3">{!saved ? <button disabled={busy} onClick={saveCompletedWalk} className="rounded-xl bg-moss px-5 py-3 text-sm font-semibold text-white disabled:opacity-50">Save completed walk</button> : <p className="rounded-xl bg-mint px-4 py-3 text-sm font-semibold text-moss">Walk saved to History</p>}<a href="/history" className="rounded-xl border border-ink/15 px-5 py-3 text-sm font-semibold text-ink">View History</a></div><p className="mt-5 rounded-xl bg-sand p-3 text-xs leading-5 text-ink/55">{status.disclaimer}</p></section> : <aside className="rounded-3xl border border-dashed border-moss/25 bg-mint/30 p-6"><p className="text-sm font-semibold text-moss">A TIMER, NOT A TRACKER</p><p className="mt-3 text-sm leading-6 text-ink/65">PawGuard will show elapsed time and conservative duration guidance once FortyGuard responds. If live conditions are unavailable, no estimate is displayed.</p></aside>}</section></div></main></AuthGate>;
}
