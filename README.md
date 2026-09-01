# PawGuard

> **Walk smart. Stay cool.** PawGuard helps dog owners plan more heat-aware walks by combining real FortyGuard environmental analysis with each dog’s saved profile and clear, cautious guidance.

[![Frontend](https://img.shields.io/badge/Frontend-Next.js%20%2B%20TypeScript-111827?logo=next.js)](frontend/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](backend/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql)](backend/alembic/)
[![Heat data](https://img.shields.io/badge/Environmental%20data-FortyGuard-F97316)](https://fortyguard.com/)

## Live Demo

[Open PawGuard](https://paw-guard-fortyguard-y26.vercel.app/)

## Demo Video

[Watch the demo](https://www.youtube.com/watch?v=Hbe9aCMw-BM)

## Temporary Crendentials
Email: test@pawguard.com <br>
Password: Paw13579

## Problem

Warm-weather walks are not one-size-fits-all. A dog’s coat, size, age, fitness, activity level, and breathing anatomy can all matter, while outdoor conditions and surface exposure can change quickly. Dog owners need practical planning support without false precision or medical claims.

## Solution

PawGuard is a responsive web app that turns a selected location, real **FortyGuard** analysis, and a saved dog profile into explainable planning tools. It keeps environmental-provider credentials on the server, uses deterministic safety rules for its estimates, and clearly distinguishes live results from profile-only guidance.

## Core Features

| Area | What PawGuard provides |
| --- | --- |
| Personalized dog profiles | Private multi-dog profiles with heat-relevant characteristics and ownership protection. |
| Heat & surface estimates | Explainable 0–100 heat estimate, estimated surface exposure, key contributors, and cautious recommendations. |
| Smart planning | Forecast-window ranking, recommended duration, Walk Match, and a non-overlapping daily multi-dog schedule. |
| Location-aware tools | Interactive FortyGuard heat map and heat-aware routes using real walking geometry. |
| During-walk support | Active Walk timer, recorded risk summaries, reminders, Safety Center, and emergency-vet map search. |
| Grounded AI assistance | An authenticated assistant grounded in PawGuard’s structured results, with profile-based fallback when live data is unavailable. |

## Tech Stack

| Layer | Technology |
| --- | --- |
| Web app | Next.js App Router, React, TypeScript, Tailwind CSS |
| API | FastAPI, Pydantic, SQLAlchemy |
| Database & migrations | PostgreSQL, Alembic, Psycopg 3 |
| Authentication | Argon2 password hashing, signed JWT session in an HTTP-only cookie |
| Environmental intelligence | FortyGuard Temperature API v1, called only by FastAPI |
| Routes | OSRM foot-routing service, called only by the backend |
| AI assistant | OpenAI Responses API, called only by the backend |
| Production | Vercel frontend, Render web service, Supabase PostgreSQL |

## Architecture

```text
                         ┌──────────────────────────┐
                         │        Browser           │
                         │  Next.js + Tailwind UI    │
                         └────────────┬─────────────┘
                                      │ HTTPS, same-origin cookie
                                      ▼
                    ┌─────────────────────────────────┐
                    │             Vercel              │
                    │  Next.js frontend + /backend/*  │
                    │         reverse proxy           │
                    └────────────┬────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────┐
                    │          Render Free            │
                    │          FastAPI API             │
                    │ auth · risk rules · async polls │
                    └───┬───────────────┬─────────────┘
                        │               │
              ┌─────────▼────────┐  ┌───▼──────────────────────┐
              │ Supabase         │  │ Server-only integrations │
              │ PostgreSQL       │  │ FortyGuard · OSRM · OpenAI│
              │ users/dogs/walks │  │                          │
              └──────────────────┘  └──────────────────────────┘
```

The browser calls `/backend/api/v1/...` in production. Vercel’s rewrite forwards that traffic to Render while the browser stays on the PawGuard origin, so the HTTP-only session cookie remains same-origin. Provider API keys, database credentials, and the signing secret never belong in frontend variables or browser code.

## How PawGuard Works

1. A user signs up, signs in, and creates one or more dog profiles.
2. The user chooses **Use my location** where a current location is needed; latitude/longitude entry is available as a fallback.
3. FastAPI requests the relevant FortyGuard activity and polls its status when the provider processes asynchronously.
4. Once real completed data is available, PawGuard applies its deterministic profile, surface, duration, scheduling, or route rules.
5. The UI shows results, clear processing/error/no-data states, and safety disclaimers rather than fabricated environmental values.

## FortyGuard Integration

FortyGuard is central to PawGuard. The backend uses its documented v1 workflows for environmental parameters and heatmap activities. For asynchronous work, PawGuard creates an activity, retains its activity ID server-side, and polls the provider’s status endpoint until completion, failure, no-data, or a bounded timeout.

- **Current conditions:** PawGuard obtains a completed current heatmap result, then requests supported environmental parameters for the selected point.
- **Forecast planning:** Completed heatmap intervals within the available 12-hour horizon are ranked; missing intervals are never invented.
- **Heat Map:** Completed FortyGuard GeoJSON tiles and available statistics are displayed on the interactive map.
- **Route heat exposure:** PawGuard requests a heatmap for the candidate routes’ bounding area and calculates a relative exposure index only from usable returned tile values.

Provider issues are surfaced as meaningful states, including missing configuration, unsupported request/location, quota or rate limits, processing, failure, and no data. PawGuard does not claim exact pavement or street-level temperatures.

## Personalized Heat-Risk System

PawGuard returns an **estimated 0–100 score** with `Low`, `Moderate`, `High`, or `Very High` status, a walk-now recommendation, and the leading contributors. The calculation is deterministic and configurable in the backend—never generated by an LLM.

When present in completed environmental data, the rules consider apparent temperature, humidity, and solar exposure. Profile factors include age/date of birth, weight and body size, coat color and thickness, brachycephalic status, activity level, and fitness level. These are cautious product heuristics, not medical thresholds or a veterinary diagnosis.

## Paw / Surface Risk

For **asphalt, concrete, grass, sand, and soil/dirt**, PawGuard combines the selected surface with available environmental conditions and time of day. It returns an estimated risk level, reasons, leading factors, and safer alternatives. This feature explicitly labels its output as an estimate: FortyGuard does not provide an exact pavement-temperature reading.

## Walk Planner

The Best Walk Time Finder starts an asynchronous forecast analysis for a selected dog and location. It ranks only completed FortyGuard intervals, optionally includes surface risk, and returns a best window, alternatives, estimated risk, and a cautious recommended duration. If no lower-risk window exists, it says so instead of forcing a plan.

## Walk Match

“I’m free now—who can I walk?” evaluates every dog owned by the signed-in user for 15, 30, 45, or 60 available minutes. A single completed current FortyGuard analysis is reused across the pack. Dogs are ranked by their existing personalized heat estimate, optional surface estimate, and duration guidance—not by breed alone.

## Daily Walk Scheduler

Users can supply up to eight available time blocks. PawGuard uses real forecast intervals in FortyGuard’s supported horizon to suggest non-overlapping walks, prioritizes more heat-sensitive dogs for safer available windows, and clearly marks any dog that cannot be safely scheduled.

## Interactive Heat Map

The Heat Map page requests a small-area FortyGuard GeoJSON heatmap around the selected location. It polls the same activity until terminal status, then visualizes the returned tiles and available statistics. Loading, provider error, unsupported/no-data, and bounded-timeout states are handled explicitly.

## Heat-Aware Route Planner

PawGuard can compare a start-to-destination walk or generate a short loop. It obtains real foot-route geometry from OSRM, requests FortyGuard heat tiles for the route area, and ranks routes with a transparent relative heat-exposure cost while keeping detours within configured limits. If usable heat tiles are unavailable, it falls back to normal walking-time ranking and labels heat optimization as unavailable.

## Active Walk & History

Active Walk combines a selected dog, selected surface, and current FortyGuard analysis to show elapsed time, a cautious duration limit, heat and surface estimates, and hydration/rest reminders. Users can explicitly save a completed walk; Walk History stores the dog snapshot, completion time, duration, surface, recorded risk summaries, and optional route metadata, then provides recent-walk summaries.

## Safety Center

The Safety Center provides cautious education about possible heat-stress warning signs, steps to take if a dog seems overheated, and urgent situations that need veterinary help. Its Emergency Vet Finder uses a user-triggered location lookup to open a nearby map search; it does not claim live clinic hours, capacity, or emergency availability.

## AI Safety Assistant

The authenticated **Ask PawGuard** assistant is available throughout the signed-in app. With a supplied location, it receives only the minimum structured PawGuard context needed to answer: saved dog traits, completed current environmental data, and deterministic heat/surface/Walk Match results where available. It cannot override PawGuard’s deterministic recommendations or duration limits.

Without live conditions, it returns concise, dog-specific **Profile-based guidance only**—for example, noting relevant saved coat, size, fitness, or brachycephalic factors and practical precautions. It does not claim whether a walk is currently safe without live FortyGuard data. It never receives API keys, password hashes, account email, dog notes, or raw provider responses.

## Authentication & Dog Profiles

- Sign up, login, logout, and current-session endpoints
- Argon2 password hashing and server-issued signed session cookies
- HTTP-only cookie handling with secure-cookie support for HTTPS deployment
- Protected routes and owner-scoped database queries
- Add, view, edit, and delete multiple dog profiles
- Profile validation for name, breed, age/date of birth, weight, body size, coat color, coat length, brachycephalic status, activity level, fitness level, and optional notes

## Getting Started

### Prerequisites

- Node.js 20.9+
- Python 3.11+
- Docker Desktop for the included local PostgreSQL service (or another PostgreSQL database)

### Environment Variables

### Optional demo seed

PawGuard never creates demo content during application startup. To initialize the
single designated hackathon demo account after migrations, configure these
values only in the deployment environment, then run the command once:

```bash
DEMO_SEED_ENABLED=true
DEMO_ACCOUNT_EMAIL=demo-account-email@example.com
DEMO_ACCOUNT_PASSWORD=use-a-strong-demo-password
python -m app.db.seed_demo
```

The command is idempotent: it creates only missing Max, Bruno, Luna, Bella,
and Coco profiles plus six clearly marked sample saved walks for that account.
It does not call FortyGuard or create current conditions. Remove the three
temporary seed variables after initialization; the demo account continues to
work normally.

Copy the template before starting. Use your own values; do not commit the resulting `.env` file.

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Server-side PostgreSQL connection string. |
| `SECRET_KEY` | High-entropy server-side signing key. |
| `CORS_ORIGINS` | Comma-separated browser origins permitted to call FastAPI. |
| `COOKIE_SECURE` | `false` for local HTTP; `true` for deployed HTTPS. |
| `FORTYGUARD_API_KEY` | Server-only FortyGuard API credential. |
| `OPENAI_API_KEY` | Server-only credential for the AI Safety Assistant. |
| `OPENAI_MODEL` | OpenAI model name used by the assistant. |
| `NEXT_PUBLIC_API_URL` | Frontend API base: `http://localhost:8000` locally, `/backend` in Vercel production. |

The checked-in template contains placeholders only. Keep `FORTYGUARD_API_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`, and `SECRET_KEY` out of Git and out of `NEXT_PUBLIC_*` variables.

### Run PostgreSQL Locally

```bash
docker compose up -d db
```

### Run the Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API health check: [http://localhost:8000/api/v1/health/](http://localhost:8000/api/v1/health/)
Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Run the Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000).

### Test and Build

```bash
# backend/
pytest -q
alembic upgrade head --sql

# frontend/
pnpm test
pnpm exec tsc --noEmit
pnpm build
```

## Deployment Architecture

PawGuard’s checked-in production configuration uses:

| Service | Deployment role |
| --- | --- |
| **Vercel** | Hosts the Next.js app with `frontend` as the project root. `frontend/vercel.json` rewrites `/backend/:path*` to the Render API. |
| **Render Free** | Runs the FastAPI web service from `backend`. Its start command runs `alembic upgrade head` and only starts Uvicorn if migration succeeds. |
| **Supabase** | Supplies the production PostgreSQL database through `DATABASE_URL`. Standard Supabase PostgreSQL URLs are normalized to the installed Psycopg driver; percent-encoded credentials are safely escaped for Alembic. |

For production:

1. Set Vercel Production `NEXT_PUBLIC_API_URL=/backend` and deploy from the `frontend` root directory.
2. Create the Render web service from [`render.yaml`](render.yaml), then set the required server-side secrets in Render.
3. Set Render `CORS_ORIGINS=https://paw-guard-fortyguard-y26.vercel.app` and keep `COOKIE_SECURE=true`.
4. Supply the Supabase connection string only to Render as `DATABASE_URL`.

## Why PawGuard Matters

PawGuard makes heat-aware walking more actionable: it joins hyperlocal environmental analysis from **FortyGuard** with the realities of an individual dog, surface choice, available time, and walking route. Its design favors explainability, privacy, cautious wording, and honest unavailable-data states over false certainty.

> PawGuard is a planning and awareness tool, not veterinary diagnosis, medical advice, emergency dispatch, or a guarantee of safety. Stop activity and seek veterinary help promptly for concerning symptoms.
