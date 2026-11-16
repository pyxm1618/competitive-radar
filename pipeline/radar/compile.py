"""Compile authoritative intelligence into the ONE static frontend artifact.

    config/competitors.yaml + config/topics.yaml
    data/intelligence/pending/*.json   (deterministic derived queue)
    data/intelligence/records/*.json   (Antigravity output, validated)
    evidence/manual/*/metadata.json    (manual evidence)
    data/intelligence/research/*.json  (manual research queue)
        -> web/public/radar-static/radar.json

The frontend is a renderer only. It never reads the repository, the warehouse,
or a second business-data source at runtime.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pipeline.config import Settings, get_settings
from pipeline.logging_setup import get_logger
from pipeline.radar.contracts import (
    BeforeAfterPair,
    CompiledCompetitor,
    CompiledEvidence,
    CompiledIntelligence,
    CompiledTopic,
    EvidenceKind,
    IntelligenceRecord,
    ManualResearchRequest,
    PendingChange,
    RadarSnapshot,
    RadarSummary,
    SnapshotRef,
    TimelineEvent,
    TopicsFile,
    TrackedSource,
    VerificationState,
    WeeklyPulse,
    stable_source_id,
    utcnow_iso,
)
from pipeline.radar.manual import (
    compile_manual_evidence,
    compile_research_requests,
    copy_manual_assets,
    load_manual_evidence,
    load_research_requests,
)
from pipeline.radar.paths import (
    COMPETITORS_PATH,
    EXAMPLE_COMPETITORS_PATH,
    EXAMPLE_MANUAL_EVIDENCE_DIR,
    EXAMPLE_PENDING_DIR,
    EXAMPLE_RECORDS_DIR,
    EXAMPLE_RESEARCH_DIR,
    MANUAL_EVIDENCE_DIR,
    PENDING_DIR,
    RECORDS_DIR,
    REPO_ROOT,
    RESEARCH_DIR,
    STATIC_RADAR_JSON,
    TOPICS_PATH,
    WEEKLY_DIR,
    ensure_intelligence_dirs,
)
from pipeline.radar.pending import (
    active_source_pairs,
    is_active_source,
    load_competitors_from,
    load_pending,
)
from pipeline.radar.validate import load_topics, validate_intelligence
from pipeline.radar.weekly import (
    build_weekly_pulse,
    intelligence_score,
    render_weekly_markdown,
    week_bounds,
)
from pipeline.schemas import CompetitorsFile
from pipeline.storage.duckdb_store import Warehouse

log = get_logger("radar.compile")


class IntelligenceValidationFailed(RuntimeError):
    """Raised when authoritative intelligence does not pass validation."""


def _verified_snapshot_ids(snapshot_ids: set[str]) -> set[str]:
    """Check references against the upstream raw authority (best effort)."""
    if not snapshot_ids:
        return set()
    try:
        wh = Warehouse.from_settings(get_settings(), read_only=True)
    except Exception as exc:
        log.warning("raw snapshot verification unavailable: %s", exc)
        return set()
    try:
        placeholders = ",".join("?" for _ in snapshot_ids)
        rows = wh.query(
            f"SELECT id FROM raw.raw_pages WHERE id IN ({placeholders})",
            list(snapshot_ids),
        )
        return {str(r[0]) for r in rows}
    except Exception as exc:
        log.warning("raw snapshot verification query failed: %s", exc)
        return set()
    finally:
        wh.close()


def _pending_evidence(
    items: list[PendingChange],
    verified: set[str],
    demo: bool,
) -> tuple[list[CompiledEvidence], dict[str, SnapshotRef]]:
    """Evidence derived from pending items = references into raw.raw_pages."""
    refs: dict[str, SnapshotRef] = {}
    for item in items:
        for ref in (item.before_snapshot, item.after_snapshot):
            if ref is not None:
                refs[ref.snapshot_id] = ref

    out: list[CompiledEvidence] = []
    for item in items:
        for ev in item.evidence:
            ref = refs.get(ev.snapshot_ref or "")
            if demo:
                state = VerificationState.DEMO_PLACEHOLDER
            elif ev.snapshot_ref and ev.snapshot_ref in verified:
                state = VerificationState.VERIFIED
            else:
                state = VerificationState.UNVERIFIED
            out.append(
                CompiledEvidence(
                    evidence_id=ev.evidence_id,
                    competitor_id=item.competitor_id,
                    type=str(ev.type),
                    kind=str(EvidenceKind.RAW),
                    url=ev.url or (ref.url if ref else None),
                    snapshot_ref=ev.snapshot_ref,
                    content_hash=ref.content_hash if ref else None,
                    captured_at=ref.fetched_at if ref else item.detected_at,
                    title=ev.title,
                    extract=ref.extract if ref else None,
                    verification_state=state,
                )
            )
    return out, refs


def _compile_intelligence(
    records: list[IntelligenceRecord],
    pending_by_change: dict[str, PendingChange],
    now: datetime,
) -> list[CompiledIntelligence]:
    ranked = sorted(
        records,
        key=lambda r: (
            -intelligence_score(r, now.date()),
            -r.date.toordinal(),
            r.intelligence_id,
        ),
    )
    out: list[CompiledIntelligence] = []
    for r in ranked:
        provenance = dict(r.provenance)
        pending = pending_by_change.get(r.change_id)
        if pending is not None:
            provenance.setdefault(
                "pending_file", f"data/intelligence/pending/{pending.change_id}.json"
            )
            provenance.setdefault("url", pending.url)
            provenance.setdefault("snapshot_after", pending.after_snapshot.snapshot_id)
            provenance.setdefault(
                "snapshot_before",
                pending.before_snapshot.snapshot_id if pending.before_snapshot else "",
            )
        out.append(
            CompiledIntelligence(
                intelligence_id=r.intelligence_id,
                change_id=r.change_id,
                competitor_id=r.competitor_id,
                date=r.date.isoformat(),
                summary=r.summary,
                topic_ids=r.topic_ids,
                change_type=r.change_type,
                impact=r.impact,
                confidence=r.confidence,
                relevance=r.relevance,
                decision=r.decision,
                xiaoshuyin_relevance=r.xiaoshuyin_relevance,
                mechanism=r.mechanism,
                why_it_matters=r.why_it_matters,
                evidence_ids=[e.evidence_id for e in r.evidence],
                human_review_status=r.human_review_status,
                analyst=r.analyst,
                provenance=provenance,
            )
        )
    return out


def _compile_competitors(
    cfg: CompetitorsFile,
    records: list[IntelligenceRecord],
    evidence: list[CompiledEvidence],
) -> list[CompiledCompetitor]:
    out: list[CompiledCompetitor] = []
    for comp in cfg.competitors:
        related = sorted(
            (r for r in records if r.competitor_id == comp.id),
            key=lambda r: (r.date, r.intelligence_id),
        )
        sources = [
            TrackedSource(
                source_id=stable_source_id(str(t.url)),
                url=str(t.url),
                source_type=str(t.source_type),
            )
            for t in comp.tracked_urls
        ]
        topic_ids = list(dict.fromkeys(comp.topic_ids + [t for r in related for t in r.topic_ids]))
        timeline = [
            TimelineEvent(
                date=r.date.strftime("%Y-%m"),
                intelligence_id=r.intelligence_id,
                title=r.summary[:100],
                summary=r.summary,
                decision=r.decision,
                topic_ids=r.topic_ids,
                change_id=r.change_id,
            )
            for r in related
        ]
        out.append(
            CompiledCompetitor(
                id=comp.id,
                name=comp.name,
                domain=comp.domain,
                industry=comp.industry,
                tier=comp.tier,
                why_tracked=comp.why_tracked,
                tracked_sources=sources,
                topic_ids=topic_ids,
                latest_intelligence_at=max((r.date.isoformat() for r in related), default=None),
                intelligence_count=len(related),
                evidence_count=sum(1 for e in evidence if e.competitor_id == comp.id),
                timeline=timeline,
            )
        )
    return out


def _compile_topics(topics: TopicsFile, records: list[IntelligenceRecord]) -> list[CompiledTopic]:
    out: list[CompiledTopic] = []
    for topic in topics.topics:
        related = [r for r in records if topic.id in r.topic_ids]
        out.append(
            CompiledTopic(
                id=topic.id,
                label=topic.label,
                description=topic.description,
                intelligence_count=len(related),
                competitor_ids=sorted({r.competitor_id for r in related}),
                evidence_ids=sorted({e.evidence_id for r in related for e in r.evidence}),
            )
        )
    return out


def _write_weekly_and_report(
    pulse: WeeklyPulse,
    records: list[IntelligenceRecord],
    research: list[ManualResearchRequest],
) -> None:
    """Write the derived pulse + markdown brief into upstream storage."""
    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    weekly_file = WEEKLY_DIR / f"{pulse.week_start}.json"
    weekly_file.write_text(
        json.dumps(pulse.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    body = render_weekly_markdown(pulse, records, research)
    try:
        wh = Warehouse.from_settings(get_settings())
        try:
            wh.upsert_report(
                report_id=f"pulse-{pulse.week_start}",
                title=f"Weekly Pulse - {pulse.week_start}",
                week_start=pulse.week_start,
                summary=(
                    f"{pulse.total_changes} changes, {pulse.important_changes} important, "
                    f"{pulse.manual_research_needed} manual research request(s)."
                ),
                body_md=body,
                created_at=datetime.now(UTC),
            )
        finally:
            wh.close()
    except Exception as exc:
        log.warning("could not persist pulse into upstream raw.reports: %s", exc)


def compile_radar(
    *,
    demo: bool = False,
    settings: Settings | None = None,
    write: bool = True,
) -> RadarSnapshot:
    """Validate -> aggregate -> write the single compiled frontend artifact.

    ``settings`` is accepted for CLI symmetry; compilation itself is file-based
    so it works in CI without a DuckDB warehouse or any model API key.
    """
    del settings
    ensure_intelligence_dirs()

    competitors_path = EXAMPLE_COMPETITORS_PATH if demo else COMPETITORS_PATH
    pending_dir = EXAMPLE_PENDING_DIR if demo else PENDING_DIR
    records_dir = EXAMPLE_RECORDS_DIR if demo else RECORDS_DIR
    research_dir = EXAMPLE_RESEARCH_DIR if demo else RESEARCH_DIR
    manual_root = EXAMPLE_MANUAL_EVIDENCE_DIR if demo else MANUAL_EVIDENCE_DIR

    report = validate_intelligence(
        records_dir=records_dir,
        pending_dir=pending_dir,
        competitors_path=competitors_path,
        topics_path=TOPICS_PATH,
        manual_root=manual_root,
    )
    if not report.ok:
        raise IntelligenceValidationFailed("; ".join(report.errors))

    cfg = load_competitors_from(competitors_path)
    topics = load_topics(TOPICS_PATH)
    active_sources = active_source_pairs(cfg)
    pending = [
        item
        for item in load_pending(pending_dir)
        if is_active_source(active_sources, item.competitor_id, item.url)
    ]
    pending_by_change = {p.change_id: p for p in pending}
    records = report.records
    active_competitor_ids = {c.id for c in cfg.competitors}
    manual_items = [
        item
        for item in load_manual_evidence(manual_root)
        if item.competitor_id in active_competitor_ids
        and (item.related_change_id is None or item.related_change_id in pending_by_change)
    ]
    research_items = [
        item
        for item in load_research_requests(research_dir)
        if (item.competitor_id is None or item.competitor_id in active_competitor_ids)
        and (item.related_change_id is None or item.related_change_id in pending_by_change)
    ]

    verified = (
        set()
        if demo
        else _verified_snapshot_ids(
            {
                ref.snapshot_id
                for item in pending
                for ref in (item.before_snapshot, item.after_snapshot)
                if ref is not None
            }
        )
    )
    raw_evidence, _refs = _pending_evidence(pending, verified, demo)
    manual_evidence = compile_manual_evidence(manual_items)
    evidence = raw_evidence + manual_evidence
    evidence_by_id = {e.evidence_id: e for e in evidence}
    for record in records:
        for ref in record.evidence:
            existing = evidence_by_id.get(ref.evidence_id)
            if existing is not None and record.intelligence_id not in existing.intelligence_ids:
                existing.intelligence_ids.append(record.intelligence_id)

    before_after: list[BeforeAfterPair] = []
    for item in pending:
        before_id = item.before_snapshot.snapshot_id if item.before_snapshot else None
        after_id = item.after_snapshot.snapshot_id
        before = (
            next((e for e in raw_evidence if e.snapshot_ref == before_id), None)
            if before_id
            else None
        )
        after = next((e for e in raw_evidence if e.snapshot_ref == after_id), None)
        if before is None and after is None:
            continue
        if before is not None:
            before.before_evidence_id = before.evidence_id
            before.after_evidence_id = after.evidence_id if after else None
        if after is not None:
            after.before_evidence_id = before.evidence_id if before else None
            after.after_evidence_id = after.evidence_id
        before_after.append(
            BeforeAfterPair(
                change_id=item.change_id,
                competitor_id=item.competitor_id,
                url=item.url,
                before=before,
                after=after,
                diff=item.diff,
            )
        )

    now = datetime.now(UTC)
    today = now.date()
    start, end = week_bounds(today)
    detected_in_week = sum(
        1 for p in pending if start.isoformat() <= p.detected_at[:10] < end.isoformat()
    )
    pulse = build_weekly_pulse(
        records,
        topics,
        research_items,
        detected_changes_in_week=detected_in_week,
        today=today,
    )
    important = sum(
        1 for r in records if str(r.impact) == "high" or str(r.decision) in ("act", "investigate")
    )
    analyzed_changes = {r.change_id for r in records}

    snapshot = RadarSnapshot(
        generated_at=utcnow_iso(),
        demo=demo,
        authority={
            "competitors": str(Path(competitors_path).relative_to(REPO_ROOT)),
            "topics": "config/topics.yaml",
            "changes": "deterministic snapshot diff (upstream compete, raw.changes)",
            "intelligence": (
                "examples/intelligence/records/*.json (DEMO ONLY)"
                if demo
                else "data/intelligence/records/*.json"
            ),
            "raw_evidence": "upstream raw.raw_pages + data/raw/*.parquet",
            "frontend": "web/public/radar-static/radar.json (renderer only)",
        },
        summary=RadarSummary(
            tracked_competitors=len(cfg.competitors),
            tracked_sources=sum(len(c.tracked_urls) for c in cfg.competitors),
            detected_changes=len(pending),
            important_changes=important,
            pending_intelligence=sum(1 for p in pending if p.change_id not in analyzed_changes),
            manual_research_requests=len(research_items),
        ),
        topics=_compile_topics(topics, records),
        competitors=_compile_competitors(cfg, records, evidence),
        intelligence=_compile_intelligence(records, pending_by_change, now),
        evidence=evidence,
        before_after=before_after,
        manual_research=compile_research_requests(research_items),
        weekly=pulse,
    )

    if write:
        STATIC_RADAR_JSON.parent.mkdir(parents=True, exist_ok=True)
        STATIC_RADAR_JSON.write_text(
            json.dumps(
                snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        copy_manual_assets(manual_items, manual_root)
        if not demo:
            _write_weekly_and_report(pulse, records, research_items)
        log.info("wrote %s", STATIC_RADAR_JSON)
    return snapshot


__all__ = ["IntelligenceValidationFailed", "compile_radar"]
