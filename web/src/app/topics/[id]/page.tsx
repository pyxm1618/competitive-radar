import { Layers } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { DecisionBadge, Tag } from "@/components/radar/badges";
import { EvidenceView } from "@/components/radar/evidence-view";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  competitorById,
  competitorNamesMap,
  evidenceByIds,
  getRadarData,
  intelligenceForTopic,
  topicById,
} from "@/lib/radar-data";
import type { Competitor, Intelligence } from "@/lib/radar-types";

export const dynamicParams = false;

export function generateStaticParams() {
  return getRadarData().topics.map((topic) => ({ id: topic.id }));
}

interface ComparisonRow {
  competitor: Competitor;
  records: Intelligence[];
  changeTypes: string[];
  decisions: string[];
}

export default function TopicDetailPage({ params }: { params: { id: string } }) {
  const data = getRadarData();
  const topic = topicById(data, params.id);
  if (!topic) notFound();

  const competitorNames = competitorNamesMap(data);
  const related = intelligenceForTopic(data, topic.id);

  // Involved competitors: union of configured ids and ids seen in intelligence.
  const competitorIds = new Set<string>(topic.competitor_ids);
  for (const intel of related) competitorIds.add(intel.competitor_id);
  const involved: Competitor[] = [];
  for (const id of competitorIds) {
    const competitor = competitorById(data, id);
    if (competitor) involved.push(competitor);
  }

  // Key evidence: configured evidence ids plus those linked from intelligence.
  const evidenceIds = new Set<string>(topic.evidence_ids);
  for (const intel of related) for (const id of intel.evidence_ids) evidenceIds.add(id);
  const keyEvidence = evidenceByIds(data, Array.from(evidenceIds));

  // Cross-product comparison is derived ONLY from compiled change_type values.
  // It is a factual grouping, never an analyst conclusion about products.
  const byCompetitor = new Map<string, Intelligence[]>();
  for (const intel of related) {
    const list = byCompetitor.get(intel.competitor_id) ?? [];
    list.push(intel);
    byCompetitor.set(intel.competitor_id, list);
  }
  const comparisonRows: ComparisonRow[] = [];
  for (const [id, records] of byCompetitor) {
    const competitor = competitorById(data, id);
    if (!competitor) continue;
    comparisonRows.push({
      competitor,
      records,
      changeTypes: Array.from(new Set(records.map((r) => r.change_type).filter(Boolean))),
      decisions: Array.from(new Set(records.map((r) => r.decision))),
    });
  }
  const comparisonAvailable = comparisonRows.length >= 2;

  // Shared vs unique change types, purely derived from the rows above.
  const typeCounts = new Map<string, number>();
  for (const row of comparisonRows) {
    for (const type of row.changeTypes) typeCounts.set(type, (typeCounts.get(type) ?? 0) + 1);
  }
  const sharedTypes = Array.from(typeCounts.entries())
    .filter(([, count]) => count >= 2)
    .map(([type]) => type);
  const uniqueTypes = Array.from(typeCounts.entries())
    .filter(([, count]) => count === 1)
    .map(([type]) => type);

  return (
    <div>
      <PageHeader title={topic.label} description={topic.description || undefined} />

      <div className="mb-6 flex flex-wrap gap-2">
        <Tag>{topic.intelligence_count} intelligence</Tag>
        <Tag>{topic.competitor_ids.length} competitors</Tag>
        <Tag>{topic.evidence_ids.length} evidence</Tag>
      </div>

      {/* Involved competitors */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Involved competitors</h2>
        {involved.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {involved.map((competitor) => (
              <Link
                key={competitor.id}
                href={`/competitors/${encodeURIComponent(competitor.id)}`}
                className="rounded-md border bg-card px-3 py-1.5 text-sm font-medium hover:bg-secondary"
              >
                {competitor.name}
                {competitor.industry ? ` · ${competitor.industry}` : ""}
              </Link>
            ))}
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No competitors are associated with this topic in the compiled artifact.
          </p>
        )}
      </section>

      {/* Related intelligence */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Related intelligence</h2>
        {related.length > 0 ? (
          <div className="space-y-3">
            {related.map((intel) => (
              <Card key={intel.intelligence_id}>
                <CardContent className="space-y-2 pt-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        href={`/competitors/${encodeURIComponent(intel.competitor_id)}`}
                        className="text-sm font-semibold hover:underline"
                      >
                        {competitorNames[intel.competitor_id] ?? intel.competitor_id}
                      </Link>
                      <span className="tabular text-xs text-muted-foreground">{intel.date}</span>
                      {intel.change_type && <Tag>{intel.change_type}</Tag>}
                    </div>
                    <DecisionBadge value={intel.decision} />
                  </div>
                  <p className="text-sm leading-relaxed">{intel.summary}</p>
                  {intel.mechanism && (
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      <span className="font-medium text-foreground">Mechanism: </span>
                      {intel.mechanism}
                    </p>
                  )}
                  <a
                    href={`/evidence#${intel.intelligence_id}`}
                    className="inline-block text-xs font-medium text-primary underline underline-offset-2 hover:opacity-80"
                  >
                    View its evidence →
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Layers}
            title="Insufficient evidence"
            description="No intelligence has been compiled for this topic yet, so there are no records, mechanisms or decisions to display. Nothing is inferred here."
          />
        )}
      </section>

      {/* Key evidence */}
      <section className="mb-8">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Key evidence (RAW)</h2>
        {keyEvidence.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {keyEvidence.map((evidence) => (
              <EvidenceView key={evidence.evidence_id} evidence={evidence} />
            ))}
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No raw evidence is linked to this topic yet.
          </p>
        )}
      </section>

      {/* Cross-product similarities / differences (derived only) */}
      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">
          Cross-product similarities &amp; differences
        </h2>
        {comparisonAvailable ? (
          <Card>
            <CardHeader className="border-b bg-muted/30">
              <CardTitle className="text-sm">Derived from compiled change types</CardTitle>
              <p className="text-xs text-muted-foreground">
                Factual grouping only — no analyst conclusions about product features are made.
              </p>
            </CardHeader>
            <CardContent className="space-y-3 pt-4">
              <ul className="space-y-1.5">
                {comparisonRows.map((row) => (
                  <li key={row.competitor.id} className="text-sm">
                    <span className="font-medium">{row.competitor.name}</span>: {row.records.length}{" "}
                    record(s); change types: {row.changeTypes.join(", ") || "—"}; decisions:{" "}
                    {row.decisions.join(", ") || "—"}
                  </li>
                ))}
              </ul>
              <p className="text-sm">
                <span className="font-medium">Similarities (shared change types): </span>
                {sharedTypes.length > 0 ? sharedTypes.join(", ") : "none derivable"}
              </p>
              <p className="text-sm">
                <span className="font-medium">Differences (single-product change types): </span>
                {uniqueTypes.length > 0 ? uniqueTypes.join(", ") : "none derivable"}
              </p>
            </CardContent>
          </Card>
        ) : (
          <EmptyState
            icon={Layers}
            title="Insufficient evidence"
            description="Fewer than two products have compiled intelligence on this topic, so no cross-product similarities or differences can be derived from the data. No comparative claims are made without source evidence."
          />
        )}
      </section>
    </div>
  );
}
