"""Regenerate the clearly-labelled SAMPLE fixtures under examples/.

These files are NOT authoritative. They exist so that the pipeline, validation,
frontend pages, empty-state complements, timeline, before/after and manual
evidence can be exercised locally without inventing real competitors.

Run:  uv run python scripts/generate_radar_examples.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pipeline.radar.contracts import (
    Confidence,
    Decision,
    EvidenceKind,
    EvidenceType,
    HumanReviewStatus,
    Impact,
    IntelligenceRecord,
    ManualEvidence,
    ManualResearchRequest,
    PendingChange,
    PendingEvidence,
    Relevance,
    RequiredEvidenceItem,
    ResearchStatus,
    SnapshotRef,
    VerificationState,
    stable_change_id,
    stable_evidence_id,
    stable_intelligence_id,
    stable_request_id,
    stable_source_id,
)
from pipeline.radar.paths import (
    EXAMPLE_MANUAL_EVIDENCE_DIR,
    EXAMPLE_PENDING_DIR,
    EXAMPLE_RECORDS_DIR,
    EXAMPLE_RESEARCH_DIR,
    REPO_ROOT,
)

BEFORE_DATE = "2026-10-20T09:00:00Z"
AFTER_DATES = [
    "2026-11-10T09:00:00Z",
    "2026-11-12T09:00:00Z",
    "2026-11-14T09:00:00Z",
    "2026-11-15T09:00:00Z",
]

# (competitor, url, before text, after text, change_type)
SNAPSHOTS = [
    (
        "sample-alpha",
        "https://alpha.example.com/home",
        "SAMPLE — AI consultation only. Ask a question, receive a written answer.",
        "SAMPLE — AI consultation plus a staged action plan with weekly check-ins.",
        "updated",
    ),
    (
        "sample-alpha",
        "https://alpha.example.com/changelog",
        "SAMPLE — Changelog: assessment v1.",
        "SAMPLE — Changelog: added long-term tracking and follow-up reminders.",
        "updated",
    ),
    (
        "sample-beta",
        "https://beta.example.com/features",
        "",
        "SAMPLE — Shared family tasks: parents and child each see their own steps.",
        "new",
    ),
    (
        "sample-gamma",
        "https://gamma.example.com/pricing",
        "SAMPLE — Free tier, 9 USD/month premium.",
        "SAMPLE — Free tier, 11 USD/month premium, annual plan added.",
        "updated",
    ),
]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def _snapshot_id(url: str, text: str) -> str:
    return f"snap-{_hash(f'{url}|{text}')}"


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"  {path.relative_to(REPO_ROOT)}")


def _build_pending() -> list[PendingChange]:
    items: list[PendingChange] = []
    for idx, (competitor, url, before_text, after_text, change_type) in enumerate(SNAPSHOTS):
        after_hash = _hash(after_text)
        after_snap = _snapshot_id(url, after_text)
        before_snap = _snapshot_id(url, before_text) if before_text else None
        before_hash = _hash(before_text) if before_text else None
        after = SnapshotRef(
            snapshot_id=after_snap,
            url=url,
            content_hash=after_hash,
            source_type="static",
            fetched_at=AFTER_DATES[idx],
            extract=after_text,
        )
        before = (
            SnapshotRef(
                snapshot_id=before_snap or "",
                url=url,
                content_hash=before_hash or "",
                source_type="static",
                fetched_at=BEFORE_DATE,
                extract=before_text,
            )
            if before_text
            else None
        )
        evidence = [
            PendingEvidence(
                evidence_id=stable_evidence_id(after_snap, "after"),
                type=EvidenceType.SNAPSHOT_AFTER,
                kind=EvidenceKind.RAW,
                title=f"SAMPLE — After snapshot: {url}",
                url=url,
                snapshot_ref=after_snap,
            )
        ]
        if before is not None and before_snap:
            evidence.insert(
                0,
                PendingEvidence(
                    evidence_id=stable_evidence_id(before_snap, "before"),
                    type=EvidenceType.SNAPSHOT_BEFORE,
                    kind=EvidenceKind.RAW,
                    title=f"SAMPLE — Before snapshot: {url}",
                    url=url,
                    snapshot_ref=before_snap,
                ),
            )
        diff = "\n".join(
            [
                "--- before",
                "+++ after",
                f"-{before_text}" if before_text else "-(no prior snapshot)",
                f"+{after_text}",
            ]
        )
        items.append(
            PendingChange(
                change_id=stable_change_id(url, after_hash),
                competitor_id=competitor,
                source_id=stable_source_id(url),
                source_type="static",
                url=url,
                detected_at=AFTER_DATES[idx],
                change_type=change_type,  # type: ignore[arg-type]
                before_snapshot=before,
                after_snapshot=after,
                diff=diff,
                evidence=evidence,
                provenance={
                    "change_authority": "SAMPLE deterministic snapshot diff",
                    "raw_evidence_table": "raw.raw_pages (SAMPLE reference)",
                    "competitor_authority": "config/examples/competitors.sample.yaml",
                    "snapshot_before": before_snap or "",
                    "snapshot_after": after_snap,
                    "diff_engine": "pipeline/detect/change.py",
                },
            )
        )
    return items


def _build_records(pending: list[PendingChange]) -> list[IntelligenceRecord]:
    specs = [
        {
            "date": "2026-11-10",
            "summary": "SAMPLE — Added a staged action plan after the AI consultation.",
            "topic_ids": ["ai-conversation", "action-plan"],
            "impact": Impact.HIGH,
            "confidence": Confidence.HIGH,
            "relevance": Relevance.HIGH,
            "decision": Decision.ACT,
            "xiaoshuyin_relevance": "SAMPLE — Directly matches the assessment-to-action-plan chain Xiaoshuyin is exploring.",
            "mechanism": "SAMPLE — Conversation output is converted into a sequenced, time-boxed plan instead of a free-form answer.",
            "why_it_matters": "SAMPLE — Shows one concrete way to move from dialogue to an executable family plan.",
            "roles": ("before", "after"),
        },
        {
            "date": "2026-11-12",
            "summary": "SAMPLE — Changelog now mentions long-term tracking and follow-up reminders.",
            "topic_ids": ["tracking", "follow-up"],
            "impact": Impact.MEDIUM,
            "confidence": Confidence.MEDIUM,
            "relevance": Relevance.HIGH,
            "decision": Decision.INVESTIGATE,
            "xiaoshuyin_relevance": "SAMPLE — Follow-up and tracking are core Xiaoshuyin capability areas.",
            "mechanism": "SAMPLE — Retention is implemented as recurring check-in prompts tied to earlier actions.",
            "why_it_matters": "SAMPLE — Only a changelog line is available; the actual flow still needs manual research.",
            "roles": ("after",),
        },
        {
            "date": "2026-11-14",
            "summary": "SAMPLE — Shared family tasks assign separate steps to parents and child.",
            "topic_ids": ["family-collaboration", "child-participation"],
            "impact": Impact.HIGH,
            "confidence": Confidence.LOW,
            "relevance": Relevance.MEDIUM,
            "decision": Decision.INVESTIGATE,
            "xiaoshuyin_relevance": "SAMPLE — Parent-child collaboration is a Xiaoshuyin design question.",
            "mechanism": "SAMPLE — One plan is split into role-specific views with a shared progress state.",
            "why_it_matters": "SAMPLE — High potential impact, but only a marketing page was captured. IMPACT HIGH / CONFIDENCE LOW is intentional.",
            "roles": ("after",),
        },
        {
            "date": "2026-11-15",
            "summary": "SAMPLE — Premium price changed and an annual plan appeared.",
            "topic_ids": ["monetization"],
            "impact": Impact.LOW,
            "confidence": Confidence.HIGH,
            "relevance": Relevance.LOW,
            "decision": Decision.IGNORE,
            "xiaoshuyin_relevance": "SAMPLE — Pricing packaging is outside the current product-design questions.",
            "mechanism": "SAMPLE — Simple tier price adjustment plus an annual billing option.",
            "why_it_matters": "SAMPLE — No product mechanism change; noise for this radar.",
            "roles": ("after",),
        },
    ]
    records: list[IntelligenceRecord] = []
    for item, spec in zip(pending, specs, strict=True):
        wanted = set(spec["roles"])
        refs = [
            {
                "evidence_id": e.evidence_id,
                "role": ("before" if e.type == EvidenceType.SNAPSHOT_BEFORE else "after"),
            }
            for e in item.evidence
            if ("before" if e.type == EvidenceType.SNAPSHOT_BEFORE else "after") in wanted
        ]
        records.append(
            IntelligenceRecord(
                intelligence_id=stable_intelligence_id(item.change_id),
                change_id=item.change_id,
                competitor_id=item.competitor_id,
                date=spec["date"],  # type: ignore[arg-type]
                summary=spec["summary"],  # type: ignore[arg-type]
                topic_ids=spec["topic_ids"],  # type: ignore[arg-type]
                change_type=item.change_type,
                impact=spec["impact"],  # type: ignore[arg-type]
                confidence=spec["confidence"],  # type: ignore[arg-type]
                relevance=spec["relevance"],  # type: ignore[arg-type]
                decision=spec["decision"],  # type: ignore[arg-type]
                xiaoshuyin_relevance=spec["xiaoshuyin_relevance"],  # type: ignore[arg-type]
                mechanism=spec["mechanism"],  # type: ignore[arg-type]
                why_it_matters=spec["why_it_matters"],  # type: ignore[arg-type]
                evidence=refs,  # type: ignore[arg-type]
                human_review_status=HumanReviewStatus.UNREVIEWED,
                analyst="sample-fixture-generator",
                provenance={
                    "pending_file": f"examples/intelligence/pending/{item.change_id}.json",
                    "url": item.url,
                    "snapshot_after": item.after_snapshot.snapshot_id,
                    "snapshot_before": (
                        item.before_snapshot.snapshot_id if item.before_snapshot else ""
                    ),
                },
                created_at=f"{spec['date']}T12:00:00Z",
            )
        )
    return records


def _build_manual_evidence() -> list[ManualEvidence]:
    items = [
        ManualEvidence(
            evidence_id="evm-sample-ios-onboarding",
            competitor_id="sample-beta",
            captured_at="2026-11-15T10:00:00Z",
            evidence_type=EvidenceType.MANUAL_NOTE,
            title="SAMPLE — Manual note about iOS onboarding",
            description=(
                "SAMPLE — Placeholder note describing a login-walled iOS onboarding flow "
                "that automated collection cannot reach. Not real evidence."
            ),
            source_label="iOS App (manual)",
            url=None,
            files=["notes.txt"],
            topic_ids=["child-participation", "assessment"],
            verification_state=VerificationState.DEMO_PLACEHOLDER,
            captured_by="sample-fixture-generator",
        ),
        ManualEvidence(
            evidence_id="evm-sample-miniprogram",
            competitor_id="sample-alpha",
            captured_at="2026-11-15T11:00:00Z",
            evidence_type=EvidenceType.MANUAL_SCREENSHOT,
            title="SAMPLE — Labelled placeholder, not a real screenshot",
            description=(
                "SAMPLE — This is an explicitly labelled placeholder image used only to "
                "exercise the manual-screenshot display path. No real product screen is depicted."
            ),
            source_label="WeChat Mini Program (manual)",
            files=["placeholder.svg"],
            topic_ids=["family-collaboration"],
            verification_state=VerificationState.DEMO_PLACEHOLDER,
            captured_by="sample-fixture-generator",
        ),
    ]
    for item in items:
        folder = EXAMPLE_MANUAL_EVIDENCE_DIR / item.evidence_id
        folder.mkdir(parents=True, exist_ok=True)
        _write(folder / "metadata.json", item.model_dump(mode="json"))
        if "notes.txt" in item.files:
            (folder / "notes.txt").write_text(
                "SAMPLE MANUAL EVIDENCE — NOT REAL EVIDENCE.\n"
                "This file exists only to demonstrate the manual-evidence directory contract.\n",
                encoding="utf-8",
            )
        if "placeholder.svg" in item.files:
            (folder / "placeholder.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
                '<rect width="640" height="360" fill="#f4f4f5"/>'
                '<rect x="24" y="24" width="592" height="312" rx="12" fill="#ffffff" stroke="#d4d4d8" stroke-width="2"/>'
                '<text x="320" y="160" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#27272a">'
                "SAMPLE PLACEHOLDER — NOT A REAL SCREENSHOT</text>"
                '<text x="320" y="200" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#71717a">'
                "Manual evidence asset used only to exercise the display contract.</text></svg>\n",
                encoding="utf-8",
            )
    return items


def _build_research(
    pending: list[PendingChange], records: list[IntelligenceRecord]
) -> list[ManualResearchRequest]:
    questions = [
        (
            1,
            "sample-beta",
            ["family-collaboration", "child-participation"],
            "SAMPLE — Does the shared family task flow require a separate child onboarding?",
            "SAMPLE — The marketing page cannot show whether the child participates directly.",
            [
                "SAMPLE — Capture the iOS onboarding up to the first shared task.",
                "SAMPLE — Capture the parent view and the child view of the same task.",
                "SAMPLE — Capture the final result page after the task is completed.",
            ],
            [
                "SAMPLE — onboarding screenshot",
                "SAMPLE — parent task view screenshot",
                "SAMPLE — child task view screenshot",
                "SAMPLE — final result page screenshot",
            ],
        ),
        (
            0,
            "sample-alpha",
            ["ai-conversation", "action-plan"],
            "SAMPLE — Is the action plan generated dynamically or selected from a fixed template?",
            "SAMPLE — The mechanism determines whether this is relevant to Xiaoshuyin's AI support design.",
            [
                "SAMPLE — Run the same intake twice with different answers.",
                "SAMPLE — Capture both resulting plans.",
                "SAMPLE — Note any unchanged sections.",
            ],
            ["SAMPLE — two plan screenshots", "SAMPLE — intake answers note"],
        ),
    ]
    out: list[ManualResearchRequest] = []
    for idx, cid, topics, question, why, steps, required in questions:
        out.append(
            ManualResearchRequest(
                request_id=stable_request_id(pending[idx].change_id, question),
                competitor_id=cid,
                topic_ids=topics,
                research_question=question,
                why_needed=why,
                suggested_steps=steps,
                required_evidence=[RequiredEvidenceItem(label=label) for label in required],
                status=ResearchStatus.OPEN,
                created_by="sample-fixture-generator",
                related_change_id=pending[idx].change_id,
                related_intelligence_id=records[idx].intelligence_id,
            )
        )
    return out


def main() -> None:
    print("Regenerating SAMPLE fixtures (not authoritative):")
    for directory in (
        EXAMPLE_PENDING_DIR,
        EXAMPLE_RECORDS_DIR,
        EXAMPLE_RESEARCH_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
        for old in directory.glob("*.json"):
            old.unlink()

    pending = _build_pending()
    for item in pending:
        _write(EXAMPLE_PENDING_DIR / f"{item.change_id}.json", item.model_dump(mode="json"))
    records = _build_records(pending)
    for record in records:
        _write(
            EXAMPLE_RECORDS_DIR / f"{record.intelligence_id}.json", record.model_dump(mode="json")
        )
    _build_manual_evidence()
    for request in _build_research(pending, records):
        _write(EXAMPLE_RESEARCH_DIR / f"{request.request_id}.json", request.model_dump(mode="json"))
    print("Done. All fixtures are explicitly marked SAMPLE and are not authoritative.")


if __name__ == "__main__":
    main()
