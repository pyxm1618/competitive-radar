"""Competitive Radar V1 contracts.

These Pydantic models are the ONLY authoritative shapes for the external-AI
file protocol. They are intentionally kept in one module so that the pending
queue, the intelligence output, the manual-evidence contract and the compiled
frontend artifact cannot drift apart.

Authority rules encoded here:
  * AI never decides whether a change happened (only ``detect_changes`` does).
  * No intelligence record may exist without at least one evidence reference.
  * ``impact`` and ``confidence`` are independent enums.
  * IDs are deterministic and derived, never random.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Impact(StrEnum):
    """How much the change would matter for a product decision IF it holds."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Confidence(StrEnum):
    """How well the available evidence supports the conclusion."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Relevance(StrEnum):
    """Closeness to Xiaoshuyin's current product questions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Decision(StrEnum):
    ACT = "act"  # enough evidence, worth a product decision now
    INVESTIGATE = "investigate"  # potentially high impact, needs more research
    WATCH = "watch"  # no action now, keep observing
    IGNORE = "ignore"  # noise or unrelated to the product direction


class HumanReviewStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    DISPUTED = "disputed"
    CORRECTED = "corrected"


class EvidenceType(StrEnum):
    SNAPSHOT_BEFORE = "snapshot_before"
    SNAPSHOT_AFTER = "snapshot_after"
    SCREENSHOT = "screenshot"
    PAGE_EXTRACT = "page_extract"
    CHANGELOG = "changelog"
    MANUAL_SCREENSHOT = "manual_screenshot"
    MANUAL_RECORDING = "manual_recording"
    MANUAL_NOTE = "manual_note"
    PDF_DOCUMENT = "pdf_document"


class EvidenceKind(StrEnum):
    RAW = "raw"
    MANUAL = "manual"


class VerificationState(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    MISSING = "missing"
    DEMO_PLACEHOLDER = "demo_placeholder"


class ResearchStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


CHANGE_TYPES = ("new", "updated", "removed")


# --------------------------------------------------------------------------- #
# Stable identifiers
# --------------------------------------------------------------------------- #
def stable_change_id(url: str, new_hash: str) -> str:
    """Deterministic change id.

    Reuses the upstream ``_signal_id`` convention
    (``pipeline/extract/runner.py``) so the legacy LLM path and the default
    no-key path can never produce two IDs for the same detected change.
    """
    digest = hashlib.sha256(f"{url}\n{new_hash}".encode()).hexdigest()[:24]
    return f"chg-{digest}"


def stable_source_id(url: str) -> str:
    return f"src-{hashlib.sha256(url.encode()).hexdigest()[:16]}"


def stable_evidence_id(snapshot_id: str, role: str) -> str:
    digest = hashlib.sha256(f"{snapshot_id}|{role}".encode()).hexdigest()[:20]
    return f"ev-{digest}"


def stable_intelligence_id(change_id: str) -> str:
    """Exactly one intelligence record per detected change."""
    digest = hashlib.sha256(f"intelligence|{change_id}".encode()).hexdigest()[:24]
    return f"int-{digest}"


def stable_request_id(change_id: str, research_question: str) -> str:
    digest = hashlib.sha256(f"{change_id}|{research_question}".encode()).hexdigest()[:20]
    return f"req-{digest}"


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------- #
# Taxonomy authority (config/topics.yaml)
# --------------------------------------------------------------------------- #
class Topic(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    label: str = Field(min_length=1)
    description: str = ""
    keywords: list[str] = Field(default_factory=list)


class TopicsFile(BaseModel):
    schema_version: int = SCHEMA_VERSION
    topics: list[Topic] = Field(min_length=1)

    @field_validator("topics")
    @classmethod
    def _unique_ids(cls, value: list[Topic]) -> list[Topic]:
        ids = [t.id for t in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate topic ids in config/topics.yaml")
        return value

    @property
    def topic_ids(self) -> set[str]:
        return {t.id for t in self.topics}


# --------------------------------------------------------------------------- #
# Pending change contract (deterministic machine input for Antigravity)
# --------------------------------------------------------------------------- #
class SnapshotRef(BaseModel):
    """A reference into the upstream raw evidence authority (raw.raw_pages)."""

    snapshot_id: str
    url: str
    content_hash: str
    source_type: str = "static"
    fetched_at: str | None = None
    extract: str | None = None


class PendingEvidence(BaseModel):
    evidence_id: str
    type: EvidenceType
    kind: EvidenceKind = EvidenceKind.RAW
    title: str
    url: str | None = None
    snapshot_ref: str | None = None
    file_path: str | None = None
    note: str | None = None


class PendingChange(BaseModel):
    """One already-detected change. Contains NO AI prose."""

    schema_version: int = SCHEMA_VERSION
    change_id: str = Field(pattern=r"^chg-[0-9a-f]{24}$")
    competitor_id: str
    source_id: str
    source_type: str
    url: str
    detected_at: str
    change_type: Literal["new", "updated", "removed"]
    before_snapshot: SnapshotRef | None
    after_snapshot: SnapshotRef
    diff: str
    evidence: list[PendingEvidence] = Field(min_length=1)
    provenance: dict[str, str] = Field(default_factory=dict)
    analysis_status: Literal["pending"] = "pending"

    @field_validator("diff")
    @classmethod
    def _diff_is_deterministic_text(cls, value: str) -> str:
        return value.strip()


# --------------------------------------------------------------------------- #
# Intelligence output contract (written by Antigravity)
# --------------------------------------------------------------------------- #
class EvidenceRef(BaseModel):
    evidence_id: str
    role: Literal["before", "after", "supporting"] = "supporting"
    note: str | None = None


class IntelligenceRecord(BaseModel):
    """The single authoritative external-AI intelligence format."""

    schema_version: int = SCHEMA_VERSION
    intelligence_id: str = Field(pattern=r"^int-[0-9a-f]{24}$")
    change_id: str = Field(pattern=r"^chg-[0-9a-f]{24}$")
    competitor_id: str
    date: date
    summary: str = Field(min_length=1, max_length=600)
    topic_ids: list[str] = Field(default_factory=list)
    change_type: Literal["new", "updated", "removed"]
    impact: Impact
    confidence: Confidence
    relevance: Relevance = Relevance.MEDIUM
    decision: Decision
    xiaoshuyin_relevance: str = Field(min_length=1, max_length=1200)
    mechanism: str = Field(min_length=1, max_length=1200)
    why_it_matters: str = Field(min_length=1, max_length=1200)
    # Evidence-first: a conclusion without an evidence reference is invalid.
    evidence: list[EvidenceRef] = Field(min_length=1)
    human_review_status: HumanReviewStatus = HumanReviewStatus.UNREVIEWED
    analyst: str = "antigravity"
    notes: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow_iso)

    @field_validator("topic_ids")
    @classmethod
    def _clean_topics(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(t.strip() for t in value if t.strip()))

    @field_validator("evidence")
    @classmethod
    def _unique_evidence(cls, value: list[EvidenceRef]) -> list[EvidenceRef]:
        seen: dict[str, EvidenceRef] = {}
        for item in value:
            seen.setdefault(item.evidence_id, item)
        return list(seen.values())

    @model_validator(mode="after")
    def _stable_id(self) -> IntelligenceRecord:
        expected = stable_intelligence_id(self.change_id)
        if self.intelligence_id != expected:
            raise ValueError(
                f"intelligence_id must be deterministic: expected {expected} "
                f"for change_id {self.change_id}"
            )
        return self


# --------------------------------------------------------------------------- #
# Manual evidence + manual research queue
# --------------------------------------------------------------------------- #
class ManualEvidence(BaseModel):
    """evidence/manual/<evidence_id>/metadata.json"""

    schema_version: int = SCHEMA_VERSION
    evidence_id: str = Field(pattern=r"^evm-[a-z0-9][a-z0-9_-]*$")
    competitor_id: str
    captured_at: str
    evidence_type: EvidenceType
    title: str = Field(min_length=1)
    description: str = ""
    # What could not be collected automatically, e.g. "iOS App",
    # "WeChat Mini Program", "Logged-in onboarding", "Manual screenshot".
    source_label: str = Field(min_length=1)
    url: str | None = None
    files: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    related_change_id: str | None = None
    verification_state: VerificationState = VerificationState.UNVERIFIED
    captured_by: str = "human"
    notes: str | None = None

    @model_validator(mode="after")
    def _needs_an_artefact(self) -> ManualEvidence:
        if not self.files and not self.url:
            raise ValueError("manual evidence needs at least one file or an original url")
        return self


class RequiredEvidenceItem(BaseModel):
    label: str
    required: bool = True
    satisfied: bool = False


class ManualResearchRequest(BaseModel):
    """Simple, viewable queue. NOT a task-management system."""

    schema_version: int = SCHEMA_VERSION
    request_id: str = Field(pattern=r"^req-[0-9a-f]{20}$")
    competitor_id: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    research_question: str = Field(min_length=1)
    why_needed: str = Field(min_length=1)
    suggested_steps: list[str] = Field(min_length=1)
    required_evidence: list[RequiredEvidenceItem] = Field(min_length=1)
    status: ResearchStatus = ResearchStatus.OPEN
    created_at: str = Field(default_factory=utcnow_iso)
    created_by: str = "antigravity"
    related_change_id: str | None = None
    related_intelligence_id: str | None = None
    notes: str | None = None


# --------------------------------------------------------------------------- #
# Weekly pulse (derived from authoritative intelligence, never from a live LLM)
# --------------------------------------------------------------------------- #
class TopChange(BaseModel):
    intelligence_id: str
    competitor_id: str
    summary: str
    impact: Impact
    decision: Decision


class CrossCompetitorTheme(BaseModel):
    topic_id: str
    label: str
    intelligence_count: int
    competitor_ids: list[str]


class WeeklyPulse(BaseModel):
    week_start: str
    week_end: str
    total_changes: int = 0
    important_changes: int = 0
    top_changes: list[TopChange] = Field(default_factory=list)
    cross_competitor_themes: list[CrossCompetitorTheme] = Field(default_factory=list)
    by_decision: dict[str, int] = Field(default_factory=dict)
    manual_research_needed: int = 0


# --------------------------------------------------------------------------- #
# Compiled frontend artifact (derived, read-only renderer input)
# --------------------------------------------------------------------------- #
class RadarSummary(BaseModel):
    tracked_competitors: int = 0
    tracked_sources: int = 0
    detected_changes: int = 0
    important_changes: int = 0
    pending_intelligence: int = 0
    manual_research_requests: int = 0


class CompiledTopic(BaseModel):
    id: str
    label: str
    description: str
    intelligence_count: int = 0
    competitor_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class TrackedSource(BaseModel):
    source_id: str
    url: str
    source_type: str


class TimelineEvent(BaseModel):
    date: str
    intelligence_id: str
    title: str
    summary: str
    decision: Decision
    topic_ids: list[str] = Field(default_factory=list)
    change_id: str


class CompiledCompetitor(BaseModel):
    id: str
    name: str
    domain: str | None = None
    industry: str | None = None
    tier: int = 2
    why_tracked: str | None = None
    tracked_sources: list[TrackedSource] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    latest_intelligence_at: str | None = None
    intelligence_count: int = 0
    evidence_count: int = 0
    timeline: list[TimelineEvent] = Field(default_factory=list)


class CompiledIntelligence(BaseModel):
    intelligence_id: str
    change_id: str
    competitor_id: str
    date: str
    summary: str
    topic_ids: list[str] = Field(default_factory=list)
    change_type: str
    impact: Impact
    confidence: Confidence
    relevance: Relevance
    decision: Decision
    xiaoshuyin_relevance: str
    mechanism: str
    why_it_matters: str
    evidence_ids: list[str] = Field(default_factory=list)
    human_review_status: HumanReviewStatus
    analyst: str
    provenance: dict[str, str] = Field(default_factory=dict)


class CompiledEvidence(BaseModel):
    evidence_id: str
    intelligence_ids: list[str] = Field(default_factory=list)
    competitor_id: str = ""
    type: str
    kind: str
    url: str | None = None
    snapshot_ref: str | None = None
    content_hash: str | None = None
    captured_at: str | None = None
    title: str = ""
    extract: str | None = None
    image_path: str | None = None
    file_path: str | None = None
    verification_state: VerificationState = VerificationState.UNVERIFIED
    before_evidence_id: str | None = None
    after_evidence_id: str | None = None


class BeforeAfterPair(BaseModel):
    change_id: str
    competitor_id: str
    url: str
    before: CompiledEvidence | None = None
    after: CompiledEvidence | None = None
    diff: str = ""


class CompiledManualResearch(BaseModel):
    request_id: str
    competitor_id: str | None = None
    topic_ids: list[str] = Field(default_factory=list)
    research_question: str
    why_needed: str
    suggested_steps: list[str] = Field(default_factory=list)
    required_evidence: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    created_at: str
    created_by: str


class RadarSnapshot(BaseModel):
    """The ONE compiled artifact the frontend is allowed to read."""

    generated_at: str
    demo: bool = False
    authority: dict[str, str] = Field(default_factory=dict)
    summary: RadarSummary = Field(default_factory=RadarSummary)
    topics: list[CompiledTopic] = Field(default_factory=list)
    competitors: list[CompiledCompetitor] = Field(default_factory=list)
    intelligence: list[CompiledIntelligence] = Field(default_factory=list)
    evidence: list[CompiledEvidence] = Field(default_factory=list)
    before_after: list[BeforeAfterPair] = Field(default_factory=list)
    manual_research: list[CompiledManualResearch] = Field(default_factory=list)
    weekly: WeeklyPulse


__all__ = [
    "SCHEMA_VERSION",
    "BeforeAfterPair",
    "CompiledCompetitor",
    "CompiledEvidence",
    "CompiledIntelligence",
    "CompiledManualResearch",
    "CompiledTopic",
    "Confidence",
    "CrossCompetitorTheme",
    "Decision",
    "EvidenceKind",
    "EvidenceRef",
    "EvidenceType",
    "HumanReviewStatus",
    "Impact",
    "IntelligenceRecord",
    "ManualEvidence",
    "ManualResearchRequest",
    "PendingChange",
    "PendingEvidence",
    "RadarSnapshot",
    "RadarSummary",
    "Relevance",
    "RequiredEvidenceItem",
    "ResearchStatus",
    "SnapshotRef",
    "TimelineEvent",
    "TopChange",
    "Topic",
    "TopicsFile",
    "TrackedSource",
    "VerificationState",
    "WeeklyPulse",
    "stable_change_id",
    "stable_evidence_id",
    "stable_intelligence_id",
    "stable_request_id",
    "stable_source_id",
    "utcnow_iso",
]
