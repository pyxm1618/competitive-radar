# Runbook

Operational procedures for running and maintaining **Xiaoshuyin Competitive
Radar V1**. The V1 procedures come first; the upstream `compete` scraper /
rate-limit / backfill procedures that are still useful follow below under
**"upstream baseline (retained)"**.

> Derived from `yassnemo/compete` (MIT). See [NOTICE](../NOTICE). The `radar`
> CLI is a thin wrapper over the upstream pipeline. `radar collect` /
> `radar prepare` / `radar update` never call a model.

## V1 procedures

### Prerequisites

```bash
uv sync --extra dev --extra dbt --extra api --extra report
uv run playwright install chromium      # for the dynamic collector
cp .env.example .env
cd web && npm install
```

No model key is needed. `COMPETE_LLM_PROVIDER` defaults to `mock`.

### Daily / weekly workflow (non-AI monitoring + human-triggered analysis)

```bash
# 1. Non-AI monitoring (safe in CI / GitHub Actions — never needs a model key)
radar collect       # sync competitors -> collect -> snapshot -> deterministic diff (no AI)
radar prepare       # detected changes -> normalize -> generate/update pending queue (no AI)
radar status        # counts and current state

# 2. Human-triggered analysis (NOT in CI, NOT automatic)
#    Open Antigravity, invoke the competitor-intelligence skill
#    (or run the analyze-pending workflow). It reads:
#      data/intelligence/pending/*.json, data/intelligence/schema/*.schema.json,
#      raw snapshots / data/raw/*.parquet, evidence/manual/,
#      config/competitors.yaml, config/topics.yaml, context/xiaoshuyin.md,
#      and prior records in data/intelligence/records/ when needed.
#    It writes ONE record per change_id to:
#      data/intelligence/records/<intelligence_id>.json
#    and, when evidence is insufficient:
#      data/intelligence/research/<request_id>.json

# 3. Validate + build
radar validate      # validate intelligence records against JSON Schemas
radar build         # validate -> dbt build -> static JSON -> frontend build

# Or the combined no-AI command (collect + prepare + build):
radar update
```

`radar demo-build` builds compiled JSON from `examples/` fixtures only and never
writes authority. The weekly pulse lives at
`data/intelligence/weekly/<week_start>.json`.

AI analysis is **human-triggered** via Antigravity (external, not a runtime
dependency). AI explains already-detected changes; it never decides whether a
change happened. See [ANTIGRAVITY_WORKFLOW.md](./ANTIGRAVITY_WORKFLOW.md) and
[`.agents/workflows/analyze-pending.md`](../.agents/workflows/analyze-pending.md).

### Add competitors

Edit **`config/competitors.yaml`** — the **only** competitor authority — then
re-run collection:

```bash
radar collect
```

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

**Important:** In V1 this file is intentionally empty (`competitors: []`). The
real ~55-competitor list has **not** been supplied. **Do NOT invent, scrape, or
research competitors to populate it, and do NOT fabricate the 55.** Import the
authoritative list in one pass when available. The clearly-labelled sample at
`config/examples/competitors.sample.yaml` is for tests / demo only and is **not**
authoritative. The frontend must never hardcode a competitor list (checked by
`tests/test_radar_authority.py`).

### Add manual evidence (directory + metadata.json contract)

Create one folder per evidence item; `metadata.json` plus the asset files live
in the same folder:

```
evidence/manual/<evidence_id>/
    metadata.json
    screenshot.png            # or page.html, note.md, etc. — same folder
```

`metadata.json` contract:

```json
{
  "schema_version": 1,
  "evidence_id": "evm-example-pricing-001",
  "competitor_id": "example",
  "captured_at": "2026-11-16T10:00:00Z",
  "evidence_type": "manual_screenshot",
  "title": "SAMPLE — manually captured competitor pricing page",
  "description": "SAMPLE — screenshot of the pricing change referenced by the record",
  "source_label": "Browser screenshot (manual)",
  "url": "https://example.com/pricing",
  "files": ["screenshot.png"],
  "topic_ids": ["monetization"],
  "related_change_id": null,
  "verification_state": "unverified",
  "captured_by": "human",
  "notes": null
}
```

Reference the `evidence_id` from the intelligence record's `evidence[]`. Manual
evidence is **read-only input** for the Agent; the intelligence workflow must
never write to `evidence/`, and no AI prose is written into raw snapshots or the
raw change authority.

### Create a manual research request

When evidence is insufficient, the Agent lowers `confidence` and writes:

```
data/intelligence/research/<request_id>.json
```

Use the template
`.agents/skills/competitor-intelligence/resources/manual-research-template.json`:

```json
{
  "schema_version": 1,
  "request_id": "req-0123456789abcdef0123",
  "competitor_id": "example",
  "topic_ids": ["monetization"],
  "research_question": "SAMPLE — what exactly changed on the pricing page?",
  "why_needed": "SAMPLE — evidence is thin, confidence was lowered to low",
  "suggested_steps": [
    "SAMPLE — re-capture the page",
    "SAMPLE — confirm the plan names"
  ],
  "required_evidence": [
    {
      "label": "SAMPLE — dated screenshot",
      "required": true,
      "satisfied": false
    },
    {
      "label": "SAMPLE — original URL",
      "required": true,
      "satisfied": false
    }
  ],
  "status": "open",
  "created_at": "2026-11-16T10:00:00Z",
  "created_by": "antigravity",
  "related_change_id": "chg-0123456789abcdef01234567",
  "related_intelligence_id": "int-0123456789abcdef01234567",
  "notes": null
}
```

A human performs the research, adds manual evidence, and the change may be
re-analyzed. Low evidence means low confidence even when the topic feels
important.

### Run weekly pulse

The weekly pulse is a file-based summary at
`data/intelligence/weekly/<week_start>.json` (`<week_start>` is the week's start
date). It is derived from intelligence records in
`data/intelligence/records/`; it is not a second intelligence store. Regenerate
it from the records and keep it under the `weekly/` path.

### Rebuild the static frontend

```bash
radar build         # validate -> dbt build -> web/public/radar-static/radar.json -> frontend build
```

The compiled artifact is `web/public/radar-static/radar.json`. The Next.js app is
a **read-only renderer** with exactly four first-level entries: Radar (default),
Topics, Competitors, Evidence. Deploy the built app to Vercel; no backend and no
API keys are needed (see [DEPLOYMENT.md](./DEPLOYMENT.md)).

### Troubleshoot: empty authority

Symptom: `radar collect` reports no targets / no snapshots, the frontend shows
an empty competitor list.

- This is **expected** in V1: `config/competitors.yaml` is intentionally
  `competitors: []` because the real ~55-competitor list has **not** been
  supplied.
- **Do not** fix it by inventing competitors or by un-commenting the sample
  fixture as production data.
- For tests / local demo only, use
  `config/examples/competitors.sample.yaml` or `radar demo-build`.
- When the authoritative list is available, import it into
  `config/competitors.yaml` in one pass and re-run `radar collect`.

### Troubleshoot: missing model keys

Symptom: a warning or error referencing `GOOGLE_API_KEY`, `GROQ_API_KEY`,
`OPENAI_API_KEY`, or an Anthropic key.

- V1 uses **NO PAID LLM API**. No model key is required for the normal
  workflow. `COMPETE_LLM_PROVIDER` defaults to `mock`.
- `radar collect` / `radar prepare` / `radar update` never call a model, and
  GitHub Actions runs only non-AI monitoring and must **never fail** for a
  missing model key. If CI fails on a missing key, that is a bug in the
  non-AI path — do not "fix" it by adding a key.
- Upstream Gemini/Groq/Ollama/mock extraction code is retained for
  compatibility **only** and is **not** the default path. Antigravity analysis
  is human-triggered and external, not a key-based runtime dependency.

---

# Upstream baseline (retained)

> The sections below are upstream `compete` operational procedures imported at
> baseline commit `ebc32b20c...`. They still apply to the collection / scraper
> layer that V1 reuses. Commands shown here use the upstream `compete` CLI; the
> V1 `radar` wrapper is preferred for the V1 workflow above. The LLM-related
> guidance (`compete extract`, provider keys) is **compatibility-only** in V1.

Operational procedures for running and maintaining `compete`.

## Prerequisites (upstream baseline)

```bash
uv sync --extra dev --extra dbt --extra api --extra report
uv run playwright install chromium      # for the dynamic collector
cp .env.example .env                     # Windows: copy .env.example .env
uv run compete init-db
```

## Add a competitor (upstream baseline)

Two ways - both end up in `raw.competitors`:

1. **Config (version-controlled):** edit `config/competitors.yaml`, then
   ```bash
   uv run compete sync-competitors
   ```
2. **UI / API:** Settings → "Add competitor", or `POST /competitors`.

> After editing `competitors.yaml`, always run `sync-competitors` (or `run-all`)
> so `dim_competitors` reflects the change.

Then collect + extract just that competitor:

```bash
uv run compete collect --competitor <id>
uv run compete extract
```

## Run the full pipeline (upstream baseline)

```bash
uv run compete run-all                 # sync → collect → extract → dbt → report
uv run compete run-all -p mock -n 5    # offline, capped to 5 URLs/candidates
```

Individual steps: `collect`, `detect` (dry-run, no LLM), `extract`, `report`.

## Backfill / re-extract (upstream baseline)

- Snapshots are content-addressed; re-running `collect` only stores genuinely
  new content. `extract` skips any `(url, content_hash)` already in
  `raw.signals`, so re-runs are cheap and idempotent.
- To force re-extraction of everything: `DELETE FROM raw.signals;` then
  `uv run compete extract` (DuckDB CLI or `uv run python -c "..."`).
- To rebuild marts after manual changes: `cd warehouse/dbt && dbt build`.

## Fix a broken scraper (upstream baseline)

Symptoms: `collect` reports `failed` for a URL, or signals stop appearing.

1. Identify the source type in `competitors.yaml`.
2. Test the URL in isolation:
   ```bash
   uv run python -c "from pipeline.collect.static import StaticCollector as C; print(C().collect('x','https://…'))"
   ```
   (swap `static` for `dynamic` / `rss`; jobs uses ATS APIs - verify the board token.)
3. Common causes & fixes:
   - **JS-rendered content empty** → change `source_type` to `dynamic`.
   - **403 / blocked** → the site may disallow bots; check `robots.txt` (we honor
     it). Do not bypass. Consider an official feed/API instead.
   - **Jobs board returns nothing** → confirm the ATS (Greenhouse/Lever/Ashby)
     and the board token in the URL path; otherwise the JSON-LD fallback applies.
   - **Playwright error "Executable doesn't exist"** → `uv run playwright install chromium`.

## Handle rate limits (upstream baseline)

- **Scraping:** raise `COMPETE_THROTTLE_SECONDS`; the collector also honors any
  `Crawl-delay` in robots.txt (uses the stricter of the two).
- **LLM:** the snapshot-diff gate means only real changes hit the model. Cap a
  run with `compete extract -n N`. Switch provider with `-p groq` / `-p ollama`,
  or `-p mock` for zero cost. Token usage per call is logged in `raw.llm_calls`
  (`compete status` shows the running total). *(Compatibility-only in V1; the
  default V1 path calls no model.)*

## Inspect the warehouse (upstream baseline)

```bash
uv run compete status                  # counts + latest signals + token total
uv run python scripts/inspect_marts.py # mart row counts + samples
cd warehouse/dbt && dbt docs generate && dbt docs serve   # lineage + catalog
```

## Reports & alerts (upstream baseline)

```bash
uv run compete report          # generate the weekly brief (stored in raw.reports)
uv run compete alert-test      # dry-run an alert (or live if configured + enabled)
```

Enable alerts by setting `COMPETE_ALERTS_ENABLED=true` plus a `SLACK_WEBHOOK_URL`
and/or SMTP_* vars in `.env`.
