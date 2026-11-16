# Xiaoshuyin Competitive Radar V1 (小树荫竞品雷达)

An internal product-research tool for the **Xiaoshuyin (小树荫)** product owner.
It watches competitor pages, detects changes **deterministically**, and — via a
human-triggered external Antigravity agent — turns those already-detected changes
into short intelligence records that answer one question: *值得你看的变化?* (is
this change worth your attention?).

This repository is a **thin V1 layer on top of upstream
[`yassnemo/compete`](https://github.com/yassnemo/compete)** (MIT). The guiding
principle is **reuse first, modify minimally**. The confirmed 55-object onboarding
set is now populated in `config/competitors.yaml` (34 Tier 1 / 21 Tier 2).
No paid LLM API is used.

- Target repo: `pyxm1618/competitive-radar`
- Feature branch: `feat/competitive-radar-v1`

## What this is

- A **monitoring + intelligence pipeline**: collect public competitor pages,
  store content-addressed snapshots, diff snapshots deterministically, and queue
  detected changes for analysis.
- An **intelligence workflow**, not an autonomous agent: AI (Antigravity) explains
  changes that the pipeline already detected; it never decides whether a change
  happened.
- A **read-only frontend** that renders compiled intelligence as a radar, topic
  view, competitor view, and evidence view.
- An **internal tool** for product design decisions, not a Xiaoshuyin product
  codebase, a general competitor directory, or a BI dashboard.

The `radar` CLI is a thin wrapper over the upstream pipeline. `radar collect`,
`radar prepare`, and `radar update` never call a model. Analysis is performed by
Antigravity, not by the CLI.

## Architecture (V1 flow)

```
Collection → Snapshot → Diff → Pending Intelligence Queue → Antigravity → Intelligence Output → Frontend

config/competitors.yaml  (competitor authority; 55 onboarded objects)
config/topics.yaml       (topic taxonomy authority; 13 topics)
        |
        v
[Collection]   radar collect
        |      httpx/static, Playwright/dynamic, RSS, jobs  (upstream collectors)
        v
[Snapshot]     raw.raw_pages (DuckDB) + data/raw/*.parquet   (upstream raw layer)
        |
        v
[Diff]         deterministic comparison between collected snapshots
               (upstream pipeline/detect/change.py)  -> detected changes
        |
        v
[Pending Intelligence Queue]   radar prepare
               data/intelligence/pending/<change_id>.json
        |      .------------------------------.  (human-triggered hand-off;
        |      | no model is called by the CLI |   no AI in GitHub Actions)
        v      '------------------------------'
[Antigravity]  EXTERNAL intelligence agent, invoked by a human
               reads: pending + evidence + config/* + context/xiaoshuyin.md
        |
        v
[Intelligence Output]   data/intelligence/records/<intelligence_id>.json
               (one format only; radar validate checks it)
        |
        v
[Frontend]     radar build -> web/public/radar-static/radar.json
               -> Next.js (Renderer, read-only) -> Vercel
```

The integration is a **deterministic file protocol**. Antigravity is an external
intelligence agent, **not** a web-app runtime dependency.

## Authority (single sources)

| Concern | Single source of truth | Exact path |
|---|---|---|
| Competitors | `config/competitors.yaml` (55 onboarded objects: 34 Tier 1 / 21 Tier 2) | `config/competitors.yaml` |
| Topic taxonomy | `config/topics.yaml` (13 topics) | `config/topics.yaml` |
| Raw evidence | upstream `raw.raw_pages` (DuckDB) + `data/raw/*.parquet` | no second raw-evidence DB |
| Change detection | deterministic diff between snapshots (upstream `pipeline/detect/change.py`) | AI cannot decide a change happened |
| Pending queue | `data/intelligence/pending/<change_id>.json` | one file per detected change |
| Intelligence | `data/intelligence/records/<intelligence_id>.json` | ONE format only |
| Manual research queue | `data/intelligence/research/<request_id>.json` | created when evidence is insufficient |
| Weekly pulse | `data/intelligence/weekly/<week_start>.json` | file-based |
| JSON Schemas | `data/intelligence/schema/*.schema.json` | validation contract |
| Manual evidence | `evidence/manual/<evidence_id>/metadata.json` + asset files in the same folder | read-only input |
| Compiled frontend artifact | `web/public/radar-static/radar.json` | built by `radar build` |
| Xiaoshuyin context | `context/xiaoshuyin.md` | relevance guardrails |

See [docs/AUTHORITY.md](docs/AUTHORITY.md) for the full authority model and the
prohibited list.

## How to install

Requires [`uv`](https://docs.astral.sh/uv/) (manages Python 3.12) and Node.js for
the web app.

```bash
uv sync --extra dev --extra dbt --extra api --extra report
uv run playwright install chromium      # for the dynamic collector
cp .env.example .env
cd web && npm install
```

No model key is needed. `COMPETE_LLM_PROVIDER` defaults to `mock`; the upstream
Gemini/Groq/Ollama/mock extraction code is retained for compatibility only and is
not the default path.

## How to collect

```bash
radar collect     # sync competitors -> collect -> snapshot -> deterministic diff (no AI)
radar prepare     # detected changes -> normalize -> generate/update pending queue (no AI)
radar status      # counts and current state
radar update      # collect + prepare + build (no AI)
```

`radar collect` and `radar prepare` never call a model. GitHub Actions runs only
non-AI monitoring (collection, snapshot, diff, pending-queue generation) and must
never fail for a missing model key. With `config/competitors.yaml` empty,
collection has no real targets yet.

## How Antigravity analyzes

Analysis is **human-triggered** in V1; nothing is auto-analyzed on a schedule.

1. Run `radar prepare` to produce `data/intelligence/pending/<change_id>.json`.
2. Open Antigravity and invoke the workspace skill
   `competitor-intelligence` (`.agents/skills/competitor-intelligence/SKILL.md`),
   e.g. via the `analyze-pending` workflow.
3. The Agent reads the pending queue, raw evidence, `config/competitors.yaml`,
   `config/topics.yaml`, `context/xiaoshuyin.md`, and (when needed) previous
   records, then writes **one** intelligence record per `change_id` to
   `data/intelligence/records/<intelligence_id>.json`.
4. Run `radar validate` (validates records against
   `data/intelligence/schema/*.schema.json`) and then `radar build`.

AI explains a change that the deterministic diff already detected; it never
decides whether a change happened. Impact and Confidence are independent
judgements. See [docs/ANTIGRAVITY_WORKFLOW.md](docs/ANTIGRAVITY_WORKFLOW.md).

## How to build frontend

```bash
radar validate    # validate intelligence records
radar build       # validate -> dbt build -> static JSON -> frontend build
radar demo-build  # build compiled JSON from examples/ fixtures only; never writes authority
```

`radar build` produces `web/public/radar-static/radar.json`. The frontend has
**exactly four first-level entries**: **Radar** (default homepage), **Topics**,
**Competitors**, **Evidence**. It is a **Renderer**: read-only, no second
competitor truth, no realtime AI chat.

Quality gates: `uv run pytest`, `uv run ruff check pipeline tests api scripts`,
`uv run black --check pipeline tests api scripts`, `uv run mypy pipeline`,
`cd warehouse/dbt && dbt build`, `cd web && npm run lint && npm run typecheck && npm run build`.

## How to add competitors

Edit **`config/competitors.yaml`** — it is the **only** competitor authority, and
no code changes are required:

```yaml
competitors:
  - id: example
    name: Example (sample only)
    domain: example.com
    industry: sample
    tier: 2
    tracked_urls:
      - url: https://example.com/blog
        source_type: static      # static | dynamic | rss | jobs
        signal_hint: other
```

Then run `radar collect` (the upstream sync is part of `radar collect`).

**Important:** The confirmed 55-object onboarding set is now populated here
(34 Tier 1 / 21 Tier 2). Do not add, remove, substitute, or re-rank competitors
without explicit human authority. The clearly-labelled sample fixture at
`config/examples/competitors.sample.yaml` remains **tests / demo only** and is
**not** authoritative.

## How to add manual evidence

Create a folder per evidence item:

```
evidence/manual/<evidence_id>/
    metadata.json       # provenance: source, captured_at, description, original URL
    <asset files>       # e.g. screenshot.png, page.html — same folder
```

Reference the `evidence_id` from the intelligence record's `evidence[]`. Manual
evidence is read-only input for the Agent; it must never be written to by the
intelligence workflow, and no AI prose is written into the raw change authority.

## How to deploy

**Static-first:** Pipeline → static JSON → Next.js → Vercel.

`radar build` compiles `web/public/radar-static/radar.json`; the Next.js app reads
it directly in the browser. No long-running FastAPI server is needed, no API keys
are required, and there is no backend hosting in the default path. Upstream
FastAPI remains available for live mode / legacy compatibility only. See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## No paid LLM API

V1 uses **NO PAID LLM API**. No `OPENAI_API_KEY`, `GOOGLE_API_KEY`,
`GROQ_API_KEY`, Anthropic API, or any model key is required for the normal
workflow. Upstream Gemini/Groq/Ollama/mock extraction code is retained for
compatibility **only** and is **not** the default path; `COMPETE_LLM_PROVIDER`
now defaults to `mock`. GitHub Actions must never fail for a missing model key.

Antigravity is an external, human-triggered intelligence agent connected by a
deterministic file protocol — it is not a paid model API dependency of the CLI
or the web app.

## What was intentionally not built

- A second crawler / collection pipeline (upstream collectors are reused).
- A second diff engine or a second change-detection authority (upstream
  `pipeline/detect/change.py` is the only one).
- A second database or a second raw-evidence store (upstream DuckDB + Parquet is
  the only one).
- A second competitor registry, a hardcoded frontend competitor list, or
  localStorage CRUD as a source of truth.
- Fully unattended AI analysis (V1 is human-triggered via Antigravity).
- A realtime AI chat in the frontend.
- A production long-running FastAPI server (static-first instead).
- Any paid model API integration for the normal workflow.

## Known limitations

- `config/competitors.yaml` contains the confirmed 55-object onboarding set.
  Public monitoring can still be incomplete for app-only, authenticated,
  research-prototype, or hardware flows; those gaps use manual research requests.
- Intelligence analysis is human-triggered; there is no scheduled auto-analysis.
- Impact and Confidence are independent human judgements; records carry a
  `human_review_status` and require human review.
- The frontend is a read-only renderer; there is no write-through CRUD.
- Manual evidence, the research queue, and the weekly pulse are file-based, not
  automated services.
- Upstream LLM extraction remains for compatibility, not as the default V1 path.

## Upstream attribution

This project is derived from [**`compete`**](https://github.com/yassnemo/compete)
by **Yassine Erradouani**, released under the **MIT License** (Copyright (c) 2026).

- Upstream repository: https://github.com/yassnemo/compete
- Baseline commit imported **verbatim**:
  `ebc32b20c2016282976d2375af5821b530fa66bf`
  (2026-07-03, *"Round out the dashboard: signals + competitors pages, 404/error
  pages"*).
- The original `LICENSE` is kept **UNCHANGED** in the repository root.
- Substantial portions of this repository are upstream code, not original work
  from scratch. Retained: the Python collection pipeline (httpx/static,
  Playwright/dynamic, RSS, jobs), snapshots, deterministic snapshot diff,
  Parquet raw layer, DuckDB warehouse, dbt staging→marts, static JSON export,
  Next.js + TypeScript + Tailwind + shadcn/ui, tests, CI patterns, and
  static/serverless deployment.

See [NOTICE](NOTICE) for the formal attribution notice.

## Documentation

- [ARCHITECTURE](docs/ARCHITECTURE.md) — V1 flow, single monitoring authority, upstream baseline
- [AUTHORITY](docs/AUTHORITY.md) — the single-source-of-truth model and prohibited list
- [ANTIGRAVITY_WORKFLOW](docs/ANTIGRAVITY_WORKFLOW.md) — the deterministic file protocol
- [DATA_MODEL](docs/DATA_MODEL.md) — upstream tables + V1 extension
- [AGENTS](docs/AGENTS.md) — upstream LLM extraction (compatibility only)
- [RUNBOOK](docs/RUNBOOK.md) — daily/weekly procedures, upstream baseline
- [DEPLOYMENT](docs/DEPLOYMENT.md) — static-first path, legacy live mode
- [ADRs](docs/adr/) — 0001–0004 upstream + 0005 Antigravity file protocol
- [CONTRIBUTING](CONTRIBUTING.md) — setup and quality gates
- [NOTICE](NOTICE) — upstream attribution

## License

The original upstream [MIT License](LICENSE) is retained unchanged in the repo
root. See [NOTICE](NOTICE).
