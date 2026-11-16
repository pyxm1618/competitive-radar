"""Authority tests: single sources of truth, no fabricated competitors,
no paid LLM API dependency, frontend read-only.
"""

from __future__ import annotations

import yaml
from pipeline.radar.contracts import (
    Confidence,
    Impact,
    IntelligenceRecord,
    ManualResearchRequest,
)
from pipeline.radar.paths import (
    COMPETITORS_PATH,
    PENDING_DIR,
    RECORDS_DIR,
    REPO_ROOT,
    TOPICS_PATH,
)

WEB_SRC = REPO_ROOT / "web" / "src"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pipeline.yml"

EXPECTED_TOPICS = {
    "problem-discovery",
    "assessment",
    "diagnosis",
    "ai-conversation",
    "action-plan",
    "family-collaboration",
    "child-participation",
    "tracking",
    "follow-up",
    "reflection",
    "report",
    "expert-service",
    "monetization",
}

FORBIDDEN_RUNTIME = (
    "changedetection.io",
    "rival",
    "archivebox",
    "karakeep",
    "appsmith",
)


def test_competitor_authority_contains_real_onboarding_set() -> None:
    data = yaml.safe_load(COMPETITORS_PATH.read_text(encoding="utf-8"))
    competitors = data["competitors"]
    assert len(competitors) == 55
    assert sum(c["tier"] == 1 for c in competitors) == 34
    assert sum(c["tier"] == 2 for c in competitors) == 21
    ids = [c["id"] for c in competitors]
    assert len(ids) == len(set(ids))
    assert all(c["tracked_urls"] for c in competitors)
    assert sum(len(c["tracked_urls"]) for c in competitors) == 102
    header = COMPETITORS_PATH.read_text(encoding="utf-8")
    assert "AUTHORITY" in header
    assert "confirmed 55-object onboarding list" in header


def test_topic_authority_is_single_and_complete() -> None:
    data = yaml.safe_load(TOPICS_PATH.read_text(encoding="utf-8"))
    ids = {t["id"] for t in data["topics"]}
    assert ids == EXPECTED_TOPICS
    assert len(ids) == len(data["topics"])


def test_only_one_competitor_registry_and_one_sample_fixture() -> None:
    registries = sorted((REPO_ROOT / "config").rglob("competitors*.yaml"))
    assert len(registries) == 2
    sample = REPO_ROOT / "config" / "examples" / "competitors.sample.yaml"
    assert sample.exists()
    assert "NOT AUTHORITATIVE" in sample.read_text(encoding="utf-8")


def test_single_intelligence_authority_paths() -> None:
    assert PENDING_DIR == REPO_ROOT / "data" / "intelligence" / "pending"
    assert RECORDS_DIR == REPO_ROOT / "data" / "intelligence" / "records"
    assert PENDING_DIR.parent == RECORDS_DIR.parent


def test_frontend_has_no_second_competitor_truth() -> None:
    loader = WEB_SRC / "lib" / "radar-data.ts"
    assert loader.exists(), "frontend must read the compiled artifact"
    assert "radar-static" in loader.read_text(encoding="utf-8")
    banned = ("sample-alpha", "sample-beta", "sample-gamma", "anthropic.com", "mistral.ai")
    offenders: list[str] = []
    for file in WEB_SRC.rglob("*"):
        if file.suffix not in {".ts", ".tsx", ".js", ".json"}:
            continue
        text = file.read_text(encoding="utf-8")
        for token in banned:
            if token in text:
                offenders.append(f"{file.relative_to(REPO_ROOT)}: {token}")
    assert not offenders, f"frontend hardcodes competitor data: {offenders}"


def test_no_parallel_old_frontend_static_data() -> None:
    assert not (REPO_ROOT / "web" / "public" / "api-static").exists()


def test_ci_never_requires_a_model_api_key() -> None:
    # Comments may legitimately explain that no keys are used; only check
    # executable YAML lines.
    active_lines = [
        line
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    text = "\n".join(active_lines)
    for key in ("GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        assert key not in text
    assert "compete run-all" not in text
    assert "radar collect" in text
    assert "radar prepare" in text


def test_default_workflow_is_no_key() -> None:
    env = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "COMPETE_LLM_PROVIDER=mock" in env
    assert "NO PAID MODEL KEY IS REQUIRED" in env
    config = (REPO_ROOT / "pipeline" / "config.py").read_text(encoding="utf-8")
    assert 'Field(default="mock", alias="COMPETE_LLM_PROVIDER")' in config


def test_radar_entry_point_registered() -> None:
    assert 'radar = "pipeline.radar_cli:app"' in (REPO_ROOT / "pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_no_second_runtime_platform_in_dependencies() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    for name in FORBIDDEN_RUNTIME:
        assert name not in pyproject


def test_upstream_attribution_retained() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Yassine Erradouani" in license_text
    notice = REPO_ROOT / "NOTICE"
    assert notice.exists()
    assert "yassnemo/compete" in notice.read_text(encoding="utf-8")


def test_antigravity_skill_exists_with_required_rules() -> None:
    skill = REPO_ROOT / ".agents" / "skills" / "competitor-intelligence" / "SKILL.md"
    assert skill.exists()
    text = skill.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "name: competitor-intelligence" in text
    for phrase in (
        "Impact",
        "Confidence",
        "act",
        "investigate",
        "watch",
        "ignore",
        "provenance",
        "evidence",
    ):
        assert phrase.lower() in text.lower()


def test_docs_authority_files_exist() -> None:
    for name in (
        "docs/AUTHORITY.md",
        "docs/ANTIGRAVITY_WORKFLOW.md",
        "docs/RUNBOOK.md",
        "docs/ARCHITECTURE.md",
        "docs/DATA_MODEL.md",
        "context/xiaoshuyin.md",
    ):
        assert (REPO_ROOT / name).exists(), name


def test_antigravity_resource_templates_are_schema_valid() -> None:
    """The Agent's copy-paste templates must be valid, not illustrative junk."""
    resources = REPO_ROOT / ".agents" / "skills" / "competitor-intelligence" / "resources"
    record = IntelligenceRecord.model_validate_json(
        (resources / "intelligence-template.json").read_text(encoding="utf-8")
    )
    assert record.impact == Impact.HIGH
    assert record.confidence == Confidence.LOW  # independent axes are demonstrated
    assert record.provenance.get("snapshot_after")
    request = ManualResearchRequest.model_validate_json(
        (resources / "manual-research-template.json").read_text(encoding="utf-8")
    )
    assert request.required_evidence
    assert all(item.label.startswith("SAMPLE") for item in request.required_evidence)


def test_generated_schemas_are_present() -> None:
    schemas = REPO_ROOT / "data" / "intelligence" / "schema"
    assert {p.name for p in schemas.glob("*.json")} == {
        "pending-change.schema.json",
        "intelligence-record.schema.json",
        "manual-evidence.schema.json",
        "manual-research-request.schema.json",
    }
