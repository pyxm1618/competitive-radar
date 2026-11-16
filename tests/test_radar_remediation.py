"""Targeted remediation regressions for PR #1 audit findings."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pipeline.config import Settings, get_settings
from pipeline.radar import compile as radar_compile_module
from pipeline.radar import manual as manual_module
from pipeline.radar.contracts import (
    IntelligenceRecord,
    ManualEvidence,
    ManualResearchRequest,
    PendingChange,
    PendingEvidence,
    SnapshotRef,
    stable_change_id,
    stable_evidence_id,
    stable_intelligence_id,
    stable_source_id,
)
from pipeline.radar.manual import copy_manual_assets, load_manual_evidence
from pipeline.radar.paths import EXAMPLE_COMPETITORS_PATH, REPO_ROOT, TOPICS_PATH
from pipeline.radar.pending import load_pending, run_collect, run_prepare
from pipeline.radar.validate import validate_intelligence
from pipeline.schemas import CompetitorsFile, RawPage, SourceType
from pipeline.storage.duckdb_store import Warehouse
from pydantic import ValidationError

URL_A = "https://alpha.example.com/home"
URL_A2 = "https://alpha.example.com/changelog"
URL_B = "https://beta.example.com/features"
BASE_TIME = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def _settings(tmp_path: Path, monkeypatch) -> Settings:
    monkeypatch.setenv("COMPETE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("COMPETE_DUCKDB_PATH", str(tmp_path / "data" / "radar.duckdb"))
    monkeypatch.setenv("COMPETE_DIFF_SIMILARITY_THRESHOLD", "1.1")
    monkeypatch.setenv("COMPETE_LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    settings = Settings()
    settings.ensure_dirs()
    monkeypatch.setattr(
        "pipeline.radar.pending.collect_all",
        lambda _settings: {"urls": 0, "snapshots": 0, "failed": 0},
    )
    return settings


def _competitor(competitor_id: str, domain: str, urls: list[str]) -> dict:
    return {
        "id": competitor_id,
        "name": competitor_id,
        "domain": domain,
        "tier": 1,
        "tracked_urls": [
            {"url": url, "source_type": "static", "signal_hint": "other"} for url in urls
        ],
    }


def _write_config(tmp_path: Path, competitors: list[dict]) -> Path:
    path = tmp_path / "competitors.yaml"
    path.write_text(
        yaml.safe_dump({"competitors": competitors}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _snapshot(
    wh: Warehouse,
    *,
    snapshot_id: str,
    competitor_id: str,
    url: str,
    content_hash: str,
    text: str,
    when: datetime,
) -> None:
    wh.upsert_raw_page(
        RawPage(
            id=snapshot_id,
            competitor_id=competitor_id,
            url=url,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=text,
            content_hash=content_hash,
            fetched_at=when,
        )
    )


def _write_pending(
    directory: Path,
    *,
    competitor_id: str,
    url: str,
    snapshot_id: str,
    content_hash: str,
) -> PendingChange:
    directory.mkdir(parents=True, exist_ok=True)
    change_id = stable_change_id(url, content_hash)
    after = SnapshotRef(
        snapshot_id=snapshot_id,
        url=url,
        content_hash=content_hash,
        source_type="static",
        fetched_at="2026-11-10T09:00:00Z",
        extract="sample evidence",
    )
    evidence = PendingEvidence(
        evidence_id=stable_evidence_id(snapshot_id, "after"),
        type="snapshot_after",
        kind="raw",
        title=f"After snapshot: {url}",
        url=url,
        snapshot_ref=snapshot_id,
    )
    item = PendingChange(
        change_id=change_id,
        competitor_id=competitor_id,
        source_id=stable_source_id(url),
        source_type="static",
        url=url,
        detected_at="2026-11-10T09:00:00Z",
        change_type="new",
        before_snapshot=None,
        after_snapshot=after,
        diff="+sample evidence",
        evidence=[evidence],
        provenance={"url": url},
    )
    (directory / f"{change_id}.json").write_text(
        item.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return item


def _record(
    item: PendingChange,
    evidence_id: str,
    *,
    competitor_id: str | None = None,
    change_id: str | None = None,
    provenance_url: str | None = None,
) -> IntelligenceRecord:
    cid = change_id or item.change_id
    return IntelligenceRecord.model_validate(
        {
            "intelligence_id": stable_intelligence_id(cid),
            "change_id": cid,
            "competitor_id": competitor_id or item.competitor_id,
            "date": "2026-11-10",
            "summary": "A grounded sample change.",
            "topic_ids": ["action-plan"],
            "change_type": "new",
            "impact": "medium",
            "confidence": "high",
            "relevance": "medium",
            "decision": "watch",
            "xiaoshuyin_relevance": "Relevant to the action-plan design question.",
            "mechanism": "A deterministic sample mechanism.",
            "why_it_matters": "The evidence is sufficient for this regression fixture.",
            "evidence": [{"evidence_id": evidence_id, "role": "after"}],
            "human_review_status": "unreviewed",
            "provenance": {"url": provenance_url or item.url},
        }
    )


def _write_record(directory: Path, record: IntelligenceRecord) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{record.intelligence_id}.json").write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _write_manual(
    root: Path,
    *,
    evidence_id: str,
    competitor_id: str,
    related_change_id: str | None = None,
    files: list[str] | None = None,
    url: str | None = "https://example.com/manual-source",
) -> ManualEvidence:
    folder = root / evidence_id
    folder.mkdir(parents=True, exist_ok=True)
    item = ManualEvidence(
        evidence_id=evidence_id,
        competitor_id=competitor_id,
        captured_at="2026-11-10T10:00:00Z",
        evidence_type="manual_note",
        title="Manual evidence fixture",
        description="Manual evidence fixture",
        source_label="Manual test",
        url=url,
        files=files or [],
        related_change_id=related_change_id,
    )
    (folder / "metadata.json").write_text(
        item.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return item


def test_processed_hash_is_not_redetected_but_real_next_hash_is(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _write_config(
        tmp_path,
        [_competitor("sample-alpha", "alpha.example.com", [URL_A])],
    )
    wh = Warehouse.from_settings(settings)
    _snapshot(
        wh,
        snapshot_id="snap-h1",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="h1",
        text="old content",
        when=BASE_TIME - timedelta(days=1),
    )
    _snapshot(
        wh,
        snapshot_id="snap-h2",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="h2",
        text="new content",
        when=BASE_TIME,
    )
    wh.close()

    first = run_collect(settings, config)
    assert first.detected_changes == 1

    pending_dir = tmp_path / "pending"
    prepared = run_prepare(settings, path=config, out_dir=pending_dir)
    assert prepared.created == 1
    item = load_pending(pending_dir)[0]

    records_dir = tmp_path / "records"
    _write_record(records_dir, _record(item, item.evidence[-1].evidence_id))
    assert list(records_dir.glob("*.json"))

    pending_before = (pending_dir / f"{item.change_id}.json").read_text(encoding="utf-8")
    wh = Warehouse.from_settings(settings)
    detected_before = wh.query(
        "SELECT detected_at FROM raw.changes WHERE change_id = ?",
        [item.change_id],
    )[0][0]
    wh.close()

    same = run_collect(settings, config)
    assert same.detected_changes == 0
    prepared_again = run_prepare(settings, path=config, out_dir=pending_dir)
    assert prepared_again.created == 0
    assert prepared_again.unchanged == 1
    assert (pending_dir / f"{item.change_id}.json").read_text(encoding="utf-8") == pending_before

    wh = Warehouse.from_settings(settings)
    detected_after = wh.query(
        "SELECT detected_at FROM raw.changes WHERE change_id = ?",
        [item.change_id],
    )[0][0]
    assert detected_after == detected_before

    _snapshot(
        wh,
        snapshot_id="snap-h3",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="h3",
        text="genuinely newer content",
        when=BASE_TIME + timedelta(days=1),
    )
    wh.close()

    next_change = run_collect(settings, config)
    assert next_change.detected_changes == 1
    wh = Warehouse.from_settings(settings)
    ids = {row[0] for row in wh.query("SELECT change_id FROM raw.changes")}
    wh.close()
    assert stable_change_id(URL_A, "h3") in ids


def test_evidence_ownership_rejects_cross_competitor_and_wrong_change(
    tmp_path: Path,
) -> None:
    config = _write_config(
        tmp_path,
        [
            _competitor("sample-alpha", "alpha.example.com", [URL_A, URL_A2]),
            _competitor("sample-beta", "beta.example.com", [URL_B]),
        ],
    )
    pending_dir = tmp_path / "pending"
    alpha = _write_pending(
        pending_dir,
        competitor_id="sample-alpha",
        url=URL_A,
        snapshot_id="snap-alpha",
        content_hash="alpha-h1",
    )
    alpha_other = _write_pending(
        pending_dir,
        competitor_id="sample-alpha",
        url=URL_A2,
        snapshot_id="snap-alpha-other",
        content_hash="alpha-h2",
    )
    beta = _write_pending(
        pending_dir,
        competitor_id="sample-beta",
        url=URL_B,
        snapshot_id="snap-beta",
        content_hash="beta-h1",
    )
    manual_root = tmp_path / "manual"
    alpha_manual = _write_manual(
        manual_root,
        evidence_id="evm-alpha",
        competitor_id="sample-alpha",
    )
    alpha_wrong_change = _write_manual(
        manual_root,
        evidence_id="evm-alpha-other",
        competitor_id="sample-alpha",
        related_change_id=alpha_other.change_id,
    )
    beta_manual = _write_manual(
        manual_root,
        evidence_id="evm-beta",
        competitor_id="sample-beta",
    )

    def validate(record: IntelligenceRecord, label: str):
        records = tmp_path / f"records-{label}"
        _write_record(records, record)
        return validate_intelligence(
            records_dir=records,
            pending_dir=pending_dir,
            competitors_path=config,
            topics_path=TOPICS_PATH,
            manual_root=manual_root,
        )

    cross_raw = validate(_record(alpha, beta.evidence[0].evidence_id), "cross-raw")
    assert not cross_raw.ok
    assert any("cross-competitor evidence" in error for error in cross_raw.errors)

    cross_manual = validate(_record(alpha, beta_manual.evidence_id), "cross-manual")
    assert not cross_manual.ok
    assert any("cross-competitor evidence" in error for error in cross_manual.errors)

    wrong_raw = validate(_record(alpha, alpha_other.evidence[0].evidence_id), "wrong-raw")
    assert not wrong_raw.ok
    assert any("raw evidence" in error and "belongs to change" in error for error in wrong_raw.errors)

    wrong_manual = validate(_record(alpha, alpha_wrong_change.evidence_id), "wrong-manual")
    assert not wrong_manual.ok
    assert any(
        "manual evidence" in error and "is bound to change" in error
        for error in wrong_manual.errors
    )

    correct_raw = validate(_record(alpha, alpha.evidence[0].evidence_id), "correct-raw")
    assert correct_raw.ok, correct_raw.errors

    correct_manual = validate(_record(alpha, alpha_manual.evidence_id), "correct-manual")
    assert correct_manual.ok, correct_manual.errors


def test_retired_competitor_is_not_detected_or_prepared_and_raw_history_remains(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _write_config(
        tmp_path,
        [_competitor("sample-alpha", "alpha.example.com", [URL_A])],
    )
    wh = Warehouse.from_settings(settings)
    _snapshot(
        wh,
        snapshot_id="snap-a-old",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="a-old",
        text="old",
        when=BASE_TIME - timedelta(days=1),
    )
    _snapshot(
        wh,
        snapshot_id="snap-a-new",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="a-new",
        text="new",
        when=BASE_TIME,
    )
    wh.close()

    assert run_collect(settings, config).detected_changes == 1
    pending_dir = tmp_path / "pending"
    assert run_prepare(settings, path=config, out_dir=pending_dir).created == 1
    assert len(load_pending(pending_dir)) == 1

    config.write_text(yaml.safe_dump({"competitors": []}), encoding="utf-8")
    assert run_collect(settings, config).detected_changes == 0
    retired = run_prepare(settings, path=config, out_dir=pending_dir)
    assert retired.changes_read == 0
    assert retired.ignored_inactive == 1
    assert retired.removed_inactive == 1
    assert load_pending(pending_dir) == []

    wh = Warehouse.from_settings(settings)
    assert wh.count("raw_pages") == 2
    assert wh.count("changes") == 1
    wh.close()


def test_removed_url_stops_detection_and_pending_while_other_url_continues(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _write_config(
        tmp_path,
        [_competitor("sample-alpha", "alpha.example.com", [URL_A, URL_A2])],
    )
    wh = Warehouse.from_settings(settings)
    for suffix, url in (("home", URL_A), ("changelog", URL_A2)):
        _snapshot(
            wh,
            snapshot_id=f"snap-{suffix}-old",
            competitor_id="sample-alpha",
            url=url,
            content_hash=f"{suffix}-old",
            text=f"{suffix} old",
            when=BASE_TIME - timedelta(days=1),
        )
        _snapshot(
            wh,
            snapshot_id=f"snap-{suffix}-new",
            competitor_id="sample-alpha",
            url=url,
            content_hash=f"{suffix}-new",
            text=f"{suffix} new",
            when=BASE_TIME,
        )
    wh.close()

    assert run_collect(settings, config).detected_changes == 2
    pending_dir = tmp_path / "pending"
    assert run_prepare(settings, path=config, out_dir=pending_dir).created == 2

    config = _write_config(
        tmp_path,
        [_competitor("sample-alpha", "alpha.example.com", [URL_A2])],
    )
    wh = Warehouse.from_settings(settings)
    _snapshot(
        wh,
        snapshot_id="snap-home-h3",
        competitor_id="sample-alpha",
        url=URL_A,
        content_hash="home-h3",
        text="home h3 retired",
        when=BASE_TIME + timedelta(days=1),
    )
    _snapshot(
        wh,
        snapshot_id="snap-changelog-h3",
        competitor_id="sample-alpha",
        url=URL_A2,
        content_hash="changelog-h3",
        text="changelog h3 active",
        when=BASE_TIME + timedelta(days=1),
    )
    wh.close()

    result = run_collect(settings, config)
    assert result.detected_changes == 1

    prepared = run_prepare(settings, path=config, out_dir=pending_dir)
    assert prepared.ignored_inactive == 1
    current = load_pending(pending_dir)
    assert current
    assert all(item.url == URL_A2 for item in current)

    wh = Warehouse.from_settings(settings)
    change_ids = {row[0] for row in wh.query("SELECT change_id FROM raw.changes")}
    raw_urls = {row[0] for row in wh.query("SELECT DISTINCT url FROM raw.raw_pages")}
    wh.close()
    assert stable_change_id(URL_A, "home-h3") not in change_ids
    assert stable_change_id(URL_A2, "changelog-h3") in change_ids
    assert URL_A in raw_urls


def test_compiler_excludes_retired_competitor_but_keeps_history_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = yaml.safe_load(EXAMPLE_COMPETITORS_PATH.read_text(encoding="utf-8"))
    data["competitors"] = [
        row for row in data["competitors"] if row["id"] != "sample-gamma"
    ]
    config = tmp_path / "competitors-no-gamma.yaml"
    config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(radar_compile_module, "EXAMPLE_COMPETITORS_PATH", config)

    snapshot = radar_compile_module.compile_radar(demo=True, write=False)
    assert all(c.id != "sample-gamma" for c in snapshot.competitors)
    assert all(i.competitor_id != "sample-gamma" for i in snapshot.intelligence)
    assert all(e.competitor_id != "sample-gamma" for e in snapshot.evidence)
    assert all(pair.competitor_id != "sample-gamma" for pair in snapshot.before_after)
    assert len(snapshot.intelligence) == 3


def test_compiler_excludes_removed_tracked_url_but_keeps_other_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = copy.deepcopy(
        yaml.safe_load(EXAMPLE_COMPETITORS_PATH.read_text(encoding="utf-8"))
    )
    alpha = next(row for row in data["competitors"] if row["id"] == "sample-alpha")
    alpha["tracked_urls"] = [
        row for row in alpha["tracked_urls"] if row["url"] != URL_A2
    ]
    config = tmp_path / "competitors-no-changelog.yaml"
    config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(radar_compile_module, "EXAMPLE_COMPETITORS_PATH", config)

    snapshot = radar_compile_module.compile_radar(demo=True, write=False)
    assert all(pair.url != URL_A2 for pair in snapshot.before_after)
    alpha_compiled = next(c for c in snapshot.competitors if c.id == "sample-alpha")
    assert len(alpha_compiled.timeline) == 1
    assert len(snapshot.intelligence) == 3


def test_duplicate_competitor_ids_are_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate competitor ids"):
        CompetitorsFile.model_validate(
            {
                "competitors": [
                    _competitor("duplicate", "one.example.com", [URL_A]),
                    _competitor("duplicate", "two.example.com", [URL_B]),
                ]
            }
        )


@pytest.mark.parametrize("asset_name", ["../secret.txt", "/tmp/secret.txt"])
def test_manual_evidence_rejects_path_escape(tmp_path: Path, asset_name: str) -> None:
    root = tmp_path / "manual"
    _write_manual(
        root,
        evidence_id="evm-path-test",
        competitor_id="sample-alpha",
        files=[asset_name],
        url=None,
    )
    with pytest.raises(ValueError, match="must stay inside"):
        load_manual_evidence(root)


def test_manual_evidence_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "manual"
    folder = root / "evm-symlink-test"
    folder.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (folder / "escape.txt").symlink_to(outside)
    _write_manual(
        root,
        evidence_id="evm-symlink-test",
        competitor_id="sample-alpha",
        files=["escape.txt"],
        url=None,
    )
    with pytest.raises(ValueError, match="resolves outside"):
        load_manual_evidence(root)


def test_manual_evidence_normal_asset_loads_and_copies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "manual"
    item = _write_manual(
        root,
        evidence_id="evm-normal",
        competitor_id="sample-alpha",
        files=["screenshot.png"],
        url=None,
    )
    (root / item.evidence_id / "screenshot.png").write_bytes(b"png")
    loaded = load_manual_evidence(root)
    assert len(loaded) == 1

    public = tmp_path / "public-evidence"
    monkeypatch.setattr(manual_module, "PUBLIC_EVIDENCE_DIR", public)
    assert copy_manual_assets(loaded, root) == 1
    assert (public / item.evidence_id / "screenshot.png").is_file()


def _json_example_after(text: str, heading: str) -> dict:
    section = text.split(heading, 1)[1]
    fence = chr(96) * 3
    block = section.split(f"{fence}json", 1)[1].split(fence, 1)[0]
    return json.loads(block)


def test_runbook_manual_examples_match_real_contracts() -> None:
    text = (REPO_ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    manual = _json_example_after(text, "### Add manual evidence")
    research = _json_example_after(text, "### Create a manual research request")
    ManualEvidence.model_validate(manual)
    ManualResearchRequest.model_validate(research)
