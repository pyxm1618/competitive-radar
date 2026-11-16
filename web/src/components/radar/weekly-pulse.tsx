import Link from "next/link";

import { ImpactBadge, DecisionBadge, Tag } from "@/components/radar/badges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WeeklyPulse } from "@/lib/radar-types";

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-background px-4 py-3">
      <p className="tabular text-2xl font-semibold">{value}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

/** Weekly Pulse: a compact, read-only summary of the latest compiled week. */
export function WeeklyPulse({
  weekly,
  competitorNames,
}: {
  weekly: WeeklyPulse;
  competitorNames: Record<string, string>;
}) {
  const decisions = [
    { label: "Act", value: weekly.by_decision.act },
    { label: "Investigate", value: weekly.by_decision.investigate },
    { label: "Watch", value: weekly.by_decision.watch },
    { label: "Ignore", value: weekly.by_decision.ignore },
  ];

  return (
    <Card>
      <CardHeader className="border-b bg-muted/30">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle className="text-lg">Weekly Pulse</CardTitle>
          <span className="tabular text-xs text-muted-foreground">
            {weekly.week_start || "—"} → {weekly.week_end || "—"}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 pt-5">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          <Metric label="Total changes" value={weekly.total_changes} />
          <Metric label="Important changes" value={weekly.important_changes} />
          {decisions.map((decision) => (
            <Metric key={decision.label} label={decision.label} value={decision.value} />
          ))}
          <Metric label="Manual research needed" value={weekly.manual_research_needed} />
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Top changes
            </h4>
            {weekly.top_changes.length > 0 ? (
              <ul className="space-y-2">
                {weekly.top_changes.map((change) => (
                  <li key={change.intelligence_id} className="rounded-md border p-3">
                    <div className="mb-1 flex flex-wrap items-center gap-1.5">
                      <span className="text-xs font-medium">
                        {competitorNames[change.competitor_id] ?? change.competitor_id}
                      </span>
                      <ImpactBadge value={change.impact} />
                      <DecisionBadge value={change.decision} />
                    </div>
                    <a
                      href={`/evidence#${change.intelligence_id}`}
                      className="text-sm hover:underline"
                    >
                      {change.summary}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
                No top changes were compiled for this week.
              </p>
            )}
          </section>

          <section>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Cross-competitor themes
            </h4>
            {weekly.cross_competitor_themes.length > 0 ? (
              <ul className="space-y-2">
                {weekly.cross_competitor_themes.map((theme) => (
                  <li key={theme.topic_id} className="rounded-md border p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <Link
                        href={`/topics/${encodeURIComponent(theme.topic_id)}`}
                        className="text-sm font-medium hover:underline"
                      >
                        {theme.label}
                      </Link>
                      <Tag>{theme.intelligence_count} signals</Tag>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {theme.competitor_ids.length} competitor(s):{" "}
                      {theme.competitor_ids
                        .map((id) => competitorNames[id] ?? id)
                        .join(", ") || "—"}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
                No cross-competitor themes were compiled for this week.
              </p>
            )}
          </section>
        </div>
      </CardContent>
    </Card>
  );
}
