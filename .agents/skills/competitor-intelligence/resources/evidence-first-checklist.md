# Evidence-first checklist

Work through this checklist for **every** pending change before any judgement.
If any box is unchecked, the evidence is insufficient: lower `confidence` and
create a manual research request (requirement 14).

- [ ] Opened `data/intelligence/pending/<change_id>.json` and read `change_id`,
      `competitor_id`, snapshot refs, and the original URL.
- [ ] Located every referenced snapshot / `data/raw/*.parquet` file; confirmed it
      exists and is readable.
- [ ] Located each `evidence/manual/<evidence_id>/metadata.json` (if referenced)
      and its asset files in the same folder.
- [ ] Confirmed the evidence actually supports the detected change (no inference
      beyond what the evidence shows).
- [ ] Checked `config/competitors.yaml` for the `competitor_id`; did **not**
      invent, substitute, or silently mutate a competitor outside the confirmed
      55-object authority.
- [ ] Checked `data/intelligence/records/` for an existing record with the same
      `change_id` (one record per change_id; duplicates rejected).
- [ ] Read `data/intelligence/schema/intelligence-record.schema.json` for the
      output contract.
- [ ] Read `config/topics.yaml` and `context/xiaoshuyin.md` for classification
      and relevance guardrails.
- [ ] Separated **impact** (magnitude if true) from **confidence** (evidence
      quality); thin evidence lowers confidence, never impact.
- [ ] No fabricated screenshots, sources, features, URLs, metrics, or competitor
      facts; every prose claim traces to located evidence.
- [ ] No writes outside `data/intelligence/records/` and
      `data/intelligence/research/`; raw snapshots and `config/` untouched.
- [ ] No model API called; no model key required.
- [ ] Record validates against the schema and `radar validate` is run.
- [ ] Ended with exactly **READY FOR INDEPENDENT RE-AUDIT** (no merge, no git).
