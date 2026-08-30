export type ScheduledWalk = { dog_id: string; dog_name: string; start: string; end: string; duration_minutes: number; estimated_risk: number; status: "Low" | "Moderate" | "High" | "Very High"; forecast_temperature_celsius: number; explanation: string };
export type DailySchedule = { scheduled: ScheduledWalk[]; unscheduled: { dog_id: string; dog_name: string; reason: string }[]; message: string; disclaimer: string };

const tone = { Low: "bg-emerald-100 text-emerald-800", Moderate: "bg-amber-100 text-amber-800", High: "bg-orange-100 text-orange-800", "Very High": "bg-red-100 text-red-800" };
const time = (value: string) => new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

export function DailyScheduleTimeline({ schedule }: { schedule: DailySchedule }) {
  return <section className="rounded-3xl bg-white p-6 shadow-card"><p className="text-sm font-semibold text-moss">TODAY&apos;S PACK PLAN</p><p className="mt-2 text-sm leading-6 text-ink/60">{schedule.message}</p>
    {schedule.scheduled.length > 0 && <div className="mt-5 space-y-3">{schedule.scheduled.map((walk, index) => <article key={walk.dog_id} className="rounded-2xl bg-sand p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-moss">WALK {index + 1} · {time(walk.start)}–{time(walk.end)}</p><h3 className="mt-1 text-lg font-bold">{walk.dog_name}</h3><p className="mt-1 max-w-xl text-sm leading-5 text-ink/65">{walk.explanation}</p></div><div className="text-right"><span className={`rounded-full px-3 py-1 text-xs font-bold ${tone[walk.status]}`}>{walk.status} · {walk.estimated_risk}/100</span><p className="mt-2 text-xs text-ink/55">{walk.duration_minutes} min · {walk.forecast_temperature_celsius.toFixed(1)}°C</p></div></div></article>)}</div>}
    {schedule.unscheduled.length > 0 && <div className="mt-5 rounded-2xl bg-red-50 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-red-700">NOT SCHEDULED</p><div className="mt-3 space-y-2">{schedule.unscheduled.map((dog) => <p key={dog.dog_id} className="text-sm leading-5 text-red-800"><span className="font-semibold">{dog.dog_name}:</span> {dog.reason}</p>)}</div></div>}
    <p className="mt-5 rounded-xl bg-sand p-3 text-xs leading-5 text-ink/55">{schedule.disclaimer}</p>
  </section>;
}
