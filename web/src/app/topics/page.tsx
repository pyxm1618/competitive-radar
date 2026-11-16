import { Tags } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Tag } from "@/components/radar/badges";
import { Card, CardContent } from "@/components/ui/card";
import { getRadarData } from "@/lib/radar-data";

export const metadata: Metadata = { title: "Topics" };

export default function TopicsPage() {
  const data = getRadarData();
  const topics = data.topics;
  const hasAnyIntelligence = topics.some((topic) => topic.intelligence_count > 0);

  return (
    <div>
      <PageHeader
        title="Topics"
        description="The taxonomy used to classify every detected change. Counts come straight from the compiled artifact."
      />

      {topics.length === 0 ? (
        <EmptyState
          icon={Tags}
          title="No topics are configured"
          description="The compiled artifact contains no taxonomy. Topics are defined by the authoritative config and produced by `radar build`."
        />
      ) : (
        <>
          {!hasAnyIntelligence && (
            <p className="mb-5 rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
              Insufficient evidence: the taxonomy is configured, but no intelligence has been
              compiled against it yet. Counts below are all zero — topic detail pages will state
              this explicitly rather than inventing analysis.
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {topics.map((topic) => (
              <Card key={topic.id} className="flex flex-col">
                <CardContent className="flex flex-1 flex-col gap-3 pt-5">
                  <Link
                    href={`/topics/${encodeURIComponent(topic.id)}`}
                    className="text-base font-semibold leading-tight hover:underline"
                  >
                    {topic.label}
                  </Link>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {topic.description || "No description provided."}
                  </p>

                  <div className="flex flex-wrap gap-1.5">
                    <Tag>{topic.intelligence_count} intelligence</Tag>
                    <Tag>{topic.competitor_ids.length} competitors</Tag>
                  </div>

                  {topic.intelligence_count === 0 && (
                    <p className="text-[11px] text-muted-foreground">
                      No compiled intelligence yet — insufficient evidence for this topic.
                    </p>
                  )}

                  <Link
                    href={`/topics/${encodeURIComponent(topic.id)}`}
                    className="mt-auto pt-2 text-xs font-medium text-primary underline underline-offset-2 hover:opacity-80"
                  >
                    View topic &amp; evidence →
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
