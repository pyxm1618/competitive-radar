import { FileText } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Tag } from "@/components/radar/badges";
import { EvidenceView } from "@/components/radar/evidence-view";
import { IntelligenceCard } from "@/components/radar/intelligence-card";
import { Timeline } from "@/components/radar/timeline";
import { Card, CardContent } from "@/components/ui/card";
import {
  buildIntelligenceView,
  competitorById,
  evidenceForCompetitor,
  getRadarData,
  intelligenceForCompetitor,
  topicLabelsMap,
} from "@/lib/radar-data";

export const dynamicParams = false;

export function generateStaticParams() {
  return getRadarData().competitors.map((competitor) => ({ id: competitor.id }));
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-lg font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export default function CompetitorDetailPage({ params }: { params: { id: string } }) {
  const data = getRadarData();
  const competitor = competitorById(data, params.id);
  if (!competitor) notFound();

  const records = intelligenceForCompetitor(data, competitor.id);
  // "Latest" = the record with the greatest date (no re-sorting of any list).
  let latest: (typeof records)[number] | null = null;
  for (const record of records) {
    if (!latest || record.date > latest.date) latest = record;
  }
  const latestView = latest ? buildIntelligenceView(data, latest) : null;
  const evidence = evidenceForCompetitor(data, competitor.id);
  const topicLabels = topicLabelsMap(data);

  const profile = [
    { label: "Name", value: competitor.name },
    { label: "Domain", value: competitor.domain ?? "—" },
    { label: "Industry", value: competitor.industry ?? "—" },
    { label: "Tier", value: String(competitor.tier) },
    { label: "Intelligence records", value: String(competitor.intelligence_count) },
    { label: "Evidence records", value: String(competitor.evidence_count) },
    { label: "Latest intelligence", value: competitor.latest_intelligence_at ?? "—" },
  ];

  return (
    <div>
      <PageHeader
        title={competitor.name}
        description={[competitor.domain, competitor.industry, `Tier ${competitor.tier}`]
          .filter(Boolean)
          .join(" · ")}
      />

      <Section title="Basic profile">
        <Card>
          <CardContent className="grid gap-x-8 gap-y-3 pt-5 sm:grid-cols-2 lg:grid-cols-3">
            {profile.map((field) => (
              <div key={field.label}>
                <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {field.label}
                </dt>
                <dd className="tabular mt-0.5 break-words text-sm">{field.value}</dd>
              </div>
            ))}
          </CardContent>
        </Card>
      </Section>

      <Section title="Why tracked">
        <Card>
          <CardContent className="pt-5">
            {competitor.why_tracked ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{competitor.why_tracked}</p>
            ) : (
              <p className="text-sm text-muted-foreground">
                No reason was provided in the authoritative config.
              </p>
            )}
          </CardContent>
        </Card>
      </Section>

      <Section title="Tracked sources">
        {competitor.tracked_sources.length > 0 ? (
          <Card>
            <CardContent className="divide-y pt-1">
              {competitor.tracked_sources.map((source) => (
                <div key={source.source_id} className="flex flex-wrap items-center gap-2 py-3">
                  <Tag>{source.source_type}</Tag>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-sm text-primary underline underline-offset-2 hover:opacity-80"
                  >
                    {source.url}
                  </a>
                  <span className="tabular ml-auto text-[11px] text-muted-foreground">
                    {source.source_id}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No tracked sources are configured for this competitor.
          </p>
        )}
      </Section>

      <Section title="Latest intelligence">
        {latestView ? (
          <IntelligenceCard view={latestView} />
        ) : (
          <EmptyState
            icon={FileText}
            title="No intelligence yet"
            description="No compiled intelligence exists for this competitor in this snapshot."
          />
        )}
      </Section>

      <Section title="Topics">
        {competitor.topic_ids.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {competitor.topic_ids.map((id) => (
              <Link key={id} href={`/topics/${encodeURIComponent(id)}`}>
                <Tag className="hover:opacity-70">{topicLabels[id] ?? id}</Tag>
              </Link>
            ))}
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No topics are associated with this competitor.
          </p>
        )}
      </Section>

      <Section title="Evidence (RAW)">
        {evidence.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {evidence.map((item) => (
              <EvidenceView key={item.evidence_id} evidence={item} />
            ))}
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No raw evidence has been compiled for this competitor.
          </p>
        )}
      </Section>

      <Section title="Product Evolution Timeline">
        <Timeline events={competitor.timeline} topicLabels={topicLabels} />
      </Section>
    </div>
  );
}
