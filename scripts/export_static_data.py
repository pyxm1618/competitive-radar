"""Static JSON export entry point (Competitive Radar V1).

Upstream ``compete`` used this script to bake FastAPI responses into
``web/public/api-static/`` via ``TestClient``. V1 keeps upstream's
**static-snapshot deployment pattern** but replaces the payload with the single
compiled artifact ``web/public/radar-static/radar.json``.

This is now a THIN WRAPPER around the authoritative compiler. It never creates a
second business-data source, never calls a model API, and never writes to
``web/public/api-static/`` (that legacy directory was removed so the frontend
cannot have two competing truths).

Run:  uv run python scripts/export_static_data.py
      (equivalent to `radar build --no-web` minus dbt / validation gating)

Prefer `radar build`, which also validates intelligence and runs dbt build.
"""

from __future__ import annotations

from pipeline.radar.compile import compile_radar


def main() -> None:
    snapshot = compile_radar()
    print(
        "Compiled static radar snapshot: "
        f"competitors={snapshot.summary.tracked_competitors} "
        f"intelligence={len(snapshot.intelligence)} "
        f"evidence={len(snapshot.evidence)}"
    )


if __name__ == "__main__":
    main()
