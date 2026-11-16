import { Radar } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Tag } from "@/components/radar/badges";
import { RadarBrowser } from "@/components/radar/radar-browser";
import { WeeklyPulse } from "@/components/radar/weekly-pulse";
import { Card } from "@/components/ui/card";
import {
  buildIntelligenceView,
  competitorNamesMap,
  getRadarData,
  topicLabelsMap,
} from "@/lib/radar-data";

function Kpi({ label, value }: { label: string; value: number }) {
  return (
    <Card className="p-4">
      <p className="tabular text-2xl font-semibold leading-none">{value}</p>
      <p className="mt-1.5 text-xs text-muted-foreground">{label}</p>
    </Card>
  );
}

export default function RadarPage() {
  const data = getRadarData();

  // Preserve the build step's ranking: map without sorting or reordering.
  const views = data.intelligence.map((item) => buildIntelligenceView(data, item));
  const competitorNames = competitorNamesMap(data);
  const topicLabels = topicLabelsMap(data);

  const manualResearch = data.manual_research;

  return (
    <div>
      <PageHeader
        title="Radar"
        description="Compiled competitive intelligence, shown as a static read-only snapshot. Evidence first, interpretation second."
      />

      {/* Compact KPI row */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Tracked competitors" value={data.summary.tracked_competitors} />
        <Kpi label="Tracked sources" value={data.summary.tracked_sources} />
        <Kpi label="Detected changes" value={data.summary.detected_changes} />
        <Kpi label="Important changes" value={data.summary.important_changes} />
      </div>

      {/* FIRST visual region: worth-your-attention changes */}
      <section className="mt-9">
        <div className="mb-4">
          <h2 className="text-xl font-semibold tracking-tight">值得你看的变化</h2>
          <p className="text-sm text-muted-foreground">Worth your attention</p>
        </div>

        {views.length === 0 ? (
          <EmptyState
            icon={Radar}
            title="No authoritative intelligence has been produced yet"
            description="This static snapshot contains no compiled intelligence records, so there are no changes to show. The next step is to run `radar prepare`, complete the Antigravity analysis workflow on the pending intelligence, then `radar build` to regenerate radar.json. Until then the Radar, Topics and Evidence views are intentionally empty — the frontend never invents competitor data."
          />
        ) : (
          <RadarBrowser views={views} referenceDate={data.generated_at} />
        )}
      </section>

      {/* Weekly Pulse */}
      <section className="mt-10">
        <WeeklyPulse weekly={data.weekly} competitorNames={competitorNames} />
      </section>

      {/* Manual research needed */}
      {manualResearch.length > 0 && (
        <section className="mt-10">
          <div className="mb-4">
            <h2 className="text-xl font-semibold tracking-tight">Manual research needed</h2>
            <p className="text-sm text-muted-foreground">
              Open questions the compiled evidence could not answer ({manualResearch.length}).
            </p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            {manualResearch.map((request) => (
              <Card key={request.request_id} className="flex flex-col gap-3 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold leading-snug">{request.research_question}</h3>
                  <Tag>{request.status}</Tag>
                </div>
                <p className="text-xs text-muted-foreground">
                  {request.competitor_id
                    ? (competitorNames[request.competitor_id] ?? request.competitor_id)
                    : "Cross-product"}{" "}
                  · {request.created_at || "—"} · by {request.created_by || "—"}
                </p>
                <p className="text-sm text-foreground">{request.why_needed}</p>

                {request.topic_ids.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {request.topic_ids.map((id) => (
                      <Link key={id} href={`/topics/${encodeURIComponent(id)}`}>
                        <Tag className="hover:opacity-70">{topicLabels[id] ?? id}</Tag>
                      </Link>
                    ))}
                  </div>
                )}

                {request.suggested_steps.length > 0 && (
                  <div>
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      Suggested steps
                    </p>
                    <ol className="list-decimal space-y-0.5 pl-5 text-xs text-foreground">
                      {request.suggested_steps.map((step, index) => (
                        <li key={index}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {request.required_evidence.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {request.required_evidence.map((item, index) => (
                      <Tag key={index}>
                        {item.label} · {item.required ? "required" : "optional"} ·{" "}
                        {item.satisfied ? "satisfied" : "missing"}
                      </Tag>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
