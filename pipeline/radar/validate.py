"""Validation of authoritative intelligence output.

`radar validate` and `radar build` both gate on this module. It enforces the
hard rules from the V1 contract:

  * schema validation (invalid impact / confidence / decision are rejected);
  * evidence-first (a conclusion with no evidence reference is rejected);
  * provenance (a record must reference an authoritative pending change);
  * unknown competitor / unknown topic are rejected;
  * duplicate change references are rejected;
  * deterministic intelligence_id;
  * unresolved evidence forces confidence = low.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from pipeline.radar.contracts import (
    Confidence,
    IntelligenceRecord,
    TopicsFile,
    stable_intelligence_id,
)
from pipeline.radar.manual import load_manual_evidence
from pipeline.radar.paths import (
    COMPETITORS_PATH,
    EXAMPLE_COMPETITORS_PATH,
    PENDING_DIR,
    RECORDS_DIR,
    TOPICS_PATH,
)
from pipeline.radar.pending import load_pending


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records: list[IntelligenceRecord] = field(default_factory=list)
    files_read: int = 0
    unresolved_evidence: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)


def load_topics(path: Path | None = None) -> TopicsFile:
    p = path or TOPICS_PATH
    with p.open("r", encoding="utf-8") as fh:
        return TopicsFile.model_validate(yaml.safe_load(fh) or {})


def load_competitor_ids(path: Path | None = None) -> set[str]:
    p = path or COMPETITORS_PATH
    with p.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    rows = data.get("competitors") or []
    return {str(row["id"]) for row in rows}


def load_records(directory: Path | None = None) -> tuple[list[IntelligenceRecord], list[str], int]:
    """Return (valid records, parse errors, files read)."""
    root = directory or RECORDS_DIR
    records: list[IntelligenceRecord] = []
    errors: list[str] = []
    count = 0
    if not root.exists():
        return records, errors, count
    for file in sorted(root.glob("*.json")):
        count += 1
        try:
            raw = json.loads(file.read_text(encoding="utf-8"))
            records.append(IntelligenceRecord.model_validate(raw))
        except (json.JSONDecodeError, ValidationError, OSError) as exc:
            errors.append(f"{file.name}: {exc}")
    return records, errors, count


def _known_evidence_ids(pending_dir: Path, manual_root: Path | None = None) -> set[str]:
    ids: set[str] = set()
    for item in load_pending(pending_dir):
        ids.update(e.evidence_id for e in item.evidence)
    for item in load_manual_evidence(manual_root):
        ids.add(item.evidence_id)
    return ids


def validate_intelligence(
    *,
    records_dir: Path | None = None,
    pending_dir: Path | None = None,
    competitors_path: Path | None = None,
    topics_path: Path | None = None,
    manual_root: Path | None = None,
) -> ValidationReport:
    """Validate all authoritative intelligence records and their references."""
    report = ValidationReport()
    records, parse_errors, count = load_records(records_dir)
    report.records = records
    report.files_read = count
    for err in parse_errors:
        report.add_error(err)

    competitor_ids = load_competitor_ids(competitors_path or COMPETITORS_PATH)
    topics = load_topics(topics_path)
    topic_ids = topics.topic_ids
    pending = load_pending(pending_dir or PENDING_DIR)
    change_ids = {p.change_id for p in pending}
    known_evidence = _known_evidence_ids(pending_dir or PENDING_DIR, manual_root)

    seen_change: dict[str, str] = {}
    seen_id: dict[str, str] = {}
    for record in records:
        label = f"{record.intelligence_id} ({record.change_id})"

        expected = stable_intelligence_id(record.change_id)
        if record.intelligence_id != expected:
            report.add_error(f"{label}: non-deterministic intelligence_id, expected {expected}")

        if record.competitor_id not in competitor_ids:
            report.add_error(f"{label}: unknown competitor_id '{record.competitor_id}'")

        unknown = [t for t in record.topic_ids if t not in topic_ids]
        if unknown:
            report.add_error(f"{label}: unknown topic_ids {unknown}")

        if record.change_id not in change_ids:
            report.add_error(f"{label}: change_id has no authoritative pending item")

        if record.change_id in seen_change:
            report.add_error(
                f"{label}: duplicate change reference (also in {seen_change[record.change_id]})"
            )
        seen_change[record.change_id] = label

        if record.intelligence_id in seen_id:
            report.add_error(f"{label}: duplicate intelligence_id")
        seen_id[record.intelligence_id] = label

        unresolved = [e.evidence_id for e in record.evidence if e.evidence_id not in known_evidence]
        if unresolved:
            report.unresolved_evidence.extend(unresolved)
            if record.confidence != Confidence.LOW:
                report.add_error(
                    f"{label}: unresolved evidence {unresolved} requires confidence='low', "
                    f"got '{record.confidence}'"
                )
            else:
                report.warnings.append(
                    f"{label}: unresolved evidence {unresolved}; confidence correctly lowered"
                )

        if record.decision.value in ("act", "investigate") and record.confidence == Confidence.LOW:
            report.warnings.append(
                f"{label}: decision={record.decision.value} with low confidence; "
                "consider a manual research request"
            )

    if not competitor_ids:
        report.warnings.append(
            "competitor authority is empty; no production competitors have been imported yet"
        )
    return report


__all__ = [
    "EXAMPLE_COMPETITORS_PATH",
    "ValidationReport",
    "load_competitor_ids",
    "load_records",
    "load_topics",
    "validate_intelligence",
]
