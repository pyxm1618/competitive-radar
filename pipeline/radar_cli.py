"""radar CLI - a thin wrapper over the upstream compete pipeline.

    radar collect      sync -> collect -> snapshot -> deterministic diff  (no AI)
    radar prepare      detected changes -> pending intelligence queue     (no AI)
    radar validate     validate authoritative intelligence output        (no AI)
    radar build        validate -> dbt build -> static JSON -> web build (no AI)
    radar update       collect + prepare + build                         (no AI)
    radar status       report what is in each authority
    radar demo-build   build the compiled artifact from sample fixtures only
    radar contracts    regenerate JSON Schemas from the Pydantic contracts

Analyze is intentionally NOT a CLI command: it is performed by the external
Antigravity agent, human-triggered, via the file protocol.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

import typer
from rich.console import Console

from pipeline.config import get_settings
from pipeline.logging_setup import force_utf8
from pipeline.radar.compile import IntelligenceValidationFailed, compile_radar
from pipeline.radar.contracts import (
    IntelligenceRecord,
    ManualEvidence,
    ManualResearchRequest,
    PendingChange,
)
from pipeline.radar.manual import load_manual_evidence, load_research_requests
from pipeline.radar.paths import (
    COMPETITORS_PATH,
    PENDING_DIR,
    RECORDS_DIR,
    REPO_ROOT,
    SCHEMA_DIR,
    STATIC_RADAR_JSON,
    TOPICS_PATH,
    ensure_intelligence_dirs,
)
from pipeline.radar.pending import load_pending, run_collect, run_prepare
from pipeline.radar.validate import load_competitor_ids, load_topics, validate_intelligence
from pipeline.transform import build_marts

force_utf8()

app = typer.Typer(
    name="radar",
    help="Xiaoshuyin Competitive Radar - no-key monitoring + static build.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
WEB_DIR = REPO_ROOT / "web"


def _run_web_build() -> bool:
    npm = shutil.which("npm")
    if npm is None:
        console.print("[red]npm not found; skipping frontend build.[/]")
        return False
    result = subprocess.run([npm, "run", "build"], cwd=str(WEB_DIR), check=False)
    return result.returncode == 0


@app.command("collect")
def collect() -> None:
    """Sync competitors, collect snapshots, detect changes deterministically."""
    result = run_collect()
    console.print(
        f"[green]✓ collect[/] competitors={result.competitors} urls={result.urls} "
        f"snapshots={result.snapshots} failed={result.failed} "
        f"[bold]detected_changes={result.detected_changes}[/]"
    )
    console.print("[dim]No model API was called.[/]")


@app.command("prepare")
def prepare() -> None:
    """Generate/update the authoritative Antigravity pending queue."""
    result = run_prepare()
    console.print(
        f"[green]✓ prepare[/] changes_read={result.changes_read} created={result.created} "
        f"unchanged={result.unchanged} updated={result.updated} "
        f"skipped_missing_evidence={result.skipped_missing_evidence} "
        f"ignored_inactive={result.ignored_inactive} "
        f"removed_inactive={result.removed_inactive}"
    )
    console.print(f"[dim]Queue: {PENDING_DIR.relative_to(REPO_ROOT)}[/]")


@app.command("validate")
def validate() -> None:
    """Validate authoritative intelligence records (schema + provenance)."""
    report = validate_intelligence()
    console.print(
        f"files_read={report.files_read} valid_records={len(report.records)} "
        f"errors={len(report.errors)} warnings={len(report.warnings)}"
    )
    for warning in report.warnings:
        console.print(f"  [yellow]warn[/] {warning}")
    for error in report.errors:
        console.print(f"  [red]error[/] {error}")
    if not report.ok:
        console.print("[red]✗ intelligence validation FAILED[/]")
        raise typer.Exit(code=1)
    console.print("[green]✓ intelligence validation passed[/]")


def _do_build(web: bool) -> None:
    """Shared implementation so `update` can call it without Typer OptionInfo."""
    report = validate_intelligence()
    if not report.ok:
        for error in report.errors:
            console.print(f"  [red]error[/] {error}")
        console.print("[red]✗ build aborted: intelligence validation failed[/]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓ validate[/] {len(report.records)} intelligence record(s)")

    ok = build_marts(get_settings())
    console.print(
        f"{'[green]✓' if ok else '[yellow]!'} dbt build[/] {'OK' if ok else 'SKIPPED/FAILED (dbt extra not installed or no warehouse)'}"
    )

    try:
        snapshot = compile_radar()
    except IntelligenceValidationFailed as exc:
        console.print(f"[red]✗ compile failed: {exc}[/]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]✓ static JSON[/] {STATIC_RADAR_JSON.relative_to(REPO_ROOT)} "
        f"(competitors={snapshot.summary.tracked_competitors}, "
        f"intelligence={len(snapshot.intelligence)}, evidence={len(snapshot.evidence)})"
    )
    if web:
        if not _run_web_build():
            console.print("[red]✗ frontend build FAILED[/]")
            raise typer.Exit(code=1)
        console.print("[green]✓ frontend build[/]")


@app.command("build")
def build(
    web: bool = typer.Option(True, "--web/--no-web", help="Also run the Next.js production build."),
) -> None:
    """Validate intelligence -> dbt build -> static JSON -> frontend build."""
    _do_build(bool(web))


@app.command("update")
def update(
    web: bool = typer.Option(True, "--web/--no-web", help="Also run the Next.js production build."),
) -> None:
    """Wrapper: collect + prepare + build. Never calls a model API."""
    collect()
    prepare()
    _do_build(bool(web))


@app.command("status")
def status() -> None:
    """Show the current contents of every authority."""
    ensure_intelligence_dirs()
    competitors = load_competitor_ids(COMPETITORS_PATH)
    topics = load_topics(TOPICS_PATH)
    pending = load_pending(PENDING_DIR)
    research = load_research_requests()
    manual = load_manual_evidence()
    records = sorted(RECORDS_DIR.glob("*.json"))
    console.print("[bold]Competitive Radar status[/]")
    console.print(
        f"  competitor authority : {len(competitors)} competitor(s)  ({COMPETITORS_PATH.relative_to(REPO_ROOT)})"
    )
    console.print(f"  topic authority      : {len(topics.topics)} topic(s)")
    console.print(f"  pending changes      : {len(pending)}")
    console.print(f"  intelligence records : {len(records)}")
    console.print(f"  manual evidence      : {len(manual)}")
    console.print(f"  manual research      : {len(research)}")
    if not competitors:
        console.print(
            "[yellow]  note: competitor authority is intentionally empty; the real 55-product list has not been imported.[/]"
        )


@app.command("demo-build")
def demo_build(
    web: bool = typer.Option(
        False, "--web/--no-web", help="Also run the Next.js production build."
    ),
) -> None:
    """Compile the SAMPLE fixture into the static artifact (never writes authority)."""
    try:
        snapshot = compile_radar(demo=True)
    except IntelligenceValidationFailed as exc:
        console.print(f"[red]✗ demo compile failed: {exc}[/]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[green]✓ demo static JSON[/] demo={snapshot.demo} "
        f"competitors={snapshot.summary.tracked_competitors} "
        f"intelligence={len(snapshot.intelligence)}"
    )
    console.print("[yellow]DEMO DATA — sample fixtures only, not authoritative.[/]")
    if web and not _run_web_build():
        raise typer.Exit(code=1)


@app.command("contracts")
def contracts() -> None:
    """Regenerate JSON Schemas from the authoritative Pydantic contracts."""
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    models: dict[str, Any] = {
        "pending-change.schema.json": PendingChange,
        "intelligence-record.schema.json": IntelligenceRecord,
        "manual-evidence.schema.json": ManualEvidence,
        "manual-research-request.schema.json": ManualResearchRequest,
    }
    for name, model in models.items():
        dest = SCHEMA_DIR / name
        dest.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        console.print(f"  [green]✓[/] {dest.relative_to(REPO_ROOT)}")
    console.print(
        "[dim]Schemas are generated from pipeline/radar/contracts.py — do not hand-edit.[/]"
    )


if __name__ == "__main__":
    app()
