# Antigravity Workflow (deterministic file protocol)

This document is the full contract for the V1 intelligence step. It connects the
deterministic upstream pipeline to an **external** intelligence agent
(Antigravity) through a **deterministic file protocol** — no network calls, no
paid model API, no runtime coupling.

```
Collection → Snapshot → Diff → Pending Intelligence Queue → Antigravity → Intelligence Output → Frontend
```

**Antigravity is human-triggered and is NOT a web-app runtime dependency.** The
CLI, GitHub Actions, and the Next.js frontend never invoke it and never require
it. A human opens Antigravity and asks it to analyze the pending queue; the
integration is entirely through files on disk.

## Antigravity workspace convention (verified)

| Artifact | Location | Format |
|---|---|---|
| Workspace skills | `.agents/skills/<name>/SKILL.md` | YAML frontmatter with `name` and required `description` |
| Workspace rules | `.agents/rules/` | markdown rules |
| Workflows | `.agents/workflows/` | markdown workflows |

`.agents/skills` is the current default; `.agent/skills` is the legacy
backward-compatible location. V1 uses `.agents/`.

The V1 intelligence skill is
[`.agents/skills/competitor-intelligence/SKILL.md`](../.agents/skills/competitor-intelligence/SKILL.md).
The always-on authority rule is
[`.agents/rules/competitive-radar-authority.md`](../.agents/rules/competitive-radar-authority.md).
The human-triggered workflow is
[`.agents/workflows/analyze-pending.md`](../.agents/workflows/analyze-pending.md).

## Exact inputs the Agent MAY read

The Antigravity agent may read **only** these authoritative inputs:

| Input | Path | Purpose |
|---|---|---|
| Pending queue (the work list) | `data/intelligence/pending/*.json` | One file per detected change; the trigger for analysis. |
| JSON Schemas | `data/intelligence/schema/*.schema.json` | The validation contract for outputs. |
| Raw evidence | upstream snapshots (`raw.raw_pages` in DuckDB) and `data/raw/*.parquet` | Ground truth for what changed. |
| Manual evidence | `evidence/manual/<evidence_id>/metadata.json` + asset files in the same folder | Supplementary human-captured evidence. |
| Competitor authority | `config/competitors.yaml` | The only competitor registry (intentionally empty in V1). |
| Topic taxonomy | `config/topics.yaml` | The only allowed `topic_ids[]` (13 topics). |
| Xiaoshuyin context | `context/xiaoshuyin.md` | Relevance guardrails. |
| Prior intelligence | `data/intelligence/records/` | Only when needed (e.g. to avoid duplicate `change_id`, keep consistency). |

The agent must **not** read or trust any second competitor list, any hardcoded
frontend list, or any localStorage overlay.

## Exact outputs the Agent MAY write

The agent writes **only** to these two locations:

| Output | Path | Rule |
|---|---|---|
| Intelligence record | `data/intelligence/records/<intelligence_id>.json` | **One** record per `change_id`. Duplicate change references are rejected. |
| Manual research request | `data/intelligence/research/<request_id>.json` | Only when evidence is insufficient (see below). |

The agent must **never** write to:
- `config/` (competitor/topic authority),
- `web/` (the renderer),
- raw snapshots / `data/raw/` / `raw.raw_pages` / DuckDB warehouse,
- `data/intelligence/pending/` (the queue),
- `evidence/` (manual evidence).

## JSON Schemas

Validation schemas live at `data/intelligence/schema/*.schema.json`. The
intelligence record must validate against
`data/intelligence/schema/intelligence-record.schema.json`. `radar validate`
checks records against these schemas; a record that does not validate is not
accepted by `radar build`.

## Step-by-step runbook

Analysis is **human-triggered**. There is no scheduled auto-analysis in V1.

1. **Detect + queue (no AI).**
   ```bash
   radar collect     # sync competitors -> collect -> snapshot -> deterministic diff
   radar prepare     # detected changes -> normalize -> generate/update pending queue
   ```
   Expected output: `data/intelligence/pending/<change_id>.json` for each
   detected change. `radar collect` / `radar prepare` **never call a model**.

2. **Open Antigravity** in this repository (the `.agents/` workspace artifacts
   are discovered automatically).

3. **Invoke the `competitor-intelligence` skill** — e.g. run the
   `analyze-pending` workflow, or ask Antigravity to "analyze the pending
   competitor changes using the competitor-intelligence skill". The skill
   reads the inputs above, applies the 15 rules (evidence-first, noise removal,
   topic classification, independent Impact/Confidence, mechanism, Xiaoshuyin
   relevance, decision, provenance, no fabrication, insufficient-evidence
   handling), and writes one record per `change_id`.

4. **Validate (CLI).**
   ```bash
   radar validate
   ```
   Expected output: all intelligence records validate against
   `data/intelligence/schema/*.schema.json`; duplicate `change_id` references are
   rejected.

5. **Build (CLI).**
   ```bash
   radar build       # validate -> dbt build -> static JSON -> frontend build
   ```
   Expected output: `web/public/radar-static/radar.json` plus the built Next.js
   app. Or `radar demo-build` to compile from `examples/` fixtures only without
   writing any authority.

The skill stops at **"READY FOR INDEPENDENT RE-AUDIT"**. It must not declare
MERGE SAFE and must not merge (no git add / commit / push).

## How to create manual research requests

When evidence is insufficient, the agent **lowers `confidence`** and writes a
manual research request:

- Path: `data/intelligence/research/<request_id>.json`.
- Template:
  `.agents/skills/competitor-intelligence/resources/manual-research-template.json`.
- Fields: `research_question`, `why_needed`, `suggested_steps`,
  `required_evidence`.
- The intelligence record should point at the gap in `why_it_matters` and carry
  `confidence: low` (or `medium` at most). A human later performs the research,
  adds manual evidence under `evidence/manual/<evidence_id>/`, and the change may
  be re-analyzed.

## How missing evidence must lower confidence

Confidence reflects **how well the evidence supports the interpretation**, not
how important the topic feels. The rule from `context/xiaoshuyin.md` is explicit:
**low evidence means low confidence, even when the topic feels important.**

- Evidence located and clearly supports the change → `confidence: high`.
- Partial / ambiguous evidence → `confidence: medium`.
- Missing, thin, or unlocatable evidence → `confidence: low` **and** a manual
  research request.
- `impact` and `confidence` are **independent**: `impact: high` /
  `confidence: low` is a valid combination (usually `decision: investigate`).
  Never lower `impact` just because evidence is thin — lower `confidence`
  instead.

Never fabricate screenshots, sources, features, or competitor facts to fill an
evidence gap.

## No paid LLM API

V1 uses **NO PAID LLM API**. No `OPENAI_API_KEY`, `GOOGLE_API_KEY`,
`GROQ_API_KEY`, Anthropic API, or any model key is required for the normal
workflow. The Antigravity analysis is performed by the external agent that a
human invokes; the CLI and CI never call a model. GitHub Actions runs only
non-AI monitoring and must never fail for a missing model key.

## Decision meanings (quick reference)

| Decision | Meaning |
|---|---|
| `act` | enough evidence + worth a product decision now |
| `investigate` | potentially high impact but needs more research |
| `watch` | no action now but keep observing |
| `ignore` | noise or irrelevant |

Impact / Confidence / Relevance are each one of `high` / `medium` / `low`.
Impact and Confidence are independent.
