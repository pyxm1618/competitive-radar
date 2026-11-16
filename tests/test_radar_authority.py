"""Authority tests: single sources of truth, no fabricated competitors,
no paid LLM API dependency, frontend read-only.
"""

from __future__ import annotations

import json

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


EXPECTED_COMPETITOR_IDENTITIES: set[tuple[str, str, int]] = {
    ("zhixin-huiyu", "知心慧语", 1),
    ("jiachangtang", "家长糖", 1),
    ("trustparent", "TrustParent", 1),
    ("rice-ai", "RICE AI / 大米和小米", 1),
    ("little-otter", "Little Otter", 1),
    ("bend-health", "Bend Health", 1),
    ("sylva", "Sylva", 1),
    ("spring-health-guide", "Spring Health / Guide", 1),
    ("kairoo", "Kairoo", 1),
    ("innowell", "Innowell", 1),
    ("one-sec", "one sec", 1),
    ("dynamicare-health", "DynamiCare Health", 1),
    ("paicoach", "PaiCoach", 1),
    ("asd-super-agent", "ASD Super Agent", 1),
    ("guji", "谷积", 1),
    ("zizai-mental-health-ai", "“自在”心理疏导大模型", 1),
    ("yangguang-duoduo", "阳光朵朵 / 花都案例", 1),
    ("xiaodu-ai-care", "小度 AI 看护 / 家庭智能体", 1),
    ("brightline", "Brightline", 1),
    ("good-inside", "Good Inside", 1),
    ("mightier", "Mightier", 1),
    ("daily-growth", "Daily Growth", 1),
    ("lumi-nova", "Lumi Nova", 1),
    ("kinspire", "Kinspire / Precision Parenting", 1),
    ("neurture", "Neurture Studio", 1),
    ("understanding-zoe", "Understanding Zoe", 1),
    ("mindler-sandbox", "Mindler / The Sandbox", 1),
    ("sword-health", "Sword Health", 1),
    ("hinge-health", "Hinge Health", 1),
    ("pelago", "Pelago", 1),
    ("luca", "LUCA", 1),
    ("understood", "Understood", 1),
    ("emora", "EMORA", 1),
    ("functional-parenting-coach", "Functional Parenting Coach", 1),
    ("zheli-zhihuijia", "浙里智慧家", 2),
    ("manatee", "Manatee", 2),
    ("huckleberry", "Huckleberry", 2),
    ("lumi-family", "Lumi", 2),
    ("bridges-engage", "BRIDGES Engage", 2),
    ("attune", "Attune", 2),
    ("luming-zhiyin", "鹿鸣知音", 2),
    ("qinbaobao", "亲宝宝", 2),
    ("shiguangji", "拾光记", 2),
    ("zhiyu-zhushou", "智育助手", 2),
    ("joon", "Joon", 2),
    ("dragonlock", "Dragonlock", 2),
    ("grogo", "Grogo", 2),
    ("parentup", "ParentUp", 2),
    ("includedvision", "IncludedVision", 2),
    ("ditri", "Ditri", 2),
    ("unpluq", "Unpluq", 2),
    ("forfeit", "Forfeit", 2),
    ("huawei-kids-watch", "华为儿童手表 / 儿童守护体系", 2),
    ("mango-parent", "Mango Parent", 2),
    ("timenest", "TimeNest", 2),
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
    manual_ids = {
        json.loads(path.read_text(encoding="utf-8"))["competitor_id"]
        for path in (REPO_ROOT / "data" / "intelligence" / "research").glob("*.json")
    }
    assert all(c["tracked_urls"] or c["id"] in manual_ids for c in competitors)
    assert sum(len(c["tracked_urls"]) for c in competitors) == 98
    header = COMPETITORS_PATH.read_text(encoding="utf-8")
    assert "AUTHORITY" in header
    assert "confirmed 55-object onboarding list" in header


def test_competitor_authority_exact_identity_set() -> None:
    data = yaml.safe_load(COMPETITORS_PATH.read_text(encoding="utf-8"))
    identities = {(c["id"], c["name"], c["tier"]) for c in data["competitors"]}
    assert identities == EXPECTED_COMPETITOR_IDENTITIES
    # This intentionally represents the current Precision Parenting generation,
    # not the retired Android Kinspire service.
    assert ("kinspire", "Kinspire / Precision Parenting", 1) in identities


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
