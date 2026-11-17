"""Tests for browser binary installation requirement detection."""

from __future__ import annotations

from pipeline.config import count_dynamic_sources, load_competitors, requires_browser
from pipeline.schemas import CompetitorsFile


def test_requires_browser_false_when_no_dynamic_sources() -> None:
    data = {
        "competitors": [
            {
                "id": "comp-a",
                "name": "Competitor A",
                "domain": "a.com",
                "tracked_urls": [
                    {"url": "https://a.com/news", "source_type": "static"},
                    {"url": "https://a.com/feed.xml", "source_type": "rss"},
                    {"url": "https://a.com/careers", "source_type": "jobs"},
                ],
            }
        ]
    }
    cfg = CompetitorsFile.model_validate(data)
    assert count_dynamic_sources(cfg) == 0
    assert requires_browser(cfg) is False


def test_requires_browser_true_when_dynamic_sources_present() -> None:
    data = {
        "competitors": [
            {
                "id": "comp-b",
                "name": "Competitor B",
                "domain": "b.com",
                "tracked_urls": [
                    {"url": "https://b.com/app", "source_type": "dynamic"},
                    {"url": "https://b.com/news", "source_type": "static"},
                ],
            },
            {
                "id": "comp-c",
                "name": "Competitor C",
                "domain": "c.com",
                "tracked_urls": [
                    {"url": "https://c.com/portal", "source_type": "dynamic"},
                ],
            },
        ]
    }
    cfg = CompetitorsFile.model_validate(data)
    assert count_dynamic_sources(cfg) == 2
    assert requires_browser(cfg) is True


def test_active_production_config_has_zero_dynamic_sources() -> None:
    cfg = load_competitors()
    assert len(cfg.competitors) == 55
    total_tracked = sum(len(c.tracked_urls) for c in cfg.competitors)
    assert total_tracked == 98
    assert count_dynamic_sources(cfg) == 0
    assert requires_browser(cfg) is False
