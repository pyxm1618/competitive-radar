# Deployment

> **Xiaoshuyin Competitive Radar V1.** The V1 **static-first** path below is the
> default and requires **no API keys and no backend hosting**. The upstream
> live-backend topology is retained only as a clearly-marked **optional legacy**
> section at the end.

## V1 static-first (default): pipeline → static JSON → Next.js → Vercel

Production is fully static. A thin `radar` wrapper runs the deterministic
pipeline, compiles one JSON file, and the Next.js app reads it directly in the
browser. There is **no long-running FastAPI server**, no backend hosting, and no
API keys in the default path.

```
radar build ──> web/public/radar-static/radar.json ──> Next.js (Renderer) ──> Vercel
```

How it works:

1. `radar collect` / `radar prepare` run **non-AI monitoring** (collection,
   snapshots, deterministic diff, pending-queue generation). They never call a
   model. GitHub Actions runs only these non-AI steps and **must never fail for a
   missing model key**.
2. A **human-triggered** external Antigravity agent turns the pending queue into
   intelligence records at `data/intelligence/records/<intelligence_id>.json`
   (see [ANTIGRAVITY_WORKFLOW.md](./ANTIGRAVITY_WORKFLOW.md)). Antigravity is
   **not** a web-app runtime dependency and is not part of CI.
3. `radar validate` checks the records; `radar build` runs
   `validate → dbt build → static JSON → frontend build` and writes
   `web/public/radar-static/radar.json`.
4. The Next.js app reads that compiled artifact directly in the browser. It is a
   **read-only renderer** with exactly four first-level entries: Radar (default),
   Topics, Competitors, Evidence.

**Deploy to Vercel (Hobby, free):**

```
Root directory:   web
Framework preset: Next.js
Env:              none required — no model key, no API host, no DB host
```

To refresh locally: `radar build` (then commit/deploy the built artifact).
`radar demo-build` builds compiled JSON from `examples/` fixtures only and never
writes authority.

### Secrets and keys for V1

| Secret | Required in V1? |
|---|---|
| `OPENAI_API_KEY` / `GOOGLE_API_KEY` / `GROQ_API_KEY` / Anthropic API key | **No.** V1 uses NO PAID LLM API. None of these is required for the normal workflow or CI. |
| `COMPETE_LLM_PROVIDER` | Optional; defaults to `mock`. Upstream Gemini/Groq/Ollama/mock extraction is compatibility-only, not the default path. |

> **Important:** V1 CI (GitHub Actions) runs only non-AI monitoring and must
> **never** require a model key. If CI fails because a model key is missing, that
> is a bug in the non-AI path — do not "fix" it by adding a key.

### Free-tier cost summary (V1)

| Component | Service | Cost |
|---|---|---|
| Pipeline schedule (non-AI) | GitHub Actions | Free |
| Intelligence analysis | human-triggered Antigravity (external, no paid API) | $0 |
| Warehouse | upstream DuckDB + Parquet (file) | $0 |
| Backend host | none (static JSON) | $0 |
| Dashboard | Vercel Hobby (static) | $0 |

**Total: $0** — no paid model API in the normal workflow.

---

# Optional legacy: upstream live-backend topology (retained)

> Everything below is the upstream `compete` **live-backend** topology imported
> at baseline commit `ebc32b20c...`. It is **optional** and **NOT the V1 default**.
> It is documented only for legacy / compatibility (e.g. if you want
> write-through CRUD or on-demand pipeline runs with a hosted FastAPI). Upstream
> FastAPI remains available for live mode, but V1 production is static-first.

`compete` has three deployable pieces: the **scheduled pipeline**, the **API**,
and the **web dashboard**. All can run on free tiers. The dashboard data is
curated and changes at most weekly, so production does not need a live Python
server at all — we **bake every API response into static JSON** shipped with the
Next.js app and read it directly in the browser.

How it works (upstream legacy):

1. *(V1 note: this legacy paragraph describes the retired upstream exporter. In
   V1 `scripts/export_static_data.py` is a thin wrapper around the authoritative
   compiler and writes only `web/public/radar-static/radar.json`; the old
   `web/public/api-static/` directory was removed.)* The original upstream script
   drove the real FastAPI app via `TestClient`
   and writes each response to `web/public/api-static/**` (JSON + rendered report
   PDFs). Shapes match the Pydantic schemas exactly.
2. `web/.env.production` sets `NEXT_PUBLIC_STATIC_DATA=1`, so a production build
   of the web app reads from `/api-static` instead of `/api`
   (see `web/src/lib/api.ts`). Filtering, sorting and pagination for the
   signals/changes feeds run client-side; competitor CRUD and "Run pipeline"
   persist to a `localStorage` overlay for the visitor's session
   (`web/src/lib/static-store.ts`). *(In V1 this localStorage overlay is a
   per-session display convenience only and is never a source of truth.)*
3. The weekly GitHub Actions run regenerates the JSON and commits it back, which
   triggers a Vercel redeploy.

> Note (legacy): `/competitors/[id]` is rendered on-demand (a free Vercel
> serverless function); everything else is fully static.

The sections below describe the **alternative live-backend** topology (a real
hosted FastAPI), useful if you want write-through CRUD or on-demand pipeline runs.

## Topology (legacy)

```
GitHub Actions cron ──> compete run-all ──> data/compete.duckdb (artifact)
                                                   │
        Oracle Free VM / Fly.io  ──> compete-api (FastAPI, reads the .duckdb)
                                                   │
                       Vercel ──> Next.js dashboard ──(/api proxy)──> API
```

DuckDB is a single file, which shapes deployment: the pipeline writes it; the
API reads it.

## 1. Scheduled pipeline - GitHub Actions (legacy)

`.github/workflows/pipeline.yml` runs `compete run-all` on a weekly cron (and on
manual dispatch). It installs uv + Chromium, runs the pipeline, generates dbt
docs, and uploads `data/compete.duckdb` + reports as a build artifact.

**Secrets (legacy, NOT required in V1):**

| Secret | Purpose |
|---|---|
| `GOOGLE_API_KEY` | *(legacy only)* Gemini extraction in the old `compete run-all` path. **Not required in V1** — V1 CI runs only non-AI monitoring and `COMPETE_LLM_PROVIDER` defaults to `mock`. |
| `GROQ_API_KEY` | *(legacy only)* optional, if using Groq. Not required in V1. |
| `SLACK_WEBHOOK_URL` | optional; presence enables alerts. |

To **persist** the warehouse between runs (instead of artifacts), either commit
the `.duckdb` back to the repo on a data branch, push it to object storage
(e.g. Cloudflare R2 free tier), or point the pipeline at a hosted DB.

## 2. API - Oracle Cloud Always Free VM (or Fly.io) (legacy)

The API needs the `.duckdb` file on disk. On an Always-Free Ampere VM:

```bash
git clone <repo> && cd compete
uv sync --extra api
# fetch the latest warehouse artifact (or run the pipeline on the VM)
COMPETE_API_HOST=0.0.0.0 uv run compete-api
```

Run it under `systemd` or `pm2`, front it with Caddy/Nginx for TLS, and have the
pipeline (cron on the same VM, or an artifact download) refresh the `.duckdb`.
Set `COMPETE_CORS_ORIGINS` to your Vercel URL.

## 3. Web - Vercel (legacy live mode)

```
Root directory:   web
Framework preset: Next.js
Env:              API_PROXY_TARGET = https://<your-api-host>
```

The app calls `/api/*`, which `next.config.mjs` rewrites to `API_PROXY_TARGET`,
so the browser stays same-origin (no CORS in the browser).

## Optional: hosted operational store (Supabase, legacy)

The brief's default is fully file-based (DuckDB). If you want a hosted CRUD store
for competitors/settings, provision a free Supabase Postgres and mirror
`raw.competitors` there; the analytical marts stay in DuckDB. This is documented
as optional and not wired by default (see ADR 0001).

## Environment variables (legacy)

All config is env-driven (`.env` locally, secrets in CI/hosting). See
`.env.example` for the full list: paths, `COMPETE_LLM_PROVIDER` + keys,
embeddings, collection throttle/robots, alerts, and API host/port/CORS. **In
V1, no model key is required** — `COMPETE_LLM_PROVIDER` defaults to `mock` and
the Antigravity step is external and human-triggered.

## Free-tier cost summary (legacy live mode)

| Component | Service | Cost |
|---|---|---|
| Pipeline schedule | GitHub Actions | Free (2,000 min/mo) |
| LLM extraction | Gemini Flash / Groq free tier, or Ollama local / mock | $0 |
| Embeddings | local hashing (default) or local MiniLM | $0 |
| Warehouse | DuckDB + Parquet (file) | $0 |
| API host | none (static JSON) — or Oracle Always Free VM / Fly.io for live mode | $0 |
| Dashboard | Vercel Hobby (static) | $0 |
| Alerts | Slack webhook / SMTP | $0 |
