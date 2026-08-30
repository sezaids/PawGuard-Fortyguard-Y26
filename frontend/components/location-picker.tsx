"use client";

import { useState } from "react";

type Props = { latitude: string; longitude: string; onChange: (latitude: string, longitude: string) => void; compact?: boolean; required?: boolean };

export function LocationPicker({ latitude, longitude, onChange, compact = false, required = true }: Props) {
  const [message, setMessage] = useState("");
  function useMyLocation() {
    if (!navigator.geolocation) { setMessage("Location is unavailable in this browser. Enter coordinates below instead."); return; }
    setMessage("Getting your location…");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => { onChange(String(coords.latitude), String(coords.longitude)); setMessage("Current location selected."); },
      () => setMessage("Location access was unavailable. Enter coordinates below instead."),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  }
  return <div className={compact ? "space-y-3" : "mt-5 space-y-3"}>
    <button type="button" onClick={useMyLocation} className="w-full rounded-xl bg-mint px-4 py-3 text-sm font-semibold text-moss">Use my location</button>
    {message && <p className="text-xs leading-5 text-ink/60">{message}</p>}
    <details className="rounded-xl border border-ink/10 p-3"><summary className="cursor-pointer text-sm font-medium text-ink/75">Enter coordinates manually</summary><div className="mt-3 grid grid-cols-2 gap-3"><input required={required} value={latitude} onChange={event => onChange(event.target.value, longitude)} type="number" step="any" min="-90" max="90" placeholder="Latitude" aria-label="Latitude" className="w-full rounded-xl border border-ink/15 px-3 py-2.5" /><input required={required} value={longitude} onChange={event => onChange(latitude, event.target.value)} type="number" step="any" min="-180" max="180" placeholder="Longitude" aria-label="Longitude" className="w-full rounded-xl border border-ink/15 px-3 py-2.5" /></div></details>
  </div>;
}
