"""Intelligence validation: schema, provenance, duplicates, unknown references,
missing evidence behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pipeline.radar.paths import (
    EXAMPLE_COMPETITORS_PATH,
    EXAMPLE_MANUAL_EVIDENCE_DIR,
    EXAMPLE_PENDING_DIR,
    EXAMPLE_RECORDS_DIR,
    TOPICS_PATH,
)
from pipeline.radar.validate import ValidationReport, load_topics, validate_intelligence
from pipeline.radar_cli import app
from typer.testing import CliRunner


def _valid_examples() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(EXAMPLE_RECORDS_DIR.glob("*.json"))
    ]


def _write_records(tmp_path: Path, records: list[dict]) -> Path:
    directory = tmp_path / "records"
    directory.mkdir(parents=True, exist_ok=True)
    for index, record in enumerate(records):
        (directory / f"record-{index}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return directory


def _validate(records_dir: Path) -> ValidationReport:
    return validate_intelligence(
        records_dir=records_dir,
        pending_dir=EXAMPLE_PENDING_DIR,
        competitors_path=EXAMPLE_COMPETITORS_PATH,
        topics_path=TOPICS_PATH,
        manual_root=EXAMPLE_MANUAL_EVIDENCE_DIR,
    )


def test_sample_fixtures_validate_cleanly(tmp_path: Path) -> None:
    report = _validate(_write_records(tmp_path, _valid_examples()))
    assert report.ok, report.errors
    assert report.files_read == 4
    assert len(report.records) == 4
    assert not report.unresolved_evidence


def test_impact_high_confidence_low_is_a_legal_combination(tmp_path: Path) -> None:
    records = _valid_examples()
    assert any(r["impact"] == "high" and r["confidence"] == "low" for r in records)
    report = _validate(_write_records(tmp_path, records))
    assert report.ok


@pytest.mark.parametrize(
    ("field", "value"),
    [("impact", "urgent"), ("confidence", "certain"), ("decision", "maybe")],
)
def test_invalid_enum_rejected(tmp_path: Path, field: str, value: str) -> None:
    records = _valid_examples()[:1]
    records[0][field] = value
    report = _validate(_write_records(tmp_path, records))
    assert not report.ok
    assert report.errors


def test_missing_evidence_rejected(tmp_path: Path) -> None:
    records = _valid_examples()[:1]
    records[0]["evidence"] = []
    report = _validate(_write_records(tmp_path, records))
    assert not report.ok


def test_duplicate_change_reference_rejected(tmp_path: Path) -> None:
    record = _valid_examples()[0]
    report = _validate(_write_records(tmp_path, [record, dict(record)]))
    assert not report.ok
    assert any("duplicate change reference" in e for e in report.errors)
    assert any("duplicate intelligence_id" in e for e in report.errors)


def test_unknown_competitor_and_topic_rejected(tmp_path: Path) -> None:
    records = _valid_examples()[:1]
    records[0]["competitor_id"] = "not-in-authority"
    records[0]["topic_ids"] = ["not-a-real-topic"]
    report = _validate(_write_records(tmp_path, records))
    assert not report.ok
    assert any("unknown competitor_id" in e for e in report.errors)
    assert any("unknown topic_ids" in e for e in report.errors)


def test_unresolved_evidence_forces_low_confidence(tmp_path: Path) -> None:
    records = _valid_examples()[:1]
    records[0]["evidence"] = [{"evidence_id": "ev-does-not-exist", "role": "after"}]
    records[0]["confidence"] = "high"
    bad = _validate(_write_records(tmp_path / "bad", records))
    assert not bad.ok
    assert any("requires confidence='low'" in e for e in bad.errors)

    records[0]["confidence"] = "low"
    lowered = _validate(_write_records(tmp_path / "lowered", records))
    assert lowered.ok
    assert lowered.unresolved_evidence == ["ev-does-not-exist"]
    assert any("confidence correctly lowered" in w for w in lowered.warnings)


def test_non_deterministic_id_rejected(tmp_path: Path) -> None:
    records = _valid_examples()[:1]
    records[0]["intelligence_id"] = "int-" + "0" * 24
    report = _validate(_write_records(tmp_path, records))
    assert not report.ok


def test_topic_authority_has_all_expected_ids() -> None:
    topics = load_topics()
    assert len(topics.topics) == 13
    assert "family-collaboration" in topics.topic_ids
    assert "monetization" in topics.topic_ids


def test_radar_validate_cli_succeeds_on_empty_authority() -> None:
    result = CliRunner().invoke(app, ["validate"])
    assert result.exit_code == 0, result.output
    assert "validation passed" in result.output
