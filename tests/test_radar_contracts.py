"""Contract-level tests: schema validation, stable IDs, independent axes."""

from __future__ import annotations

from datetime import date

import pytest
from pipeline.radar.contracts import (
    Confidence,
    Decision,
    Impact,
    IntelligenceRecord,
    PendingChange,
    Topic,
    TopicsFile,
    stable_change_id,
    stable_evidence_id,
    stable_intelligence_id,
    stable_source_id,
)
from pydantic import ValidationError


def _record(**overrides: object) -> dict:
    change_id = "chg-00651c351294422a7b110363"
    base: dict = {
        "intelligence_id": stable_intelligence_id(change_id),
        "change_id": change_id,
        "competitor_id": "sample-alpha",
        "date": date(2026, 11, 10),
        "summary": "SAMPLE — a change.",
        "topic_ids": ["action-plan"],
        "change_type": "updated",
        "impact": "high",
        "confidence": "low",
        "relevance": "high",
        "decision": "investigate",
        "xiaoshuyin_relevance": "SAMPLE — relevance.",
        "mechanism": "SAMPLE — mechanism.",
        "why_it_matters": "SAMPLE — why.",
        "evidence": [{"evidence_id": "ev-abc", "role": "after"}],
        "human_review_status": "unreviewed",
    }
    base.update(overrides)
    return base


def test_stable_identifiers_are_deterministic() -> None:
    assert stable_change_id("https://x.test/a", "h1") == stable_change_id("https://x.test/a", "h1")
    assert stable_change_id("https://x.test/a", "h1") != stable_change_id("https://x.test/a", "h2")
    cid = stable_change_id("https://x.test/a", "h1")
    assert cid.startswith("chg-") and len(cid) == 28
    assert stable_intelligence_id(cid).startswith("int-")
    assert stable_source_id("https://x.test/a").startswith("src-")
    assert stable_evidence_id("snap-1", "after").startswith("ev-")


def test_impact_and_confidence_are_independent() -> None:
    high_impact_low_confidence = IntelligenceRecord.model_validate(_record())
    assert high_impact_low_confidence.impact == Impact.HIGH
    assert high_impact_low_confidence.confidence == Confidence.LOW
    low_impact_high_confidence = IntelligenceRecord.model_validate(
        _record(impact="low", confidence="high")
    )
    assert low_impact_high_confidence.impact == Impact.LOW
    assert low_impact_high_confidence.confidence == Confidence.HIGH


@pytest.mark.parametrize("field", ["impact", "confidence", "decision"])
def test_invalid_enum_values_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        IntelligenceRecord.model_validate(_record(**{field: "catastrophic"}))


def test_missing_evidence_rejected() -> None:
    with pytest.raises(ValidationError):
        IntelligenceRecord.model_validate(_record(evidence=[]))


def test_non_deterministic_intelligence_id_rejected() -> None:
    with pytest.raises(ValidationError, match="deterministic"):
        IntelligenceRecord.model_validate(_record(intelligence_id="int-000000000000000000000000"))


def test_all_decisions_are_supported() -> None:
    for decision in Decision:
        record = IntelligenceRecord.model_validate(_record(decision=str(decision)))
        assert record.decision == decision


def test_topic_taxonomy_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate topic ids"):
        TopicsFile.model_validate(
            {
                "topics": [
                    Topic(id="tracking", label="Tracking").model_dump(),
                    Topic(id="tracking", label="Duplicate").model_dump(),
                ]
            }
        )


def test_pending_change_requires_evidence_and_validated_shape() -> None:
    with pytest.raises(ValidationError):
        PendingChange.model_validate(
            {
                "change_id": stable_change_id("https://x.test/a", "h1"),
                "competitor_id": "sample-alpha",
                "source_id": stable_source_id("https://x.test/a"),
                "source_type": "static",
                "url": "https://x.test/a",
                "detected_at": "2026-11-10T09:00:00Z",
                "change_type": "new",
                "before_snapshot": None,
                "after_snapshot": {
                    "snapshot_id": "snap-1",
                    "url": "https://x.test/a",
                    "content_hash": "h1",
                },
                "diff": "+new",
                "evidence": [],
            }
        )
