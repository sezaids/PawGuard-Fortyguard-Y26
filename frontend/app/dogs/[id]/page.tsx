"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthGate } from "../../../components/auth-gate";
import { RiskEstimator } from "../../../components/risk-estimator";
import { SurfaceEstimator } from "../../../components/surface-estimator";
import { Sidebar } from "../../../components/sidebar";
import { Dog, request } from "../../../lib/api";

export default function DogProfilePage() {
  const { id } = useParams<{ id: string }>(); const router = useRouter(); const [dog, setDog] = useState<Dog | null>(null);
  useEffect(() => { request<Dog>(`/dogs/${id}`).then(setDog).catch(() => router.replace("/dogs")); }, [id, router]);
  async function remove() { if (confirm(`Remove ${dog?.name}'s profile?`)) { await request(`/dogs/${id}`, { method: "DELETE" }); router.push("/dogs"); } }
  if (!dog) return <AuthGate><main className="grid min-h-screen place-items-center bg-sand">Loading profile…</main></AuthGate>;
  const details = [["Breed", dog.breed], ["Body size", dog.body_size], ["Weight", dog.weight_kg ? `${dog.weight_kg} kg` : "Not added"], ["Coat", `${dog.coat_length} ${dog.coat_color ?? "coat"}`], ["Activity", dog.activity_level], ["Fitness", dog.fitness_level], ["Short-nosed", dog.brachycephalic ? "Yes" : "No"]];
  return <AuthGate><main className="min-h-screen bg-sand md:pl-72"><Sidebar /><div className="mx-auto max-w-4xl px-5 pb-12 pt-20 sm:px-8 md:pt-10"><Link href="/dogs" className="text-sm font-semibold text-moss">← Back to My Dogs</Link><section className="mt-5 rounded-3xl bg-ink p-7 text-white shadow-card"><div className="flex flex-wrap items-center justify-between gap-5"><div className="flex items-center gap-5"><span className="grid h-20 w-20 place-items-center rounded-3xl bg-mint text-4xl">🐶</span><div><p className="text-sm font-semibold text-mint">DOG PROFILE</p><h1 className="mt-1 text-3xl font-bold">{dog.name}</h1><p className="mt-1 text-white/65">{dog.breed}</p></div></div><Link href={`/dogs/${dog.id}/edit`} className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-ink">Edit profile</Link></div></section><section className="mt-6 grid gap-4 sm:grid-cols-2">{details.map(([label, value]) => <article key={label} className="rounded-2xl bg-white p-5 shadow-card"><p className="text-xs font-semibold uppercase tracking-wide text-moss">{label}</p><p className="mt-2 text-lg font-bold capitalize">{value}</p></article>)}</section><RiskEstimator dogId={dog.id} dogName={dog.name} /><SurfaceEstimator dogId={dog.id} />{dog.notes && <section className="mt-5 rounded-2xl bg-white p-6 shadow-card"><p className="text-xs font-semibold uppercase tracking-wide text-moss">Notes</p><p className="mt-2 text-sm leading-6 text-ink/70">{dog.notes}</p></section>}<button onClick={remove} className="mt-7 text-sm font-semibold text-red-600">Delete {dog.name}&apos;s profile</button></div></main></AuthGate>;
}
