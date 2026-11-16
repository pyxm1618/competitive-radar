# Competitive Radar Authority — always-on workspace rule

**This rule is always on.** It applies to every task in this repository. These
are short, verifiable rules; see `docs/AUTHORITY.md` for the full model.

## The rules

1. **Single authority paths — never duplicate them.**
   - Competitors: `config/competitors.yaml` (the only registry; intentionally
     `competitors: []` in V1).
   - Topics: `config/topics.yaml` (13 topics, the only taxonomy).
   - Raw evidence: upstream `raw.raw_pages` (DuckDB) + `data/raw/*.parquet`
     (no second raw-evidence database).
   - Change detection: deterministic snapshot comparison
     (`pipeline/detect/change.py`). **AI cannot decide whether a change
     happened.**
   - Intelligence: `data/intelligence/records/<intelligence_id>.json` (ONE
     format, one record per `change_id`).
   - Compiled frontend artifact: `web/public/radar-static/radar.json`.
   No second crawler, no second diff engine, no second database, no second
   competitor registry, no second intelligence store, no localStorage CRUD
   as truth.

2. **Never invent competitors.** The real ~55-competitor list has NOT been
   supplied. Do not invent, scrape, or research competitors to populate
   `config/competitors.yaml`. `config/examples/competitors.sample.yaml` is a
   clearly-labelled sample for tests / demo only, not authority.

3. **Never modify raw snapshots.** Do not write to `data/raw/`, `raw.raw_pages`,
   the DuckDB warehouse, `config/`, `web/`, `evidence/`, or
   `data/intelligence/pending/` from the intelligence workflow.

4. **Never write AI prose into the raw change authority.** AI explains an
   already-detected change; it does not decide it and does not alter the
   deterministic diff results or raw snapshots.

5. **Never add a paid LLM API dependency.** V1 uses NO PAID LLM API. No
   `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, Anthropic API, or any
   model key is required for the normal workflow. `COMPETE_LLM_PROVIDER`
   defaults to `mock`. `radar collect` / `radar prepare` never call a model;
   CI must never fail for a missing model key. Antigravity is external and
   human-triggered, not a runtime dependency.

6. **Frontend is read-only.** `web/` is a renderer with exactly four first-level
   entries (Radar, Topics, Competitors, Evidence). No hardcoded competitor
   list, no second source of truth, no realtime AI chat.

7. **Report commands actually run.** Do not claim a command passed, a test
   result, or a validation result unless you actually ran it. No invented
   competitor names, metrics, screenshots, or sources.
