import Link from "next/link";
import type { ReactNode } from "react";

import {
  ConfidenceBadge,
  DecisionBadge,
  ImpactBadge,
  RelevanceBadge,
  ReviewBadge,
  Tag,
} from "@/components/radar/badges";
import { BeforeAfter } from "@/components/radar/before-after";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { IntelligenceView } from "@/lib/radar-view";
import { cn } from "@/lib/utils";

function Prose({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
        {children || "—"}
      </p>
    </div>
  );
}

/**
 * The canonical read-only rendering of one intelligence record.
 *
 * Raw evidence (before/after + evidence links) is deliberately shown ABOVE the
 * AI interpretation prose, so a reviewer sees the evidence before reading the
 * generated analysis. This component is intentionally free of "use client" and
 * server-only imports so it can be rendered from either a Server or Client
 * component.
 */
export function IntelligenceCard({
  view,
  className,
}: {
  view: IntelligenceView;
  className?: string;
}) {
  const { item, competitor, topics, evidence, beforeAfter } = view;
  const competitorName = competitor?.name ?? item.competitor_id;

  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="gap-3 border-b bg-muted/30">
        <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <div className="min-w-0">
            <Link
              href={`/competitors/${encodeURIComponent(item.competitor_id)}`}
              className="text-base font-semibold leading-tight hover:underline"
            >
              {competitorName}
            </Link>
            <p className="tabular mt-0.5 text-xs text-muted-foreground">{item.date}</p>
          </div>
          <div className="flex flex-wrap items-center gap-1.5">
            <ImpactBadge value={item.impact} />
            <ConfidenceBadge value={item.confidence} />
            <DecisionBadge value={item.decision} />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {topics.length > 0 ? (
            topics.map((topic) => (
              <Link key={topic.id} href={`/topics/${encodeURIComponent(topic.id)}`}>
                <Tag className="hover:opacity-70">{topic.label}</Tag>
              </Link>
            ))
          ) : (
            <Tag>No topic</Tag>
          )}
          {item.change_type && <Tag>{item.change_type}</Tag>}
          <RelevanceBadge value={item.relevance} />
          <ReviewBadge value={item.human_review_status} />
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-5">
        {/* 1) RAW evidence first: before/after comparison, when available. */}
        {beforeAfter && (
          <BeforeAfter
            before={beforeAfter.before}
            after={beforeAfter.after}
            diff={beforeAfter.diff}
            url={beforeAfter.url}
          />
        )}

        {/* 2) Evidence section: raw evidence chips + jump into the browser. */}
        <section>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Evidence (RAW)
            </h4>
            <a
              href={`/evidence#${item.intelligence_id}`}
              className="text-xs text-primary underline underline-offset-2 hover:opacity-80"
            >
              Open in evidence browser →
            </a>
          </div>
          {evidence.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {evidence.map((ev) => (
                <li key={ev.evidence_id}>
                  <a
                    href={`/evidence#${item.intelligence_id}`}
                    className="inline-flex max-w-xs items-center gap-1.5 rounded-md border bg-background px-2.5 py-1 text-xs hover:bg-secondary"
                    title={ev.evidence_id}
                  >
                    <span className="truncate">{ev.title}</span>
                    <span className="shrink-0 rounded bg-emerald-100 px-1 text-[10px] font-semibold uppercase text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                      {ev.kind}
                    </span>
                  </a>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
              No raw evidence is linked to this record yet.
            </p>
          )}
        </section>

        {/* 3) AI interpretation (the long prose) comes after the evidence. */}
        <section className="rounded-lg border bg-background p-4">
          <p className="mb-3 inline-flex rounded bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800 dark:bg-violet-950 dark:text-violet-300">
            AI interpretation
          </p>
          <div className="space-y-4">
            <Prose label="Change summary">{item.summary}</Prose>
            <Prose label="Why it matters">{item.why_it_matters}</Prose>
            <Prose label="Xiaoshuyin relevance">{item.xiaoshuyin_relevance}</Prose>
            <Prose label="Mechanism">{item.mechanism}</Prose>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-3 text-[11px] text-muted-foreground">
            <span>Analyst: {item.analyst || "—"}</span>
            <span className="tabular break-all">Source: {item.provenance.url || "—"}</span>
          </div>
        </section>
      </CardContent>
    </Card>
  );
}
