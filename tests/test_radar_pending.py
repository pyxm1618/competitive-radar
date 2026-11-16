"""Pipeline tests: collection config, snapshot persistence, diff, pending queue,
duplicate prevention and stable IDs — all without a model API key.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from pipeline.config import Settings, get_settings
from pipeline.radar.contracts import PendingChange, stable_change_id
from pipeline.radar.pending import (
    build_pending_change,
    load_pending,
    run_collect,
    run_prepare,
    unified_diff,
)
from pipeline.schemas import RawPage, SourceType
from pipeline.storage.duckdb_store import Warehouse

URL = "https://alpha.example.com/home"
OLD_TEXT = "pricing free tier nine dollars per month basic plan"
NEW_TEXT = "family shared task plan parent child collaboration long term tracking follow up"


def _settings(tmp_path: Path, monkeypatch) -> Settings:
    monkeypatch.setenv("COMPETE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("COMPETE_DUCKDB_PATH", str(tmp_path / "data" / "radar.duckdb"))
    # Force any hash change to be treated as a real change (deterministic test).
    monkeypatch.setenv("COMPETE_DIFF_SIMILARITY_THRESHOLD", "1.1")
    monkeypatch.setenv("COMPETE_LLM_PROVIDER", "mock")
    get_settings.cache_clear()
    settings = Settings()
    settings.ensure_dirs()
    return settings


def _config(tmp_path: Path) -> Path:
    """A test-only authority with the seeded URL declared active."""
    path = tmp_path / "competitors.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "competitors": [
                    {
                        "id": "sample-alpha",
                        "name": "Sample Alpha (test)",
                        "domain": "alpha.example.com",
                        "tier": 1,
                        "tracked_urls": [
                            {
                                "url": URL,
                                "source_type": "static",
                                "signal_hint": "other",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def _seed_snapshots(wh: Warehouse) -> tuple[str, str]:
    now = datetime.now(UTC)
    old_hash, new_hash = "hash-old-0001", "hash-new-0002"
    wh.upsert_raw_page(
        RawPage(
            id="snap-old",
            competitor_id="sample-alpha",
            url=URL,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=OLD_TEXT,
            content_hash=old_hash,
            fetched_at=now - timedelta(days=7),
        )
    )
    wh.upsert_raw_page(
        RawPage(
            id="snap-new",
            competitor_id="sample-alpha",
            url=URL,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=NEW_TEXT,
            content_hash=new_hash,
            fetched_at=now,
        )
    )
    return old_hash, new_hash


def test_collect_detect_prepare_end_to_end(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _config(tmp_path)
    wh = Warehouse.from_settings(settings)
    old_hash, new_hash = _seed_snapshots(wh)
    wh.close()

    # Avoid network I/O; this test targets Radar's reuse of the upstream diff.
    monkeypatch.setattr(
        "pipeline.radar.pending.collect_all",
        lambda _settings: {"urls": 0, "snapshots": 0, "failed": 0},
    )
    result = run_collect(settings, config)
    assert result.competitors == 1
    assert result.urls == 0  # no network in this test
    assert result.detected_changes == 1

    wh = Warehouse.from_settings(settings)
    rows = wh.query("SELECT change_id, summary, signal_type, prev_hash, new_hash FROM raw.changes")
    wh.close()
    assert len(rows) == 1
    change_id, summary, signal_type, prev_hash, stored_new_hash = rows[0]
    assert change_id == stable_change_id(URL, new_hash)
    assert summary is None  # NO AI prose in the change authority
    assert signal_type == "other"
    assert (prev_hash, stored_new_hash) == (old_hash, new_hash)

    out_dir = tmp_path / "pending"
    prepared = run_prepare(settings, path=config, out_dir=out_dir)
    assert prepared.changes_read == 1
    assert prepared.created == 1
    assert prepared.unchanged == 0
    assert prepared.skipped_missing_evidence == 0

    items = load_pending(out_dir)
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, PendingChange)
    assert item.change_id == change_id
    assert item.after_snapshot.snapshot_id == "snap-new"
    assert item.before_snapshot is not None
    assert item.before_snapshot.snapshot_id == "snap-old"
    assert len(item.evidence) == 2
    assert item.analysis_status == "pending"
    assert "+family shared task plan" in item.diff
    assert item.provenance["raw_evidence_table"] == "raw.raw_pages"
    assert item.provenance["diff_engine"] == "pipeline/detect/change.py"


def test_fresh_baseline_then_identical_then_real_change(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    settings.diff_similarity_threshold = 0.9
    config = _config(tmp_path)

    # Avoid network I/O while exercising the real Radar collect -> detect ->
    # persistence boundary. The seeded rows are exactly what collection writes.
    monkeypatch.setattr(
        "pipeline.radar.pending.collect_all",
        lambda _settings: {"urls": 1, "snapshots": 1, "failed": 0},
    )

    baseline_time = datetime(2026, 1, 1, tzinfo=UTC)
    wh = Warehouse.from_settings(settings)
    wh.upsert_raw_page(
        RawPage(
            id="snap-baseline",
            competitor_id="sample-alpha",
            url=URL,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=OLD_TEXT,
            content_hash="hash-baseline",
            fetched_at=baseline_time,
        )
    )
    wh.close()

    first = run_collect(settings, config)
    assert first.detected_changes == 0

    wh = Warehouse.from_settings(settings)
    assert wh.count("raw_pages") == 1
    assert wh.count("changes") == 0
    wh.close()

    out_dir = tmp_path / "pending"
    first_prepared = run_prepare(settings, path=config, out_dir=out_dir)
    assert first_prepared.changes_read == 0
    assert first_prepared.created == 0
    assert load_pending(out_dir) == []

    # Identical content has the same deterministic page id/hash and therefore
    # refreshes the baseline snapshot without creating a second snapshot/change.
    wh = Warehouse.from_settings(settings)
    wh.upsert_raw_page(
        RawPage(
            id="snap-baseline",
            competitor_id="sample-alpha",
            url=URL,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=OLD_TEXT,
            content_hash="hash-baseline",
            fetched_at=baseline_time + timedelta(days=1),
        )
    )
    wh.close()

    second = run_collect(settings, config)
    assert second.detected_changes == 0

    wh = Warehouse.from_settings(settings)
    assert wh.count("raw_pages") == 1
    assert wh.count("changes") == 0
    wh.close()

    second_prepared = run_prepare(settings, path=config, out_dir=out_dir)
    assert second_prepared.changes_read == 0
    assert second_prepared.created == 0
    assert load_pending(out_dir) == []

    # A later meaningful snapshot has a previous baseline and must retain the
    # existing deterministic UPDATED-change path.
    wh = Warehouse.from_settings(settings)
    wh.upsert_raw_page(
        RawPage(
            id="snap-changed",
            competitor_id="sample-alpha",
            url=URL,
            source_type=SourceType.STATIC,
            raw_html="<html></html>",
            clean_text=NEW_TEXT,
            content_hash="hash-changed",
            fetched_at=baseline_time + timedelta(days=2),
        )
    )
    wh.close()

    third = run_collect(settings, config)
    assert third.detected_changes == 1

    wh = Warehouse.from_settings(settings)
    rows = wh.query("SELECT change_type, prev_hash, new_hash FROM raw.changes ORDER BY detected_at")
    wh.close()
    assert rows == [("updated", "hash-baseline", "hash-changed")]

    third_prepared = run_prepare(settings, path=config, out_dir=out_dir)
    assert third_prepared.changes_read == 1
    assert third_prepared.created == 1

    items = load_pending(out_dir)
    assert len(items) == 1
    assert items[0].change_type == "updated"
    assert items[0].before_snapshot is not None
    assert items[0].before_snapshot.content_hash == "hash-baseline"
    assert items[0].after_snapshot.content_hash == "hash-changed"


def test_prepare_duplicate_prevention_and_stable_ids(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _config(tmp_path)
    wh = Warehouse.from_settings(settings)
    old_hash, new_hash = _seed_snapshots(wh)
    wh.insert_change(
        change_id=stable_change_id(URL, new_hash),
        competitor_id="sample-alpha",
        url=URL,
        signal_type="other",
        change_type="updated",
        summary=None,
        significance_score=None,
        prev_hash=old_hash,
        new_hash=new_hash,
        detected_at=datetime.now(UTC),
    )
    wh.close()

    out_dir = tmp_path / "pending"
    first = run_prepare(settings, path=config, out_dir=out_dir)
    file = out_dir / f"{stable_change_id(URL, new_hash)}.json"
    content = file.read_text(encoding="utf-8")

    second = run_prepare(settings, path=config, out_dir=out_dir)
    assert second.created == 0
    assert second.unchanged == 1
    assert second.updated == 0
    assert file.read_text(encoding="utf-8") == content
    assert json.loads(content)["change_id"] == first.change_ids[0]


def test_prepare_skips_missing_raw_evidence(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    config = _config(tmp_path)
    wh = Warehouse.from_settings(settings)
    _seed_snapshots(wh)
    wh.insert_change(
        change_id=stable_change_id(URL, "hash-that-was-never-collected"),
        competitor_id="sample-alpha",
        url=URL,
        signal_type="other",
        change_type="updated",
        summary=None,
        significance_score=None,
        prev_hash="hash-old-0001",
        new_hash="hash-that-was-never-collected",
        detected_at=datetime.now(UTC),
    )
    wh.close()

    prepared = run_prepare(settings, path=config, out_dir=tmp_path / "pending")
    assert prepared.skipped_missing_evidence == 1
    assert prepared.created == 0
    assert not list((tmp_path / "pending").glob("*.json"))


def test_pending_item_from_row_is_schema_valid(tmp_path: Path, monkeypatch) -> None:
    settings = _settings(tmp_path, monkeypatch)
    wh = Warehouse.from_settings(settings)
    old_hash, new_hash = _seed_snapshots(wh)
    from pipeline.radar.pending import _snapshot_rows

    snaps = _snapshot_rows(wh)
    wh.close()
    row = (
        stable_change_id(URL, new_hash),
        "sample-alpha",
        URL,
        "updated",
        old_hash,
        new_hash,
        datetime.now(UTC),
    )
    item = build_pending_change(row, snaps, {URL: "static"})
    assert item is not None
    assert item.source_id.startswith("src-")
    assert item.source_type == "static"
    assert item.model_dump(mode="json")["change_id"] == row[0]


def test_unified_diff_is_deterministic() -> None:
    assert unified_diff("a\nb", "a\nc") == unified_diff("a\nb", "a\nc")
    assert "-b" in unified_diff("a\nb", "a\nc")
    assert "+c" in unified_diff("a\nb", "a\nc")
    assert unified_diff("same", "same") == "(content hash changed but cleaned text is identical)"
