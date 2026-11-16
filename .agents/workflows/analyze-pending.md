---
name: analyze-pending
description: Human-triggered workflow that turns pending competitor changes into validated intelligence records using the competitor-intelligence skill, then validates and builds the static frontend.
---

# Workflow: analyze-pending

**Human-triggered.** This workflow is NOT run by CI, by GitHub Actions, or by the
web app. A person starts it after the non-AI monitoring steps have produced a
pending queue. Antigravity is an external intelligence agent, not a runtime
dependency. AI explains changes the deterministic diff already detected — it
never decides whether a change happened.

Prerequisite reading: `docs/ANTIGRAVITY_WORKFLOW.md`,
`.agents/skills/competitor-intelligence/SKILL.md`,
`.agents/rules/competitive-radar-authority.md`.

## Steps

### 1. Produce the pending queue (no AI)

```bash
radar collect     # sync competitors -> collect -> snapshot -> deterministic diff (no AI)
radar prepare     # detected changes -> normalize -> generate/update pending queue (no AI)
radar status
```

**Expected output:** `data/intelligence/pending/<change_id>.json` for each
detected change. No model is called. (GitHub Actions runs these non-AI steps
only and must never fail for a missing model key.)

If `config/competitors.yaml` is `competitors: []` (the V1 default), there may be
no pending files — that is expected; the real ~55-competitor list has not been
supplied. Never invent competitors to create work.

### 2. Invoke the skill (human-triggered, in Antigravity)

Open Antigravity in this repository and invoke the **competitor-intelligence**
skill (`../skills/competitor-intelligence/SKILL.md`), asking it to analyze the
pending changes. The skill:

- reads only authoritative inputs (pending queue, JSON Schemas, raw
  snapshots/parquet, manual evidence, `config/competitors.yaml`,
  `config/topics.yaml`, `context/xiaoshuyin.md`, prior records),
- checks evidence first, removes noise, classifies topics, judges Impact and
  Confidence independently, extracts the mechanism, judges Xiaoshuyin
  relevance, assigns one decision, preserves provenance, never fabricates,
- lowers Confidence and creates a manual research request when evidence is
  insufficient.

**Expected output:** one intelligence record per `change_id` at
`data/intelligence/records/<intelligence_id>.json`, and (when evidence is
insufficient) `data/intelligence/research/<request_id>.json`. No writes to
`config/`, `web/`, raw snapshots, `data/raw/`, `evidence/`, or
`data/intelligence/pending/`.

### 3. Validate (CLI)

```bash
radar validate
```

**Expected output:** every record validates against
`data/intelligence/schema/intelligence-record.schema.json`; duplicate
`change_id` references are rejected.

### 4. Build (CLI)

```bash
radar build       # validate -> dbt build -> web/public/radar-static/radar.json -> frontend build
```

**Expected output:** `web/public/radar-static/radar.json` plus the built Next.js
app (four read-only entries: Radar, Topics, Competitors, Evidence).
`radar demo-build` may be used to compile from `examples/` fixtures only,
without writing any authority.

## Commands summary

| Step | Command | AI? |
|---|---|---|
| Monitor | `radar collect`, `radar prepare`, `radar status` | No |
| Analyze | Antigravity `competitor-intelligence` skill | Human-triggered, external |
| Validate | `radar validate` | No |
| Build | `radar build` (or `radar demo-build`) | No |
| Combined no-AI | `radar update` (collect + prepare + build) | No |

## Stop condition

The skill stops at **"READY FOR INDEPENDENT RE-AUDIT"**.

- The skill must **not** declare "MERGE SAFE".
- The skill must **not** merge or run git add / commit / push.
- Intelligence records carry `human_review_status` and require human review;
  a human performs the independent re-audit and decides whether to merge.

Do not claim any command passed or any validation succeeded unless it was
actually run and observed.
