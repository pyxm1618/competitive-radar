# Manual evidence

For surfaces the automatic collectors cannot reach:

- iOS / Android apps
- WeChat Mini Programs (微信小程序)
- login-walled flows
- onboarding that needs a human to click through
- CAPTCHA / verification-code flows
- manual screenshots and manually recorded key product flows

## Directory contract

One folder per evidence item:

```
evidence/manual/<evidence_id>/
├── metadata.json     # pipeline.radar.contracts.ManualEvidence
└── <asset files>     # screenshots / recordings / pdfs / notes
```

`metadata.json` fields (see `data/intelligence/schema/manual-evidence.schema.json`):

| Field | Meaning |
|---|---|
| `evidence_id` | stable id, pattern `evm-[a-z0-9_-]+`; equals the folder name |
| `competitor_id` | must exist in `config/competitors.yaml` |
| `captured_at` | ISO-8601 timestamp |
| `evidence_type` | `manual_screenshot` / `manual_recording` / `manual_note` / `pdf_document` / `screenshot` |
| `title`, `description` | what this artefact shows; never claim more than the artefact shows |
| `source_label` | e.g. `iOS App (manual)`, `WeChat Mini Program (manual)` |
| `url` | original URL when one exists (optional if `files` is non-empty) |
| `files` | filenames inside this folder; at least one file or a `url` is required |
| `topic_ids` | ids from `config/topics.yaml` |
| `related_change_id` | optional link back to `data/intelligence/pending/` |
| `verification_state` | `unverified` / `verified` / `missing` / `demo_placeholder` |
| `captured_by` | human or agent that produced the artefact |

`radar build` copies referenced assets into `web/public/evidence/<evidence_id>/`
so the static frontend can display them. A metadata file that references a
missing asset is reported as `verification_state = missing`; no asset is ever
fabricated or silently substituted.

## Example (clearly-labelled sample fixtures only)

`examples/evidence/manual/` contains SAMPLE fixtures. They are not real
evidence and are never used by the authoritative build.

## Adding real manual evidence

1. Create `evidence/manual/<evidence_id>/` and put the real screenshots/files in it.
2. Write `metadata.json` following the schema; do not invent a URL or a feature.
3. Reference `evidence_id` from the intelligence record's `evidence[]`.
4. Run `radar validate && radar build`.
