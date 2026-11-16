"""No-key monitoring steps: sync -> collect -> deterministic diff -> pending queue.

This module deliberately imports ONLY upstream collection / detection / storage
code. It never imports ``pipeline.extract.llm`` or ``pipeline.extract.runner``:
the default V1 workflow must run with no model API key installed.

Single Monitoring Authority:
  * change detection happens once, in ``pipeline.detect.change.detect_changes``;
  * the result is persisted in the upstream ``raw.changes`` table;
  * the pending queue is a deterministic DERIVED view of that table, with raw
    evidence references back into ``raw.raw_pages`` / Parquet.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, cast

from pipeline.collect.dispatch import collect_all
from pipeline.config import Settings, get_settings, load_competitors
from pipeline.detect.change import ChangeCandidate, detect_changes
from pipeline.extract.embeddings import get_embedder
from pipeline.logging_setup import get_logger
from pipeline.radar.contracts import (
    EvidenceKind,
    EvidenceType,
    PendingChange,
    PendingEvidence,
    SnapshotRef,
    stable_change_id,
    stable_evidence_id,
    stable_source_id,
)
from pipeline.radar.paths import (
    COMPETITORS_PATH,
    EXAMPLE_COMPETITORS_PATH,
    PENDING_DIR,
    REPO_ROOT,
    ensure_intelligence_dirs,
)
from pipeline.schemas import CompetitorsFile, SignalType
from pipeline.storage.duckdb_store import Warehouse

log = get_logger("radar.pending")

MAX_EXTRACT_CHARS = 4000
MAX_DIFF_LINES = 200


@dataclass
class CollectResult:
    competitors: int = 0
    urls: int = 0
    snapshots: int = 0
    failed: int = 0
    detected_changes: int = 0


@dataclass
class PrepareResult:
    changes_read: int = 0
    created: int = 0
    unchanged: int = 0
    updated: int = 0
    skipped_missing_evidence: int = 0
    change_ids: list[str] | None = None


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def load_competitors_from(path: Path | None = None) -> CompetitorsFile:
    """Load the competitor authority (or the clearly-labelled sample fixture)."""
    return load_competitors(path or COMPETITORS_PATH)


def build_hints(cfg: CompetitorsFile) -> dict[str, SignalType | None]:
    """Same URL hint mapping as upstream, without importing the LLM runner."""
    hints: dict[str, SignalType | None] = {}
    for comp in cfg.competitors:
        for tracked in comp.tracked_urls:
            url = str(tracked.url)
            hints[url] = tracked.signal_hint
            hints[url.rstrip("/")] = tracked.signal_hint
    return hints


def source_type_map(cfg: CompetitorsFile) -> dict[str, str]:
    out: dict[str, str] = {}
    for comp in cfg.competitors:
        for tracked in comp.tracked_urls:
            url = str(tracked.url)
            out[url] = str(tracked.source_type)
            out[url.rstrip("/")] = str(tracked.source_type)
    return out


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _clip(text: str | None) -> str:
    if not text:
        return ""
    return text[:MAX_EXTRACT_CHARS]


def unified_diff(before: str | None, after: str | None) -> str:
    """Deterministic textual rendering of a change that was ALREADY detected.

    This is not a second change-detection engine: it only renders the two
    snapshots selected by ``detect_changes`` for human / Agent inspection.
    """
    before_lines = (before or "").splitlines()
    after_lines = (after or "").splitlines()
    lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    if not lines:
        return "(content hash changed but cleaned text is identical)"
    if len(lines) > MAX_DIFF_LINES:
        lines = [*lines[:MAX_DIFF_LINES], f"… truncated ({len(lines)} diff lines total)"]
    return "\n".join(lines)


def _snapshot_rows(wh: Warehouse) -> dict[tuple[str, str], tuple]:
    """Latest raw.raw_pages row per (url, content_hash). Read-only."""
    rows = wh.query(
        """
        SELECT id, competitor_id, url, source_type, content_hash, clean_text, fetched_at
        FROM raw.raw_pages
        ORDER BY fetched_at DESC
        """
    )
    by_key: dict[tuple[str, str], tuple] = {}
    for row in rows:
        by_key.setdefault((str(row[2]), str(row[4])), row)
    return by_key


def _snapshot_ref(row: tuple | None) -> SnapshotRef | None:
    if row is None:
        return None
    return SnapshotRef(
        snapshot_id=str(row[0]),
        url=str(row[2]),
        content_hash=str(row[4]),
        source_type=str(row[3]),
        fetched_at=_iso(row[6]),
        extract=_clip(row[5]),
    )


def _evidence_for_snapshot(ref: SnapshotRef, role: str) -> PendingEvidence:
    is_before = role == "before"
    return PendingEvidence(
        evidence_id=stable_evidence_id(ref.snapshot_id, role),
        type=EvidenceType.SNAPSHOT_BEFORE if is_before else EvidenceType.SNAPSHOT_AFTER,
        kind=EvidenceKind.RAW,
        title=f"{'Before' if is_before else 'After'} snapshot: {ref.url}",
        url=ref.url,
        snapshot_ref=ref.snapshot_id,
        note=(
            "Reference into upstream raw.raw_pages / data/raw/*.parquet; "
            "not a copy of the raw evidence."
        ),
    )


# --------------------------------------------------------------------------- #
# radar collect — no AI, no keys
# --------------------------------------------------------------------------- #
def run_collect(settings: Settings | None = None, path: Path | None = None) -> CollectResult:
    """sync competitors -> collect snapshots -> deterministic diff -> raw.changes."""
    s = settings or get_settings()
    s.ensure_dirs()
    ensure_intelligence_dirs()
    cfg = load_competitors_from(path)

    # 1) Mirror the authority into the upstream warehouse (single writer).
    wh = Warehouse.from_settings(s)
    for c in cfg.competitors:
        urls_json = json.dumps([t.model_dump(mode="json") for t in c.tracked_urls])
        wh.upsert_competitor(c.id, c.name, c.domain, c.industry, c.tier, urls_json)
    wh.close()

    # 2) Upstream collection (static / dynamic / rss / jobs + Parquet landing).
    counts = collect_all(s)

    # 3) Upstream deterministic diff (content hash + embedding cosine).
    wh = Warehouse.from_settings(s)
    result = CollectResult(
        competitors=len(cfg.competitors),
        urls=counts["urls"],
        snapshots=counts["snapshots"],
        failed=counts["failed"],
    )
    try:
        embedder = get_embedder(s)
        candidates: list[ChangeCandidate] = detect_changes(
            wh, embedder, s.diff_similarity_threshold, build_hints(cfg)
        )
        snaps = _snapshot_rows(wh)
        for cand in candidates:
            after_row = snaps.get((cand.url, cand.new_hash))
            detected_at = _iso(after_row[6]) if after_row else _iso(datetime.now())
            wh.insert_change(
                change_id=stable_change_id(cand.url, cand.new_hash),
                competitor_id=cand.competitor_id,
                url=cand.url,
                # Deterministic placeholder, NOT AI-generated prose. Keeps the
                # upstream dbt `accepted_values` test valid with no signals.
                signal_type="other",
                change_type=str(cand.change_type),
                summary=None,
                significance_score=None,
                prev_hash=cand.prev_hash,
                new_hash=cand.new_hash,
                detected_at=detected_at,
            )
        result.detected_changes = len(candidates)
        log.info("detected %d change(s); persisted to raw.changes", len(candidates))
        return result
    finally:
        wh.close()


# --------------------------------------------------------------------------- #
# radar prepare — deterministic pending queue, no AI
# --------------------------------------------------------------------------- #
def build_pending_change(
    row: tuple,
    snaps: dict[tuple[str, str], tuple],
    types: dict[str, str],
) -> PendingChange | None:
    """Build one validated pending item from an authoritative raw.changes row."""
    change_id, competitor_id, url, change_type, prev_hash, new_hash, detected_at = row
    url = str(url)
    after_row = snaps.get((url, str(new_hash)))
    if after_row is None:
        return None  # never fabricate a snapshot
    before_row = snaps.get((url, str(prev_hash))) if prev_hash else None

    after = _snapshot_ref(after_row)
    before = _snapshot_ref(before_row)
    if after is None:
        return None

    evidence = [_evidence_for_snapshot(after, "after")]
    if before is not None:
        evidence.insert(0, _evidence_for_snapshot(before, "before"))

    source_type = types.get(url) or types.get(url.rstrip("/")) or str(after_row[3])
    raw_change_type = str(change_type)
    if raw_change_type not in ("new", "updated", "removed"):
        raise ValueError(f"invalid change_type in raw.changes: {raw_change_type}")
    return PendingChange(
        change_id=str(change_id),
        competitor_id=str(competitor_id),
        source_id=stable_source_id(url),
        source_type=source_type,
        url=url,
        detected_at=_iso(detected_at) or _iso(after.fetched_at) or "",
        change_type=cast(Literal["new", "updated", "removed"], raw_change_type),
        before_snapshot=before,
        after_snapshot=after,
        diff=unified_diff(_clip(before_row[5]) if before_row else None, _clip(after_row[5])),
        evidence=evidence,
        provenance={
            "change_authority": "raw.changes (deterministic snapshot diff)",
            "raw_evidence_table": "raw.raw_pages",
            "raw_evidence_parquet": "data/raw/",
            "competitor_authority": str(COMPETITORS_PATH.relative_to(REPO_ROOT)),
            "snapshot_before": before.snapshot_id if before else "",
            "snapshot_after": after.snapshot_id,
            "diff_engine": "pipeline/detect/change.py",
        },
    )


def run_prepare(
    settings: Settings | None = None,
    *,
    path: Path | None = None,
    out_dir: Path | None = None,
) -> PrepareResult:
    """Take detected changes -> normalize -> generate/update the pending queue."""
    s = settings or get_settings()
    s.ensure_dirs()
    ensure_intelligence_dirs()
    target = out_dir or PENDING_DIR
    target.mkdir(parents=True, exist_ok=True)
    cfg = load_competitors_from(path)
    types = source_type_map(cfg)

    wh = Warehouse.from_settings(s, read_only=False)
    result = PrepareResult(change_ids=[])
    try:
        rows = wh.query(
            """
            SELECT change_id, competitor_id, url, change_type, prev_hash, new_hash, detected_at
            FROM raw.changes
            ORDER BY change_id
            """
        )
        snaps = _snapshot_rows(wh)
        result.changes_read = len(rows)
        for row in rows:
            item = build_pending_change(row, snaps, types)
            if item is None:
                result.skipped_missing_evidence += 1
                log.warning("skipping %s: after snapshot not found in raw.raw_pages", row[0])
                continue
            payload = (
                json.dumps(
                    item.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
                )
                + "\n"
            )
            dest = target / f"{item.change_id}.json"
            if dest.exists():
                previous = dest.read_text(encoding="utf-8")
                if previous == payload:
                    result.unchanged += 1
                else:
                    dest.write_text(payload, encoding="utf-8")
                    result.updated += 1
            else:
                dest.write_text(payload, encoding="utf-8")
                result.created += 1
            if result.change_ids is not None:
                result.change_ids.append(item.change_id)
        log.info(
            "pending queue: %d created, %d unchanged, %d updated, %d skipped",
            result.created,
            result.unchanged,
            result.updated,
            result.skipped_missing_evidence,
        )
        return result
    finally:
        wh.close()


def load_pending(directory: Path | None = None) -> list[PendingChange]:
    """Load and validate every authoritative pending item."""
    root = directory or PENDING_DIR
    if not root.exists():
        return []
    items: list[PendingChange] = []
    for file in sorted(root.glob("*.json")):
        items.append(PendingChange.model_validate_json(file.read_text(encoding="utf-8")))
    return items


__all__ = [
    "EXAMPLE_COMPETITORS_PATH",
    "CollectResult",
    "PrepareResult",
    "build_hints",
    "build_pending_change",
    "load_competitors_from",
    "load_pending",
    "run_collect",
    "run_prepare",
    "source_type_map",
    "unified_diff",
]
