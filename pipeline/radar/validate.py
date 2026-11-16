"""Validation of authoritative intelligence output.

radar validate and radar build both gate on this module. It enforces the
hard rules from the V1 contract while distinguishing current monitoring from
historical intelligence:

  * schema validation (invalid impact / confidence / decision are rejected);
  * evidence-first (a conclusion with no evidence reference is rejected);
  * current records must reference an authoritative active pending change;
  * evidence ownership is bound to competitor + change where applicable;
  * retired competitors / URLs may remain as historical records without
    re-entering the current Radar;
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

from pipeline.config import load_competitors
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
from pipeline.radar.pending import active_source_pairs, is_active_source, load_pending


@dataclass(frozen=True)
class EvidenceOwnership:
    kind: str
    competitor_id: str
    change_id: str | None


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    records: list[IntelligenceRecord] = field(default_factory=list)
    historical_records: list[IntelligenceRecord] = field(default_factory=list)
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
    cfg = load_competitors(path or COMPETITORS_PATH)
    return {row.id for row in cfg.competitors}


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


def _evidence_ownership(
    pending_items: list,
    manual_root: Path | None = None,
) -> dict[str, EvidenceOwnership]:
    owners: dict[str, EvidenceOwnership] = {}
    for item in pending_items:
        for evidence in item.evidence:
            owners[evidence.evidence_id] = EvidenceOwnership(
                kind="raw",
                competitor_id=item.competitor_id,
                change_id=item.change_id,
            )
    for item in load_manual_evidence(manual_root):
        owners[item.evidence_id] = EvidenceOwnership(
            kind="manual",
            competitor_id=item.competitor_id,
            change_id=item.related_change_id,
        )
    return owners


def validate_intelligence(
    *,
    records_dir: Path | None = None,
    pending_dir: Path | None = None,
    competitors_path: Path | None = None,
    topics_path: Path | None = None,
    manual_root: Path | None = None,
) -> ValidationReport:
    """Validate current authoritative intelligence and preserve retired history."""
    report = ValidationReport()
    records, parse_errors, count = load_records(records_dir)
    report.files_read = count
    for err in parse_errors:
        report.add_error(err)

    cfg = load_competitors(competitors_path or COMPETITORS_PATH)
    competitor_ids = {row.id for row in cfg.competitors}
    active_sources = active_source_pairs(cfg)

    topics = load_topics(topics_path)
    topic_ids = topics.topic_ids

    all_pending = load_pending(pending_dir or PENDING_DIR)
    pending = [
        item
        for item in all_pending
        if is_active_source(active_sources, item.competitor_id, item.url)
    ]
    pending_by_change = {item.change_id: item for item in pending}
    evidence_owners = _evidence_ownership(pending, manual_root)

    seen_change: dict[str, str] = {}
    seen_id: dict[str, str] = {}

    for record in records:
        label = f"{record.intelligence_id} ({record.change_id})"

        expected = stable_intelligence_id(record.change_id)
        if record.intelligence_id != expected:
            report.add_error(f"{label}: non-deterministic intelligence_id, expected {expected}")

        unknown = [t for t in record.topic_ids if t not in topic_ids]
        if unknown:
            report.add_error(f"{label}: unknown topic_ids {unknown}")

        if record.change_id in seen_change:
            report.add_error(
                f"{label}: duplicate change reference (also in {seen_change[record.change_id]})"
            )
        seen_change[record.change_id] = label

        if record.intelligence_id in seen_id:
            report.add_error(f"{label}: duplicate intelligence_id")
        seen_id[record.intelligence_id] = label

        current_pending = pending_by_change.get(record.change_id)
        record_url = str(record.provenance.get("url") or "")

        historical = current_pending is None and (
            record.competitor_id not in competitor_ids
            or (
                bool(record_url)
                and not is_active_source(active_sources, record.competitor_id, record_url)
            )
        )

        if historical:
            report.historical_records.append(record)
            continue

        report.records.append(record)

        if record.competitor_id not in competitor_ids:
            report.add_error(f"{label}: unknown competitor_id '{record.competitor_id}'")

        if current_pending is None:
            report.add_error(f"{label}: change_id has no authoritative active pending item")
        elif current_pending.competitor_id != record.competitor_id:
            report.add_error(
                f"{label}: pending change belongs to competitor "
                f"'{current_pending.competitor_id}', not '{record.competitor_id}'"
            )

        unresolved: list[str] = []
        for evidence in record.evidence:
            owner = evidence_owners.get(evidence.evidence_id)
            if owner is None:
                unresolved.append(evidence.evidence_id)
                continue
            if owner.competitor_id != record.competitor_id:
                report.add_error(
                    f"{label}: cross-competitor evidence '{evidence.evidence_id}' belongs to "
                    f"'{owner.competitor_id}', not '{record.competitor_id}'"
                )
                continue
            if owner.kind == "raw" and owner.change_id != record.change_id:
                report.add_error(
                    f"{label}: raw evidence '{evidence.evidence_id}' belongs to change "
                    f"'{owner.change_id}', not '{record.change_id}'"
                )
            if (
                owner.kind == "manual"
                and owner.change_id is not None
                and owner.change_id != record.change_id
            ):
                report.add_error(
                    f"{label}: manual evidence '{evidence.evidence_id}' is bound to change "
                    f"'{owner.change_id}', not '{record.change_id}'"
                )

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

    if report.historical_records:
        report.warnings.append(
            f"{len(report.historical_records)} historical intelligence record(s) excluded "
            "from the current Radar because their competitor or tracked URL is retired"
        )

    if not competitor_ids:
        report.warnings.append(
            "competitor authority is empty; no production competitors have been imported yet"
        )
    return report


__all__ = [
    "EXAMPLE_COMPETITORS_PATH",
    "EvidenceOwnership",
    "ValidationReport",
    "load_competitor_ids",
    "load_records",
    "load_topics",
    "validate_intelligence",
]
