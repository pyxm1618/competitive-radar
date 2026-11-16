# Authority (single sources of truth)

Xiaoshuyin Competitive Radar V1 is built on **one authority per concern**. There
is no duplicate, shadow, or fallback source of truth. When two files appear to
disagree, the authority listed below wins, and the other file is a derived
artifact that must be regenerated rather than edited by hand.

This document is the unambiguous authority model. It complements
[ARCHITECTURE.md](./ARCHITECTURE.md) and
[ANTIGRAVITY_WORKFLOW.md](./ANTIGRAVITY_WORKFLOW.md).

## One authority per concern

| # | Concern | ONE authority | Exact path | Notes |
|---|---|---|---|---|
| 1 | Competitors | `config/competitors.yaml` | `config/competitors.yaml` | The **only** competitor registry. Intentionally `competitors: []` in V1 — the real ~55-competitor list has **not** been supplied. Never fabricate it. |
| 2 | Topic taxonomy | `config/topics.yaml` | `config/topics.yaml` | 13 topics: `problem-discovery`, `assessment`, `diagnosis`, `ai-conversation`, `action-plan`, `family-collaboration`, `child-participation`, `tracking`, `follow-up`, `reflection`, `report`, `expert-service`, `monetization`. Intelligence `topic_ids[]` may only reference these. |
| 3 | Raw evidence | upstream `raw.raw_pages` (DuckDB) + `data/raw/*.parquet` | `data/raw/*.parquet` / DuckDB `raw.raw_pages` | The **only** raw-evidence store. No second raw-evidence database. Manual evidence lives separately (below) and is read-only input. |
| 4 | Change detection | deterministic comparison between collected snapshots | upstream `pipeline/detect/change.py` | The **only** change authority. **AI cannot decide whether a change happened.** |
| 5 | Intelligence | `data/intelligence/records/<intelligence_id>.json` | `data/intelligence/records/` | **ONE** intelligence format only. One record per `change_id`. |
| 6 | Compiled frontend artifact | `web/public/radar-static/radar.json` | `web/public/radar-static/radar.json` | Built by `radar build`; derived, never hand-edited. |

### Supporting file-protocol paths (derived / queue / input, not authorities)

| Role | Path | Notes |
|---|---|---|
| Pending intelligence queue | `data/intelligence/pending/<change_id>.json` | Written by `radar prepare` from detected changes. Input to Antigravity. |
| Manual research queue | `data/intelligence/research/<request_id>.json` | Created when evidence is insufficient. |
| Weekly pulse | `data/intelligence/weekly/<week_start>.json` | File-based weekly summary. |
| JSON Schemas | `data/intelligence/schema/*.schema.json` | The validation contract for intelligence records. |
| Manual evidence | `evidence/manual/<evidence_id>/metadata.json` + asset files in the same folder | Read-only input to the Agent; referenced by `evidence[]`. |
| Xiaoshuyin context | `context/xiaoshuyin.md` | Relevance guardrails for the Agent. |
| Sample competitor fixture | `config/examples/competitors.sample.yaml` | Clearly-labelled **sample**, tests / demo only, **not** authoritative. |

## Frontend = Renderer, read-only

The frontend (`web/`) has **exactly four first-level entries**: **Radar**
(default homepage), **Topics**, **Competitors**, **Evidence**. It reads the
compiled artifact `web/public/radar-static/radar.json` and renders it. It is:

- **Read-only** — no writes to any authority.
- **Not a second competitor truth** — it must never maintain or hardcode its own
  competitor list.
- **Not a second intelligence store** — it renders compiled intelligence only.
- **Not an AI surface** — no realtime AI chat, no model calls.

## Prohibited

The following are explicitly prohibited in V1:

- **Two crawlers / two collection pipelines.** Reuse the upstream collectors.
- **Two diff engines / two change-detection authorities.** Upstream
  `pipeline/detect/change.py` is the only one.
- **Two competitor registries.** Only `config/competitors.yaml`; no frontend
  hardcoded list, no second YAML/JSON registry. The upstream FastAPI CRUD
  endpoints (`api/routers/competitors.py`) are retained for legacy live-mode
  compatibility only and are **not** wired into the V1 default path; they must
  never be used as a competitor authority. `radar collect` mirrors
  `config/competitors.yaml` into `raw.competitors` as a one-way derived copy.
- **Two databases / two raw-evidence stores.** Only upstream DuckDB + Parquet.
- **Two intelligence stores / two intelligence formats.** Only
  `data/intelligence/records/` with the one schema.
- **localStorage CRUD as a source of truth.** The frontend is a renderer; any
  local overlay is a per-session display convenience, never authority.
- **LLM-decided changes.** AI (Antigravity or any model) may explain a detected
  change but may never decide whether a change happened, and no AI prose is
  written into the raw change authority.
- **Writing AI prose into raw snapshots / the raw change authority.**
- **Inventing the ~55 competitors.** `config/competitors.yaml` stays empty until
  the authoritative list is supplied.

## Validation note

`tests/test_radar_authority.py` checks that the frontend does not hardcode a
competitor list. The frontend must derive competitors from the compiled artifact,
whose upstream origin is `config/competitors.yaml`. This test is the guardrail for
the "frontend = renderer, no second competitor truth" rule above.

No command output is claimed here — see [CONTRIBUTING.md](../CONTRIBUTING.md) for
the quality gates that must be run locally.
