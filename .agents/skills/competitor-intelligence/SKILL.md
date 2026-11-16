---
name: competitor-intelligence
description: >-
  Turns authoritative pending competitor changes into validated intelligence
  records for the Xiaoshuyin Competitive Radar. It is triggered when a human
  operator, after running `radar prepare`, opens Antigravity and asks the agent
  to analyze the pending competitor changes; the skill reads the pending queue
  and evidence, judges impact/confidence/relevance independently, and writes one
  schema-validated record per change_id without calling any paid model API.
---

# Competitor Intelligence Skill

## Purpose and scope

This skill turns **authoritative pending competitor changes** (`data/intelligence/pending/*.json`)
into **validated intelligence records** (`data/intelligence/records/<intelligence_id>.json`)
for the **Xiaoshuyin (小树荫) Competitive Radar V1**. The question each record
answers is *值得你看的变化?* — is this already-detected change worth the product
owner's attention, and why?

The integration is a **deterministic file protocol**:

```
Collection → Snapshot → Diff → Pending Intelligence Queue → Antigravity → Intelligence Output → Frontend
```

- **Antigravity is an EXTERNAL, human-triggered intelligence agent — NOT a
  web-app runtime dependency.** The CLI, GitHub Actions, and the Next.js frontend
  never invoke it and never require it. A human opens Antigravity and invokes
  this skill.
- **AI cannot decide whether a change happened.** Change detection is a
  deterministic comparison between collected snapshots (upstream
  `pipeline/detect/change.py`). This skill only *explains* changes that the
  pipeline already detected and wrote to the pending queue.
- **V1 uses NO PAID LLM API.** This skill must **never call a model API** and must
  never require `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, an Anthropic
  API, or any model key. The analysis is done by the external agent a human
  invokes; no key is needed for the normal workflow.
- The goal (per `context/xiaoshuyin.md`) is to judge whether a competitor change
  has **meaning for Xiaoshuyin's product design** — not to write competitor
  profiles.

---

## The 15 requirements

These are the complete, explicit rules of this skill, numbered to match the V1
contract.

### 1. INPUT — read ONLY authoritative sources

Read **only** these inputs. Never read or trust a second competitor list, a
hardcoded frontend list, or a localStorage overlay.

| Input | Exact path | Why |
|---|---|---|
| Pending queue (the work list) | `data/intelligence/pending/*.json` | One file per detected change; the trigger. |
| JSON Schemas | `data/intelligence/schema/*.schema.json` | The validation contract for outputs. |
| Raw evidence | upstream snapshots (`raw.raw_pages` in DuckDB) + `data/raw/*.parquet` | Ground truth for what changed. |
| Manual evidence | `evidence/manual/<evidence_id>/metadata.json` + asset files in the same folder | Supplementary, read-only input. |
| Competitor authority | `config/competitors.yaml` | The only competitor registry (intentionally `competitors: []` in V1). |
| Topic taxonomy | `config/topics.yaml` | The only allowed `topic_ids[]`. |
| Xiaoshuyin context | `context/xiaoshuyin.md` | Relevance guardrails (requirement 10). |
| Prior intelligence | `data/intelligence/records/` | Only when needed (duplicate check, consistency). |

### 2. OUTPUT — write ONLY to the allowed paths

Write **only** to:

| Output | Exact path | Rule |
|---|---|---|
| Intelligence record | `data/intelligence/records/<intelligence_id>.json` | **One** record per `change_id`. |
| Manual research request | `data/intelligence/research/<request_id>.json` | Only when evidence is insufficient (requirement 14). |

**Never write to:** `config/`, `web/`, raw snapshots, `data/raw/`,
`raw.raw_pages` / the DuckDB warehouse, `data/intelligence/pending/`,
`evidence/`, or any other path. The CLI owns those.

### 3. Check evidence first

Before any judgement, open the pending file and locate **every referenced
snapshot / parquet / manual-evidence asset**. Confirm the evidence actually
exists and supports the detected change. If evidence cannot be located, treat it
as insufficient (requirement 14). Use `resources/evidence-first-checklist.md`.
Never start from a conclusion and look for evidence afterwards.

### 4. Remove noise

Discard noise — timestamp flips, rotating banners, nonces, layout-only edits,
duplicate announcements, tracking-parameter changes, cosmetic copy. A noise
change gets `decision: ignore` with `relevance: low` and no substantive
`mechanism` / `why_it_matters`; it must **not** be inflated into a finding and
must **not** be fabricated into substance. Removing noise is a classification
decision (**ignore**), **not** a change-detection decision — you may never
retroactively alter whether a change was recorded.

### 5. Classify against `config/topics.yaml` only

Assign `topic_ids[]` **only** from the 13 ids in `config/topics.yaml`:
`problem-discovery`, `assessment`, `diagnosis`, `ai-conversation`,
`action-plan`, `family-collaboration`, `child-participation`, `tracking`,
`follow-up`, `reflection`, `report`, `expert-service`, `monetization`. Never
invent a topic id. `topic_ids[]` may be empty if no topic applies.

### 6. Judge Impact

`impact` ∈ {`high`, `medium`, `low`}: **how much the change would matter to
Xiaoshuyin's product design if it is real**. Impact is about the magnitude of
the consequence, **not** about evidence quality.

### 7. Judge Confidence

`confidence` ∈ {`high`, `medium`, `low`}: **how well the available evidence
supports the interpretation**. Confidence is about evidence quality, **not**
about importance. Missing or thin evidence ⇒ low confidence (requirement 14).

### 8. Keep Impact / Confidence separate (with explicit examples)

They are **independent axes**. Never force them to match; never lower `impact`
just because evidence is thin — lower `confidence` instead.
- `impact: high` / `confidence: low` is **legal** — potentially big, thinly
  evidenced → usually `decision: investigate`.
- `impact: low` / `confidence: high` is **legal** — well-evidenced but trivial →
  usually `decision: watch` or `ignore`.
- `impact: high` / `confidence: high` — usually `decision: act`.
- `impact: low` / `confidence: low` — usually `decision: ignore` or `watch`.

### 9. Extract the underlying product mechanism

In `mechanism`, describe the **underlying product mechanism** the change
exercises (e.g. a sequenced action plan, an AI conversational intake, a shared
family view, a follow-up loop), not a marketing description of the feature. The
goal is to judge meaning for Xiaoshuyin's design, not to write a competitor
profile.

### 10. Judge relevance to Xiaoshuyin using `context/xiaoshuyin.md`

`relevance` ∈ {`high`, `medium`, `low`} and the prose `xiaoshuyin_relevance`
must be grounded in the capability areas and guardrails in
`context/xiaoshuyin.md`. Answer: *does this mechanism matter to Xiaoshuyin, and
why?* **Never invent a Xiaoshuyin feature, roadmap item, or product decision.**
Low evidence means low confidence even when the topic feels important.

### 11. Give one decision with the exact definitions

`decision` is exactly one of `act` / `investigate` / `watch` / `ignore`:

| `decision` | Exact definition |
|---|---|
| `act` | enough evidence + worth a product decision now |
| `investigate` | potentially high impact but needs more research |
| `watch` | no action now but keep observing |
| `ignore` | noise or irrelevant |

See the **Decision table** below for the impact/confidence mapping.

### 12. Preserve provenance

Every record must carry `change_id`, and its `evidence[]` must reference the
snapshot refs, the original URL, and the pending file path. Do not strip
identifiers. Each `evidence[]` entry references a concrete `evidence_id` (a
manual-evidence id or snapshot id), plus `url`, `snapshot_ref`, and
`pending_file` where applicable. Set `intelligence_id` (unique) and
`schema_version`. Provenance is what makes a record independently re-auditable.

### 13. NEVER fabricate screenshots, sources, features, or competitor facts

If it is not in the evidence, do not state it. No invented competitor names,
URLs, quotes, metrics, screenshots, or feature claims. **Do not invent the ~55
competitors** — `config/competitors.yaml` is authoritative and intentionally
empty in V1; the sample fixture is tests/demo only. Never fabricate evidence to
fill a gap.

### 14. When evidence is insufficient, lower Confidence and create a manual research request

When evidence is missing, thin, or ambiguous, **explicitly set `confidence:
low`** (or `medium` at most), state the gap in `why_it_matters` / the record, and
create a manual research request at
`data/intelligence/research/<request_id>.json` using
`resources/manual-research-template.json` (fields: `request_id`,
`research_question`, `why_needed`, `suggested_steps`, `required_evidence`).
`required_evidence` is a list of `{ "label", "required", "satisfied" }` objects;
`request_id` is deterministic (`"req-" + sha256(change_id + "|" +
research_question)[:20]`). Low evidence means low confidence even when the topic
feels important.

### 15. Do not modify raw snapshots; do not modify competitor authority unless the task explicitly requires it

Never edit `config/competitors.yaml`, `config/topics.yaml`, `data/raw/`,
`raw.raw_pages`, snapshots, the DuckDB warehouse,
`data/intelligence/pending/`, or `evidence/` — **unless the human operator's
task explicitly and specifically requires that change**. Raw snapshots are
read-only. The intelligence workflow writes only to the two OUTPUT paths
(requirement 2).

---

## Additional mandatory constraints

These apply in addition to the 15 requirements above:

- **One intelligence record per `change_id`.** Before writing, check
  `data/intelligence/records/` for an existing record with the same `change_id`.
  **Duplicate change references are rejected** — do not write a second record.
- **Validate** every record against
  `data/intelligence/schema/intelligence-record.schema.json`.
- **Run `radar validate` after writing.**
- **Never call a model API.** No `OPENAI_API_KEY`, `GOOGLE_API_KEY`,
  `GROQ_API_KEY`, Anthropic API, or any model key. Antigravity (the external,
  human-triggered agent) performs the analysis; this skill adds no paid LLM API
  dependency.
- **Stop at "READY FOR INDEPENDENT RE-AUDIT".** End the run with that exact
  line. Do **not** declare "MERGE SAFE", do **not** merge, and do **not** run
  git add / commit / push. Records carry `human_review_status` (e.g.
  `unreviewed`) and require an independent human re-audit.
- **Report commands actually run.** Never claim a validation, test, or command
  passed unless it was observed.

## Impact and Confidence are independent

`impact` (how much it would matter if true) and `confidence` (how well the
evidence supports it) are **separate**. This is a hard rule from
`context/xiaoshuyin.md`.

| Impact | Confidence | Legal? | Typical decision |
|---|---|---|---|
| high | low | **legal** | investigate (big but thinly evidenced) |
| low | high | **legal** | watch / ignore (well-evidenced but trivial) |
| high | high | legal | act |
| low | low | legal | ignore / watch |

When evidence is weak, lower **confidence**, not impact. Evidence quality never
changes how much the change *would* matter.

## Decision table

| `decision` | Exact definition | When |
|---|---|---|
| `act` | enough evidence + worth a product decision now | `impact: high` + `confidence: high`, clearly relevant to Xiaoshuyin |
| `investigate` | potentially high impact but needs more research | `impact: high` + `confidence: low/medium`; create a manual research request |
| `watch` | no action now but keep observing | `impact: low/medium`, `confidence: high`, relevance not yet decisive |
| `ignore` | noise or irrelevant | noise (requirement 4), `relevance: low`, or nothing material |

`relevance` is a third independent judgement ({high, medium, low}) grounded in
`context/xiaoshuyin.md`.

## Compact record template

Placeholders below must be replaced with real values. `intelligence_id` is
**deterministic**, never chosen by the agent:

```
intelligence_id = "int-" + sha256("intelligence|" + change_id).hexdigest()[:24]
```

That is enforced by `radar validate`; a free-form or random id is rejected.

```json
{
  "schema_version": 1,
  "intelligence_id": "int-<24 hex chars derived from change_id as above>",
  "change_id": "<change_id from the pending file>",
  "competitor_id": "<id that exists in config/competitors.yaml>",
  "date": "YYYY-MM-DD",
  "summary": "<one or two sentences, evidence-only>",
  "topic_ids": ["<id from config/topics.yaml>"],
  "change_type": "updated",
  "impact": "high",
  "confidence": "low",
  "relevance": "medium",
  "decision": "investigate",
  "xiaoshuyin_relevance": "<why this mechanism matters to Xiaoshuyin, grounded in context/xiaoshuyin.md>",
  "mechanism": "<underlying product mechanism, not marketing copy>",
  "why_it_matters": "<meaning for Xiaoshuyin product design; state evidence gaps here>",
  "evidence": [
    { "evidence_id": "<existing evidence_id from pending.evidence[] or evidence/manual/>", "role": "after", "note": "<optional>" }
  ],
  "human_review_status": "unreviewed",
  "analyst": "Antigravity competitor-intelligence",
  "provenance": {
    "pending_file": "data/intelligence/pending/<change_id>.json",
    "url": "<original URL>",
    "snapshot_after": "<after snapshot id>",
    "snapshot_before": "<before snapshot id, or empty string>"
  }
}
```

`evidence[]` items are `EvidenceRef` objects: `evidence_id` + `role`
(`before` / `after` / `supporting`) + optional `note`. Raw URL / snapshot
references live in `provenance` and in the pending item, **not** inside
`evidence[]`. A fully schema-valid, clearly-marked instance is at
`resources/intelligence-template.json`.

## Validation and stop condition

1. Write records to `data/intelligence/records/<intelligence_id>.json` (one per
   `change_id`).
2. Create `data/intelligence/research/<request_id>.json` where evidence is
   insufficient.
3. Validate against `data/intelligence/schema/intelligence-record.schema.json`.
4. Run `radar validate`.
5. Output exactly: **READY FOR INDEPENDENT RE-AUDIT** — no MERGE SAFE, no merge,
   no git commands.
6. Report the commands actually run; do not claim unchecked results.

`radar build` (validate → dbt build → `web/public/radar-static/radar.json` →
frontend build) and the static Vercel deploy are downstream CLI steps a human
runs after the independent re-audit. This skill does not run them.

## Resources

- `resources/intelligence-template.json` — a valid, clearly-marked sample record.
- `resources/evidence-first-checklist.md` — evidence-first checks (requirements 3 / 13).
- `resources/manual-research-template.json` — manual research request (requirement 14).

## Also see

- `docs/ANTIGRAVITY_WORKFLOW.md` — the full deterministic file protocol.
- `docs/AUTHORITY.md` — the single-authority model and prohibited list.
- `../../rules/competitive-radar-authority.md` — always-on workspace rule.
- `../../workflows/analyze-pending.md` — the human-triggered runbook.
- `context/xiaoshuyin.md` — relevance guardrails.
- `config/topics.yaml` — the only allowed `topic_ids[]`.
