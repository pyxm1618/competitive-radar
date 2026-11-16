"""Canonical paths for Competitive Radar V1.

There is exactly one location for each authority. Import these constants instead
of hardcoding paths in the CLI, build step, or tests.
"""

from __future__ import annotations

from pathlib import Path

# pipeline/radar/paths.py -> pipeline/radar -> pipeline -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

# --- authorities ----------------------------------------------------------- #
CONFIG_DIR = REPO_ROOT / "config"
COMPETITORS_PATH = CONFIG_DIR / "competitors.yaml"
TOPICS_PATH = CONFIG_DIR / "topics.yaml"
EXAMPLE_COMPETITORS_PATH = CONFIG_DIR / "examples" / "competitors.sample.yaml"

# --- intelligence (external-AI file protocol) ------------------------------ #
INTELLIGENCE_DIR = REPO_ROOT / "data" / "intelligence"
PENDING_DIR = INTELLIGENCE_DIR / "pending"
RECORDS_DIR = INTELLIGENCE_DIR / "records"
RESEARCH_DIR = INTELLIGENCE_DIR / "research"
WEEKLY_DIR = INTELLIGENCE_DIR / "weekly"
SCHEMA_DIR = INTELLIGENCE_DIR / "schema"

# --- manual evidence ------------------------------------------------------- #
MANUAL_EVIDENCE_DIR = REPO_ROOT / "evidence" / "manual"

# --- demo fixtures (never authoritative) ----------------------------------- #
EXAMPLES_DIR = REPO_ROOT / "examples"
EXAMPLE_PENDING_DIR = EXAMPLES_DIR / "intelligence" / "pending"
EXAMPLE_RECORDS_DIR = EXAMPLES_DIR / "intelligence" / "records"
EXAMPLE_RESEARCH_DIR = EXAMPLES_DIR / "intelligence" / "research"
EXAMPLE_MANUAL_EVIDENCE_DIR = EXAMPLES_DIR / "evidence" / "manual"

# --- compiled static artifact (frontend renderer input) -------------------- #
STATIC_DIR = REPO_ROOT / "web" / "public" / "radar-static"
STATIC_RADAR_JSON = STATIC_DIR / "radar.json"
PUBLIC_EVIDENCE_DIR = REPO_ROOT / "web" / "public" / "evidence"

CONTEXT_DIR = REPO_ROOT / "context"
XIAOSHUYIN_CONTEXT = CONTEXT_DIR / "xiaoshuyin.md"


def ensure_intelligence_dirs() -> None:
    """Create every authoritative directory if missing (idempotent)."""
    for path in (
        INTELLIGENCE_DIR,
        PENDING_DIR,
        RECORDS_DIR,
        RESEARCH_DIR,
        WEEKLY_DIR,
        SCHEMA_DIR,
        MANUAL_EVIDENCE_DIR,
        STATIC_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
