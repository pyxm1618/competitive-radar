# Data Model

> **Xiaoshuyin Competitive Radar V1.** The upstream warehouse tables below are
> kept **verbatim** under **"upstream baseline (unchanged)"**. The V1 extension
> (file-protocol artifacts) is appended after that section. V1 creates **no
> second raw-evidence database** — the upstream `raw.raw_pages` (DuckDB) and
> `data/raw/*.parquet` remain the only raw-evidence authority. See
> [AUTHORITY.md](./AUTHORITY.md).

---

# Upstream baseline (unchanged)

The warehouse is a single DuckDB file with three layers: a pipeline-owned
**raw** schema, a dbt **staging** schema (views), and a dbt **marts** schema
(tables). Parquet under `data/raw/` is the durable landing zone (see ADR 0001).

## Lineage

```
config/competitors.yaml
        │  (collectors)
        ▼
raw.raw_pages ──┐                         data/raw/*.parquet  (landing zone)
raw.competitors │
                │  (detect + LLM extract)
                ▼
raw.signals · raw.changes · raw.llm_calls
                │
   ┌────────────┴───────── dbt staging (views) ─────────────┐
   stg_raw_pages · stg_signals · stg_changes · stg_competitors
                │
   ┌────────────┴───────────── dbt marts (tables) ──────────┐
   dim_competitors        fct_changes          fct_hiring
   fct_pricing_history    agg_weekly_competitor fct_signal_duplicates
```

Generated dbt docs (catalog + lineage graph): from `warehouse/dbt/` run
`dbt docs generate` then `dbt docs serve`. The catalog is written to
`warehouse/dbt/target/catalog.json`.

## Raw layer (`raw.*`, written by the pipeline)

| Table | Grain | Key columns |
|-------|-------|-------------|
| `raw_pages` | one fetched snapshot of a URL | `id` (=hash(url, content)), `competitor_id`, `url`, `source_type`, `raw_html`, `clean_text`, `content_hash`, `fetched_at` |
| `competitors` | one competitor | `competitor_id`, `name`, `domain`, `industry`, `tier`, `tracked_urls` (JSON) |
| `signals` | one extracted signal per changed snapshot | `id` (=hash(url, source_hash)), `signal_type`, `title`, `summary`, `entities` (JSON), `significance`, `confidence`, `embedding` (FLOAT[]), `source_hash`, `model`, `extracted_at` |
| `changes` | one detected change | `change_id`, `change_type` (new/updated/removed), `summary`, `significance_score`, `prev_hash`, `new_hash`, `detected_at` |
| `llm_calls` | one LLM API call | `provider`, `model`, token counts, `latency_ms`, `ok`, `error` |

## Staging (`main_staging.*`, dbt views)

Type-cast, lightly cleaned passthroughs: `stg_raw_pages`, `stg_signals`
(carries the embedding), `stg_changes`, `stg_competitors` (adds
`tracked_url_count`). Source freshness/uniqueness tests live in
`models/staging/_sources.yml` and `_staging.yml`.

## Marts (`main_marts.*`, dbt tables)

| Mart | Grain | Notes |
|------|-------|-------|
| `dim_competitors` | competitor | Adds `signal_count`, `high_significance_count`, `last_signal_at`. |
| `fct_changes` | change | Joins the signal's `title`/`confidence`/`entities`; adds **`weighted_significance`** (model significance + 1 for funding/launch/pricing/leadership, capped at 5). Powers the changes feed + ranking. |
| `fct_hiring` | job posting | Parsed from `source_type='jobs'` snapshots: `role`, `location` (from the "Role (Location)" first line), `posted_at`. `removed_at` reserved for run-over-run removal detection (future). |
| `fct_pricing_history` | price point | Heuristic recovery of `plan`/`price`/`currency` from `pricing_change` signals. Sparse by design - the base `Signal` schema has no structured price field; richer history needs dedicated pricing extraction. |
| `agg_weekly_competitor` | competitor × week | `total_changes`, `high_significance_changes`, `new`/`updated` counts, `avg_significance`, `top_significance`. Feeds dashboard trends + weekly report. |
| `fct_signal_duplicates` | signal pair | Embedding near-duplicates within (competitor, signal_type) via `list_cosine_similarity ≥ 0.95`. Enables de-duplication so one announcement isn't double-counted. |

## Significance scoring

The LLM assigns each `Signal` a `significance` (1-5). `fct_changes` derives
`weighted_significance` by boosting strategically important signal types, which
is what the dashboard and report rank on. This keeps scoring deterministic and
in SQL (auditable), not hidden in a prompt.

## Data-quality tests

`dbt test` (run as part of `dbt build`) enforces: uniqueness/not-null on all
keys, `accepted_values` for `change_type` and `signal_type`, `significance` and
`weighted_significance` within 1-5, and source-level uniqueness on raw ids.
Current suite: **40 tests, all passing.**

> Compatibility note: the `raw.signals` / `raw.llm_calls` extraction path above
> is upstream behavior retained for compatibility. It is **not** the default V1
> path; see [AGENTS.md](./AGENTS.md) and [ADR 0005](./adr/0005-antigravity-file-protocol.md).

---

# Competitive Radar V1 extension

V1 adds **file-protocol artifacts** on top of the upstream warehouse. It does
**not** add a second database, a second raw-evidence store, or a second
change-detection authority. Change detection stays deterministic between
collected snapshots (`pipeline/detect/change.py`); AI cannot decide whether a
change happened.

All V1 artifacts live under `data/intelligence/`, `evidence/manual/`, and the
compiled frontend artifact. They are plain JSON/files, validated by
`radar validate` against `data/intelligence/schema/*.schema.json`.

## Pending change (intelligence queue)

- Path: `data/intelligence/pending/<change_id>.json`.
- Written by `radar prepare` from changes already detected by the deterministic
  diff. **No AI** is involved.
- One file per detected `change_id`. This is the work list for Antigravity.
- Read-only input to the Agent; the Agent never writes here.

## Intelligence record (ONE format only)

- Path: `data/intelligence/records/<intelligence_id>.json`.
- Written by the external Antigravity `competitor-intelligence` skill — **one
  record per `change_id`**; duplicate change references are rejected.
- Fields: `change_id`, `competitor_id`, `date`, `summary`, `topic_ids[]`,
  `change_type`, `impact` (high/medium/low), `confidence` (high/medium/low),
  `relevance` (high/medium/low), `decision`
  (act/investigate/watch/ignore), `xiaoshuyin_relevance`, `mechanism`,
  `why_it_matters`, `evidence[]`, `human_review_status`, `analyst`,
  `intelligence_id`, `schema_version`.
- `impact` and `confidence` are **independent** (e.g. `high / low` is valid).
- Validated against
  `data/intelligence/schema/intelligence-record.schema.json`.
- This is the **single intelligence authority**; the frontend renders it through
  the compiled artifact and is not a second store.

## Manual evidence

- Path: `evidence/manual/<evidence_id>/metadata.json` plus asset files in the
  same folder.
- `metadata.json` carries provenance (source, original URL, captured_at,
  description, asset file names). The intelligence record's `evidence[]`
  references the `evidence_id`.
- **Read-only input** to the Agent; it is not a second raw-evidence database and
  the intelligence workflow never writes to `evidence/`.

## Manual research request

- Path: `data/intelligence/research/<request_id>.json`.
- Created when evidence is insufficient; the intelligence record then has
  `confidence: low` (or `medium` at most).
- Fields: `research_question`, `why_needed`, `suggested_steps`,
  `required_evidence` (plus `request_id`, `change_id`, `competitor_id`,
  `status`).
- Template:
  `.agents/skills/competitor-intelligence/resources/manual-research-template.json`.

## Weekly pulse

- Path: `data/intelligence/weekly/<week_start>.json` (`<week_start>` = week start
  date).
- File-based summary derived from intelligence records. It is a derived view,
  not a second intelligence store.

## Compiled frontend artifact

- Path: `web/public/radar-static/radar.json`.
- Built by `radar build` (validate → dbt build → static JSON → frontend build).
  `radar demo-build` compiles from `examples/` fixtures only and never writes
  authority.
- The Next.js app reads it directly and is a **read-only renderer** with four
  entries: Radar (default), Topics, Competitors, Evidence. It is not a source of
  truth.

## Schemas

- Path: `data/intelligence/schema/*.schema.json`.
- The validation contract for intelligence records. `radar validate` checks
  records against these schemas before `radar build`.

## What V1 does NOT add

- **No second raw-evidence database.** Raw evidence stays in upstream
  `raw.raw_pages` (DuckDB) + `data/raw/*.parquet`.
- No second crawler, no second diff engine, no second change-detection
  authority, no second competitor registry, no second intelligence store, and no
  localStorage CRUD as truth. See [AUTHORITY.md](./AUTHORITY.md).
