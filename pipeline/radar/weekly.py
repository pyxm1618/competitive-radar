"""Weekly Pulse derived from authoritative intelligence (no live model call).

Upstream ``pipeline/report/generate.py`` is retained for compatibility, but V1
does not use its LLM narrative. The structured pulse below is computed purely
from validated intelligence records, and its markdown brief is written back to
the SAME upstream ``raw.reports`` table (no second report store).
"""

from __future__ import annotations

from datetime import date, timedelta

from pipeline.radar.contracts import (
    Confidence,
    CrossCompetitorTheme,
    Decision,
    Impact,
    IntelligenceRecord,
    ManualResearchRequest,
    ResearchStatus,
    TopChange,
    TopicsFile,
    WeeklyPulse,
)

IMPACT_SCORE = {Impact.HIGH: 30, Impact.MEDIUM: 20, Impact.LOW: 10}
RELEVANCE_SCORE = {"high": 15, "medium": 10, "low": 5}
CONFIDENCE_SCORE = {Confidence.HIGH: 10, Confidence.MEDIUM: 6, Confidence.LOW: 2}
DECISION_SCORE = {
    Decision.ACT: 8,
    Decision.INVESTIGATE: 6,
    Decision.WATCH: 2,
    Decision.IGNORE: 0,
}


def intelligence_score(record: IntelligenceRecord, today: date) -> int:
    """Deterministic Radar ordering: impact > relevance > confidence > recency."""
    age = max(0, (today - record.date).days)
    recency = max(0, 10 - age)
    return (
        IMPACT_SCORE[record.impact]
        + RELEVANCE_SCORE[str(record.relevance)]
        + CONFIDENCE_SCORE[record.confidence]
        + DECISION_SCORE[record.decision]
        + recency
    )


def week_bounds(today: date) -> tuple[date, date]:
    """Rolling 7-day period, matching the Radar homepage default window."""
    return today - timedelta(days=7), today + timedelta(days=1)


def build_weekly_pulse(
    records: list[IntelligenceRecord],
    topics: TopicsFile,
    research: list[ManualResearchRequest],
    *,
    detected_changes_in_week: int = 0,
    today: date | None = None,
) -> WeeklyPulse:
    current = today or date.today()
    start, end = week_bounds(current)
    in_window = [r for r in records if start <= r.date < end]
    # Same fallback semantics as upstream pipeline/report/generate.py: a quiet
    # period still produces a meaningful brief from the most significant
    # available intelligence instead of an empty placeholder.
    if not in_window and records:
        in_window = list(records)
    ranked = sorted(
        in_window, key=lambda r: (-intelligence_score(r, current), r.date, r.intelligence_id)
    )

    important = [
        r
        for r in in_window
        if r.impact == Impact.HIGH or r.decision in (Decision.ACT, Decision.INVESTIGATE)
    ]
    by_decision = {str(d): 0 for d in Decision}
    for record in in_window:
        by_decision[str(record.decision)] += 1

    labels = {t.id: t.label for t in topics.topics}
    themes: list[CrossCompetitorTheme] = []
    for topic in topics.topics:
        hits = [r for r in in_window if topic.id in r.topic_ids]
        comps = sorted({r.competitor_id for r in hits})
        if len(comps) >= 2:
            themes.append(
                CrossCompetitorTheme(
                    topic_id=topic.id,
                    label=labels[topic.id],
                    intelligence_count=len(hits),
                    competitor_ids=comps,
                )
            )
    themes.sort(key=lambda t: (-len(t.competitor_ids), -t.intelligence_count, t.topic_id))

    open_requests = sum(
        1 for r in research if r.status in (ResearchStatus.OPEN, ResearchStatus.IN_PROGRESS)
    )
    return WeeklyPulse(
        week_start=start.isoformat(),
        week_end=end.isoformat(),
        total_changes=detected_changes_in_week if detected_changes_in_week else len(in_window),
        important_changes=len(important),
        top_changes=[
            TopChange(
                intelligence_id=r.intelligence_id,
                competitor_id=r.competitor_id,
                summary=r.summary,
                impact=r.impact,
                decision=r.decision,
            )
            for r in ranked[:5]
        ],
        cross_competitor_themes=themes,
        by_decision=by_decision,
        manual_research_needed=open_requests,
    )


def render_weekly_markdown(
    pulse: WeeklyPulse,
    records: list[IntelligenceRecord],
    research: list[ManualResearchRequest],
) -> str:
    """A deterministic brief stored in the upstream raw.reports table."""
    lines = [
        f"# Weekly Pulse - week of {pulse.week_start}",
        "",
        f"Detected changes: **{pulse.total_changes}**. "
        f"Important changes: **{pulse.important_changes}**.",
        "",
        "## Top changes",
    ]
    if pulse.top_changes:
        for item in pulse.top_changes:
            lines.append(
                f"- **{item.competitor_id}** [{item.impact}/{item.decision}] {item.summary} "
                f"(`{item.intelligence_id}`)"
            )
    else:
        lines.append("- No authoritative intelligence in this period.")

    lines += ["", "## Cross-competitor themes"]
    if pulse.cross_competitor_themes:
        for theme in pulse.cross_competitor_themes:
            lines.append(
                f"- **{theme.label}** ({theme.topic_id}): {theme.intelligence_count} record(s), "
                f"{', '.join(theme.competitor_ids)}"
            )
    else:
        lines.append("- Insufficient evidence for a cross-competitor theme.")

    lines += ["", "## Decisions"]
    for key, value in pulse.by_decision.items():
        lines.append(f"- {key}: {value}")

    lines += ["", "## Manual research needed"]
    outstanding = [
        r for r in research if r.status in (ResearchStatus.OPEN, ResearchStatus.IN_PROGRESS)
    ]
    if outstanding:
        for req in outstanding:
            lines.append(f"- **{req.competitor_id or 'unassigned'}**: {req.research_question}")
    else:
        lines.append("- None.")

    lines += [
        "",
        "---",
        "Generated deterministically from `data/intelligence/records/*.json`. "
        "No model API was called. Evidence for each record is traceable from the Radar UI.",
        "",
    ]
    return "\n".join(lines)


__all__ = ["build_weekly_pulse", "intelligence_score", "render_weekly_markdown", "week_bounds"]
