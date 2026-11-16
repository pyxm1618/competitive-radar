# ADR 0005 - Antigravity file protocol over an in-app LLM pipeline

- **Status:** Accepted
- **Date:** 2026-11-16

## Context

V1 needs an "intelligence" layer that explains *why a detected competitor change
matters* to the Xiaoshuyin (小树荫) product owner. The upstream foundation
(`yassnemo/compete`, imported verbatim at `ebc32b20c...`) already provides a
deterministic pipeline: collection, content-addressed snapshots, a deterministic
snapshot diff (`pipeline/detect/change.py`), Parquet raw layer, DuckDB warehouse,
dbt staging → marts, static JSON export, and a Next.js frontend (see ADRs
0001–0004).

Constraints that shape this decision:

- **Reuse first, modify minimally.** No second crawler, no second diff engine,
  no second database, no second change-detection authority.
- **No paid LLM API.** No `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`,
  Anthropic API, or any model key may be required for the normal workflow; V1
  CI (GitHub Actions) must never fail for a missing model key.
  `COMPETE_LLM_PROVIDER` defaults to `mock`, and the upstream
  Gemini/Groq/Ollama/mock extraction code is retained for compatibility only.
- **Deterministic change authority.** ADR 0002 already establishes that the LLM
  never decides whether something changed. V1 must not weaken that guarantee.
- **Internal research tool.** Analysis is for product design decisions, is
  human-reviewed (`human_review_status`), and does not need to be fully
  unattended in V1.
- **Antigravity exists as an external agent** with a verified workspace
  convention (`.agents/skills/<name>/SKILL.md`, `.agents/rules/`,
  `.agents/workflows/`). It is not a web-app runtime dependency.

## Decision

Connect an **external Antigravity agent to the deterministic upstream pipeline
via a deterministic file protocol**, with **no paid LLM API**. AI is used only to
*explain* changes that the pipeline has **already detected**; it **never decides
whether a change happened**.

The protocol is a fixed, human-triggered flow:

```
Collection → Snapshot → Diff → Pending Intelligence Queue → Antigravity → Intelligence Output → Frontend
```

1. `radar collect` (thin wrapper) runs upstream collection, snapshot, and the
   deterministic diff. `radar prepare` turns detected changes into
   `data/intelligence/pending/<change_id>.json`. Both **never call a model**.
2. A **human** opens Antigravity and invokes the workspace skill
   `competitor-intelligence` (`.agents/skills/competitor-intelligence/SKILL.md`).
   Antigravity is external and human-triggered — not a runtime dependency of
   the CLI, CI, or the web app.
3. The agent reads only authoritative inputs (pending queue, JSON Schemas,
   upstream snapshots/parquet, manual evidence, `config/competitors.yaml`,
   `config/topics.yaml`, `context/xiaoshuyin.md`, prior records) and writes only
   to `data/intelligence/records/<intelligence_id>.json` (one record per
   `change_id`) and, when evidence is insufficient,
   `data/intelligence/research/<request_id>.json`.
4. Records validate against `data/intelligence/schema/*.schema.json`; `radar
   validate` and `radar build` consume them. `radar build` compiles
   `web/public/radar-static/radar.json` for the read-only Next.js renderer
   (four entries: Radar, Topics, Competitors, Evidence) deployed to Vercel.
5. Impact and Confidence are independent judgements; missing evidence lowers
   Confidence and creates a manual research request. The agent never fabricates
   screenshots, sources, features, or competitor facts, and stops at
   "READY FOR INDEPENDENT RE-AUDIT" (no merge).

One competitor authority (`config/competitors.yaml`, intentionally empty in V1 —
the real ~55-competitor list has not been supplied), one topic authority, one
raw-evidence authority, one change authority, one intelligence authority. The
frontend is a renderer only.

## Consequences

**Positive**
- Zero paid-model cost and zero key management; CI and the CLI never need a
  model key. `COMPETE_LLM_PROVIDER=mock` is the default path.
- The deterministic change authority (ADR 0002) is preserved and strengthened:
  AI explains, it does not detect or decide.
- Human-triggered analysis matches V1's internal, human-reviewed nature; every
  record carries `human_review_status`.
- Reuse-first is honoured: no second crawler, diff engine, database, competitor
  registry, or intelligence store. The integration is plain files and a thin
  CLI wrapper.
- The file protocol is auditable, versionable, and works fully offline; the
  external agent is swappable without touching the pipeline or frontend.
- Static-first deployment (ADR 0004) remains the production path: no backend,
  no API keys, no long-running FastAPI server.

**Negative / trade-offs**
- Analysis is not fully unattended: a human must open Antigravity and invoke the
  skill. Accepted for V1; automation is a later concern.
- Intelligence quality depends on a human re-audit; records are not
  auto-merged and must not be declared MERGE SAFE by the agent.
- The protocol relies on disciplined path conventions (one format, one record
  per `change_id`); `radar validate` and `tests/test_radar_authority.py` are the
  guardrails rather than a database constraint.
- With `config/competitors.yaml` intentionally empty, there are no real
  competitors to collect or analyze until the authoritative ~55 list is
  supplied. The sample fixture is tests/demo only.

## Alternatives considered

- **In-app LLM extraction as the default path (upstream Gemini/Groq/Ollama).**
  Rejected: it requires model keys / a paid API for the normal workflow, would
  make CI fail on missing keys, and contradicts the no-paid-LLM-API hard rule.
  The code is retained for compatibility only, with `mock` as the default.
- **Fully autonomous agent that decides what to scrape and whether a change
  matters.** Rejected per ADR 0003 (reliability, cost, debuggability) and
  because it would break the deterministic change authority.
- **Second database / second raw-evidence store for AI outputs.** Rejected:
  violates the single-authority rule; a second store would become a competing
  source of truth. File-based records under `data/intelligence/` are enough.
- **Storing intelligence in localStorage / the frontend.** Rejected: the
  frontend is a read-only renderer; localStorage would create a second
  competitor/intelligence truth that is not versionable or authoritative.
- **A realtime AI chat in the frontend.** Rejected: out of scope for V1 and
  would reintroduce a runtime model dependency.
