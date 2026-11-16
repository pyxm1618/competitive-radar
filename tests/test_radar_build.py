"""Build tests: compiled artifact shape, weekly pulse, timeline, before/after,
empty states and evidence traceability.
"""

from __future__ import annotations

import json

from pipeline.radar.compile import compile_radar
from pipeline.radar.contracts import RadarSnapshot
from pipeline.radar.paths import STATIC_RADAR_JSON


def test_demo_compile_produces_complete_artifact() -> None:
    snapshot = compile_radar(demo=True, write=False)
    assert snapshot.demo is True
    assert snapshot.summary.tracked_competitors == 3
    assert snapshot.summary.tracked_sources == 4
    assert snapshot.summary.detected_changes == 4
    assert snapshot.summary.pending_intelligence == 0
    assert snapshot.summary.manual_research_requests == 2
    assert len(snapshot.topics) == 13
    assert len(snapshot.intelligence) == 4
    assert len(snapshot.before_after) == 4
    assert len(snapshot.manual_research) == 2
    assert len(snapshot.competitors) == 3


def test_evidence_first_every_intelligence_is_traceable() -> None:
    snapshot = compile_radar(demo=True, write=False)
    evidence_ids = {e.evidence_id for e in snapshot.evidence}
    assert evidence_ids
    for item in snapshot.intelligence:
        assert item.evidence_ids, f"{item.intelligence_id} has no evidence"
        assert set(item.evidence_ids).issubset(evidence_ids)
        assert item.provenance.get("snapshot_after")
    manual = [e for e in snapshot.evidence if e.kind == "manual"]
    assert len(manual) == 2
    raw = [e for e in snapshot.evidence if e.kind == "raw"]
    assert raw


def test_radar_ordering_is_impact_relevance_confidence_recency() -> None:
    snapshot = compile_radar(demo=True, write=False)
    assert snapshot.intelligence[0].decision.value == "act"
    assert snapshot.intelligence[0].impact.value == "high"
    # Impact HIGH / Confidence LOW must survive the build (independent axes).
    assert any(
        i.impact.value == "high" and i.confidence.value == "low" for i in snapshot.intelligence
    )


def test_before_after_and_timeline_link_back_to_intelligence() -> None:
    snapshot = compile_radar(demo=True, write=False)
    for pair in snapshot.before_after:
        assert pair.diff
        assert pair.change_id in {i.change_id for i in snapshot.intelligence}
    alpha = next(c for c in snapshot.competitors if c.id == "sample-alpha")
    assert len(alpha.timeline) == 2
    ids = {i.intelligence_id for i in snapshot.intelligence}
    assert all(event.intelligence_id in ids for event in alpha.timeline)
    assert alpha.latest_intelligence_at is not None


def test_topic_and_competitor_aggregates_are_derived() -> None:
    snapshot = compile_radar(demo=True, write=False)
    collaboration = next(t for t in snapshot.topics if t.id == "family-collaboration")
    assert collaboration.intelligence_count == 1
    assert collaboration.competitor_ids == ["sample-beta"]
    assert collaboration.evidence_ids
    gamma = next(c for c in snapshot.competitors if c.id == "sample-gamma")
    assert "monetization" in gamma.topic_ids


def test_weekly_pulse_is_derived_without_a_model() -> None:
    snapshot = compile_radar(demo=True, write=False)
    assert snapshot.weekly.by_decision == {
        "act": 1,
        "investigate": 2,
        "watch": 0,
        "ignore": 1,
    }
    assert snapshot.weekly.manual_research_needed == 2
    assert snapshot.weekly.top_changes
    assert snapshot.weekly.week_start < snapshot.weekly.week_end


def test_authoritative_build_is_an_honest_empty_state() -> None:
    snapshot = compile_radar(demo=False, write=False)
    assert snapshot.demo is False
    assert snapshot.summary.tracked_competitors == 0
    assert snapshot.competitors == []
    assert snapshot.intelligence == []
    assert snapshot.evidence == []
    assert snapshot.before_after == []
    assert snapshot.manual_research == []
    assert snapshot.weekly.by_decision == {
        "act": 0,
        "investigate": 0,
        "watch": 0,
        "ignore": 0,
    }


def test_committed_static_artifact_matches_the_frontend_contract() -> None:
    payload = json.loads(STATIC_RADAR_JSON.read_text(encoding="utf-8"))
    snapshot = RadarSnapshot.model_validate(payload)
    for key in (
        "generated_at",
        "demo",
        "authority",
        "summary",
        "topics",
        "competitors",
        "intelligence",
        "evidence",
        "before_after",
        "manual_research",
        "weekly",
    ):
        assert key in payload
    assert snapshot.weekly is not None
