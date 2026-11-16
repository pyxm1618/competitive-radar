# Contributing

Thanks for your interest in **Xiaoshuyin Competitive Radar V1**! This document
covers local setup and the quality bar for changes. This is a thin V1 layer over
upstream [`yassnemo/compete`](https://github.com/yassnemo/compete) (MIT); the
principle is **reuse first, modify minimally**. See [NOTICE](NOTICE) and
[docs/AUTHORITY.md](docs/AUTHORITY.md).

## Setup

```bash
# Python (uv manages the 3.12 toolchain automatically)
uv sync --extra dev --extra dbt --extra api --extra report
uv run playwright install chromium
cp .env.example .env

# Web
cd web && npm install
```

**No paid LLM API key is needed.** No `OPENAI_API_KEY`, `GOOGLE_API_KEY`,
`GROQ_API_KEY`, Anthropic API, or any model key is required for the normal
workflow or CI. `COMPETE_LLM_PROVIDER` defaults to `mock`; the upstream
Gemini/Groq/Ollama/mock extraction code is retained for compatibility only.

## Project layout

```
pipeline/    collect · extract · detect · report · storage · transform · cli  (upstream)
warehouse/   dbt project (staging → marts, tests, docs)                    (upstream)
api/         FastAPI app (legacy / live mode)                              (upstream)
web/         Next.js dashboard — V1 read-only renderer                     (upstream + V1)
config/      competitors.yaml (competitor authority) + topics.yaml (topic authority)
context/     xiaoshuyin.md (relevance guardrails)
data/intelligence/  pending/ records/ research/ weekly/ schema/ (V1 file protocol)
evidence/manual/    manual evidence folders (V1)
docs/        architecture, authority, data model, agents, runbook, deployment, ADRs
.agents/     skills/ rules/ workflows/ (Antigravity workspace artifacts)
scripts/     seed_demo · demo · screenshots · inspect_marts                (upstream)
tests/       pytest suite (V1: test_radar_authority.py guards authority)
```

## Quality gates (must pass before merge)

**Python**
```bash
uv run pytest
uv run ruff check pipeline tests api scripts
uv run black --check pipeline tests api scripts
uv run mypy pipeline
```

**dbt**
```bash
cd warehouse/dbt && dbt build      # builds marts + runs the data tests
```

**Web**
```bash
cd web && npm run lint && npm run typecheck && npm run build
```

**Radar (V1 file protocol)**
```bash
radar validate    # validate intelligence records against data/intelligence/schema/*.schema.json
radar build       # validate → dbt build → web/public/radar-static/radar.json → frontend build
radar status      # counts and current state
```

`radar collect` / `radar prepare` / `radar update` are no-AI commands. `radar
demo-build` builds compiled JSON from `examples/` fixtures only and never writes
authority. **Do not add a model key to CI**: GitHub Actions runs only non-AI
monitoring and must never fail for a missing model key. No command output is
claimed here — run the gates locally.

## Authority rules (V1)

These are hard rules; see [docs/AUTHORITY.md](docs/AUTHORITY.md) and
`.agents/rules/competitive-radar-authority.md`.

- **Frontend is read-only.** `web/` is a renderer with exactly four first-level
  entries (Radar, Topics, Competitors, Evidence). It must never hardcode a
  competitor list (checked by `tests/test_radar_authority.py`), never be a second
  source of truth, and never use localStorage CRUD as authority.
- **One source of truth per concern.** `config/competitors.yaml` (the confirmed
  55-object competitor authority), `config/topics.yaml` (topics), upstream
  `raw.raw_pages` + `data/raw/*.parquet` (raw evidence), `pipeline/detect/change.py`
  (change detection), `data/intelligence/records/` (intelligence, one format).
  No second crawler, no second diff engine, no second database, no second
  competitor registry, no second intelligence store.
- **AI cannot decide whether a change happened.** Change detection is a
  deterministic snapshot diff. Antigravity explains already-detected changes via
  a human-triggered file protocol and writes only to
  `data/intelligence/records/` and `data/intelligence/research/`.
- **Never invent or silently mutate competitors.** The confirmed 55-object set
  is in `config/competitors.yaml`; additions, removals, substitutions, or
  re-ranking require explicit human authority. The sample fixture at
  `config/examples/competitors.sample.yaml` is tests/demo only.
- **No paid LLM API.** No model key is needed for the normal workflow. Report the
  commands you actually ran; do not claim unverified results.
- **Preserve provenance** in intelligence records (change_id, snapshot refs,
  original URL, pending file path) and keep `impact` and `confidence`
  independent.

## Conventions (upstream, retained)

- **Type hints everywhere** in Python; no `any` in TypeScript.
- The LLM is mocked in tests (`COMPETE_LLM_PROVIDER=mock`) - never call a live
  model from the test suite. In V1 no model is called by the CLI at all.
- Keep secrets out of code; everything is env-driven via `.env` / Settings. No
  model key is required.
- Scraping must stay ethical: public pages only, honor `robots.txt`, throttle,
  honest User-Agent. Don't add login-walled or aggressive collectors.
- New signal types: add to `pipeline/schemas.py::SignalType`, give them styling
  in `web/src/lib/signal-meta.tsx`, and update the `accepted_values` dbt test.
- Architecture decisions go in `docs/adr/` as short ADRs (0001–0004 upstream,
  0005 Antigravity file protocol).
- Intelligence records must validate against
  `data/intelligence/schema/intelligence-record.schema.json`; run `radar
  validate` after writing records.

## Adding a collector

Implement `collect(competitor_id, url) -> list[RawPage]` (see
`pipeline/collect/static.py`), register it in `pipeline/collect/dispatch.py`,
and add a `SourceType`. Be defensive: never raise on a single fetch failure.
Reuse the upstream collectors first — do not build a second crawler.
