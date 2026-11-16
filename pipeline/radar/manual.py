"""Manual evidence + manual research queue contracts.

Manual evidence covers surfaces that cannot be collected automatically:
iOS / Android apps, WeChat Mini Programs, login-walled onboarding, CAPTCHA
flows, manual screenshots and manually recorded product flows.

Directory contract (one folder per evidence item):

    evidence/manual/<evidence_id>/
        metadata.json      # ManualEvidence model
        <asset files>      # screenshots / recordings / pdfs / notes

No asset is fabricated. A metadata file that references a missing asset is
reported with verification_state = missing instead of being silently fixed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from pipeline.logging_setup import get_logger
from pipeline.radar.contracts import (
    CompiledEvidence,
    CompiledManualResearch,
    EvidenceKind,
    ManualEvidence,
    ManualResearchRequest,
    VerificationState,
)
from pipeline.radar.paths import MANUAL_EVIDENCE_DIR, PUBLIC_EVIDENCE_DIR, RESEARCH_DIR

log = get_logger("radar.manual")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


def _contained_asset_path(root: Path, name: str) -> Path:
    """Resolve a manual asset while preventing absolute/traversal/symlink escape."""
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"manual evidence asset must stay inside its evidence folder: {name}")
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"manual evidence asset resolves outside its evidence folder: {name}"
        ) from exc
    return resolved


def load_manual_evidence(root: Path | None = None) -> list[ManualEvidence]:
    """Load every metadata.json under the manual evidence directory."""
    directory = root or MANUAL_EVIDENCE_DIR
    if not directory.exists():
        return []
    items: list[ManualEvidence] = []
    for meta in sorted(directory.glob("*/metadata.json")):
        item = ManualEvidence.model_validate_json(meta.read_text(encoding="utf-8"))
        missing = [
            name
            for name in item.files
            if not _contained_asset_path(meta.parent, name).is_file()
        ]
        if missing:
            log.warning("%s references missing asset(s): %s", item.evidence_id, ", ".join(missing))
            item = item.model_copy(update={"verification_state": VerificationState.MISSING})
        items.append(item)
    return items


def load_research_requests(root: Path | None = None) -> list[ManualResearchRequest]:
    """Load the simple viewable manual research queue."""
    directory = root or RESEARCH_DIR
    if not directory.exists():
        return []
    return [
        ManualResearchRequest.model_validate_json(p.read_text(encoding="utf-8"))
        for p in sorted(directory.glob("*.json"))
    ]


def copy_manual_assets(items: list[ManualEvidence], root: Path | None = None) -> int:
    """Copy manual evidence assets into the static public directory.

    The frontend only reads the compiled artifact + these public files; it never
    reads the repository filesystem at runtime.
    """
    source_root = root or MANUAL_EVIDENCE_DIR
    copied = 0
    # Clear stale public assets so a demo build can never leave sample files
    # behind in the authoritative snapshot (mirrors upstream export behaviour).
    if PUBLIC_EVIDENCE_DIR.exists():
        # Only remove files. Empty directories are harmless (git does not track
        # them) and avoiding rmdir keeps this portable across sandboxed hosts.
        for stale in PUBLIC_EVIDENCE_DIR.rglob("*"):
            if stale.is_file():
                stale.unlink()
    for item in items:
        src = source_root / item.evidence_id
        dst = PUBLIC_EVIDENCE_DIR / item.evidence_id
        dst.mkdir(parents=True, exist_ok=True)
        for name in item.files:
            origin = _contained_asset_path(src, name)
            destination = _contained_asset_path(dst, name)
            if origin.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origin, destination)
                copied += 1
    return copied


def compile_manual_evidence(items: list[ManualEvidence]) -> list[CompiledEvidence]:
    out: list[CompiledEvidence] = []
    for item in items:
        image = next((f for f in item.files if Path(f).suffix.lower() in IMAGE_SUFFIXES), None)
        primary = item.files[0] if item.files else None
        out.append(
            CompiledEvidence(
                evidence_id=item.evidence_id,
                competitor_id=item.competitor_id,
                type=str(item.evidence_type),
                kind=str(EvidenceKind.MANUAL),
                url=item.url,
                captured_at=item.captured_at,
                title=item.title,
                extract=item.description or None,
                image_path=(
                    f"/evidence/{item.evidence_id}/{image}"
                    if image and item.verification_state != VerificationState.MISSING
                    else None
                ),
                file_path=(
                    f"/evidence/{item.evidence_id}/{primary}"
                    if primary and item.verification_state != VerificationState.MISSING
                    else None
                ),
                verification_state=item.verification_state,
            )
        )
    return out


def compile_research_requests(items: list[ManualResearchRequest]) -> list[CompiledManualResearch]:
    return [
        CompiledManualResearch(
            request_id=r.request_id,
            competitor_id=r.competitor_id,
            topic_ids=r.topic_ids,
            research_question=r.research_question,
            why_needed=r.why_needed,
            suggested_steps=r.suggested_steps,
            required_evidence=[e.model_dump(mode="json") for e in r.required_evidence],
            status=str(r.status),
            created_at=r.created_at,
            created_by=r.created_by,
        )
        for r in items
    ]


def write_research_request(request: ManualResearchRequest, root: Path | None = None) -> Path:
    """Persist a manual research request deterministically (used by tooling/tests)."""
    directory = root or RESEARCH_DIR
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{request.request_id}.json"
    payload = (
        json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    dest.write_text(payload, encoding="utf-8")
    return dest


__all__ = [
    "compile_manual_evidence",
    "compile_research_requests",
    "copy_manual_assets",
    "load_manual_evidence",
    "load_research_requests",
    "write_research_request",
]
