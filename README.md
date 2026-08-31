# PawGuard

PawGuard is a dog heat-safety and smart walk-planning app. It combines saved dog profiles with server-side FortyGuard environmental data, cautious deterministic safety estimates, real walking routes, and opt-in completed-walk history.

## Structure

```
frontend/       Next.js, TypeScript, Tailwind CSS UI
backend/        FastAPI application and SQLAlchemy session setup
docker-compose.yml  Local PostgreSQL service
```

## Prerequisites

- Node.js 20.9+ and npm
- Python 3.11+
- Docker Desktop (recommended for PostgreSQL)

## Configure

Copy `.env.example` to `.env` at the repository root and replace the example database password for your local environment. Do not commit `.env`; it is ignored by Git. Future provider API keys belong only in the backend environment, never in `NEXT_PUBLIC_*` variables.

## Run locally

1. Start PostgreSQL:

   ```bash
   docker compose up -d db
   ```

2. Create and activate a backend virtual environment, then install packages:

   ```bash
   cd backend
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Run the API from `backend`:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   Verify it at [http://localhost:8000/api/v1/health/](http://localhost:8000/api/v1/health/) or open [http://localhost:8000/docs](http://localhost:8000/docs).

4. Apply the database migrations from `backend` before starting the API or after pulling a schema update:

   ```bash
   alembic upgrade head
   ```

5. In a second terminal, install and run the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000).

## Authentication and dog profiles

PawGuard uses server-issued, HTTP-only session cookies. The backend hashes passwords with Argon2 and all dog endpoints require authentication; every lookup is filtered to the signed-in owner. Available API routes are `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, and CRUD at `/dogs/`.

Set `COOKIE_SECURE=true` in deployed HTTPS environments and generate a unique, high-entropy `SECRET_KEY`. The `backend/alembic` revision directory holds the required schema migration.

## Production deployment: Vercel + Cloud Run

The frontend is designed to call the same-origin `/backend` proxy in production. Browser code must **not** use the Cloud Run `run.app` URL directly.

1. Configure the Vercel project with `frontend` as its Root Directory. The [vercel.json](frontend/vercel.json) rewrite forwards `/backend/:path*` to Cloud Run without changing the browser URL.
2. Set Vercel Production `NEXT_PUBLIC_API_URL=/backend`, then redeploy the frontend. Do not add a trailing `/api/v1`; PawGuard appends it exactly once.
3. Deploy the backend from `backend` using its Dockerfile. Cloud Run supplies `PORT`; no port is hardcoded for production.
4. Set these Cloud Run environment variables securely: `DATABASE_URL`, `SECRET_KEY`, `COOKIE_SECURE=true`, `CORS_ORIGINS=https://<your-vercel-domain>`, plus provider keys as required. `BACKEND_CORS_ORIGINS` is accepted for compatibility, but `CORS_ORIGINS` is preferred.
5. Run `alembic upgrade head` against the production PostgreSQL/Supabase database before accepting signups. Standard Supabase `postgresql://` and legacy `postgres://` URLs are normalized to the installed Psycopg v3 driver.

Because the Vercel rewrite is same-origin, browser requests include the HTTP-only session cookie without relying on cross-origin cookie behavior. Keep the Cloud Run service reachable by Vercel; end-user networks do not need direct access to its `run.app` URL.

## FortyGuard integration

PawGuard calls FortyGuard only from FastAPI; the API key is never sent to the browser. Add your credential to the root `.env`:

```bash
FORTYGUARD_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

Restart the backend after adding it. Without this value, the protected environmental endpoints return a clear `503` with the same instruction and make no external request. The integration follows FortyGuard's asynchronous `POST /v1/env_params`, `POST /v1/heatmap`, and `GET /v1/status/{activity_id}` workflows. The authenticated [Heat Map](http://localhost:3000/heat-map) page is a small test console for environmental parameter submissions; it does not calculate dog risk.

## Automatic environmental data and AI Safety Assistant

PawGuard never asks users to type a current temperature. For current risk, surface risk, Walk Match, and Active Walk, the backend first obtains a real current FortyGuard heatmap temperature tile for the selected location, then uses that documented value in FortyGuard's required environmental-parameters workflow. Forecast, scheduler, route, and map features use their existing real FortyGuard heatmap workflows. Browser geolocation is the primary location option; coordinate entry is a fallback.

The authenticated `POST /api/v1/assistant/chat` endpoint uses `OPENAI_API_KEY` only on the server. It sends the user question plus the minimum structured dog and deterministic PawGuard context needed for the answer; with a supplied location it includes current FortyGuard conditions, calculated heat risk, surface risk where selected, and Walk Match results. It never sends API keys, password hashes, account email, dog notes, or raw provider responses. If the OpenAI key is absent or the service fails, PawGuard returns a clear error and does not fall back to invented advice.

## Personalized heat-risk estimate

`POST /api/v1/heat-risk/dogs/{dog_id}/current` waits for a completed FortyGuard environmental-parameter activity and combines documented conditions with the signed-in owner’s saved dog profile. The rules in `backend/app/core/risk_rules.py` are deterministic and configurable. PawGuard returns an estimated 0–100 score, label, recommendation, and the highest contributors. It is not a veterinary diagnosis; watch for heat-stress signs and seek veterinary care promptly when concerned.

## Paw-surface estimate

`POST /api/v1/surface-risk/dogs/{dog_id}/current` evaluates asphalt, concrete, grass, sand, or soil/dirt with the same completed environmental analysis. Its deterministic rules live in `backend/app/core/surface_risk_rules.py`. This is a relative exposure estimate only: FortyGuard does **not** provide exact pavement temperature, so always check the ground yourself and stop if it feels too hot.

## Best walk time finder

`POST /api/v1/walk-planner/dogs/{dog_id}/forecast` submits documented single-hour forecast heatmap jobs for the next 12 hours, ranks completed intervals with the dog heat-risk estimate and optional surface estimate, then returns the best window, alternatives, and a cautious maximum duration. If provider jobs are unavailable or still processing, PawGuard returns a clear unavailable response rather than making up a forecast.

## Walk Match

`POST /api/v1/walk-match/current` accepts 15, 30, 45, or 60 available minutes and evaluates every dog owned by the signed-in user from a single completed current FortyGuard analysis. It uses the existing personalized heat-risk, optional surface-risk, and duration rules to rank the pack, identify the best current match, and list dogs to avoid. Breed alone is never used as a ranking rule.

## API

`GET /api/v1/health/` returns a simple availability response. The API is CORS-configured from `BACKEND_CORS_ORIGINS`; use a comma-separated list when adding environments.

## Active Walk and Walk History

`POST /api/v1/active-walk/dogs/{dog_id}/status` combines one completed server-side environmental analysis with PawGuard's existing heat, surface, and duration rules. The browser timer is local only. A walk is persisted only when the user explicitly saves it through `POST /api/v1/walks/`; saved fields include the dog snapshot, completed time, duration, selected surface, recorded risk summaries, and optional route metadata. `GET /api/v1/walks/` and `/api/v1/walks/summary` power the History page and dashboard.

## Route Planner and Safety Center

The Route Planner uses server-side OSRM walking geometry and completed FortyGuard heatmap tiles when available. It falls back to normal walking-time ranking when tiles are unavailable. The Safety Center provides cautious educational information and a user-triggered map search for nearby emergency veterinary options; it does not provide live clinic availability, medical diagnosis, or emergency dispatch.

## Test

Run backend tests from `backend`:

```bash
pytest
```

Run frontend tests and production checks from `frontend`:

```bash
pnpm test
pnpm exec tsc --noEmit
pnpm build
```

## Current limitations

- FortyGuard forecast and heatmap jobs are asynchronous. PawGuard reports a clear unavailable state instead of inventing a result if a job does not complete during the bounded wait.
- The dashboard does not automatically fetch a live heat status or best window because no location preference is persisted; it links to the relevant current-condition tools instead.
- PawGuard estimates and Safety Center guidance are not veterinary diagnosis or medical advice.
