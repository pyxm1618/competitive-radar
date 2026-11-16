import { History } from "lucide-react";
import Link from "next/link";

import { DecisionBadge, Tag } from "@/components/radar/badges";
import { EmptyState } from "@/components/empty-state";
import type { TimelineEvent } from "@/lib/radar-types";

/**
 * Product Evolution Timeline. Every node is a real, data-backed event that
 * links back to the originating intelligence (and, through it, its evidence).
 * No decorative-only placeholders.
 */
export function Timeline({
  events,
  topicLabels,
}: {
  events: TimelineEvent[];
  topicLabels: Record<string, string>;
}) {
  if (events.length === 0) {
    return (
      <EmptyState
        icon={History}
        title="No evolution events yet"
        description="This competitor has no compiled timeline events. Once intelligence is produced by radar prepare + analysis, each detected change will appear here with a link to its evidence."
      />
    );
  }

  return (
    <ol className="relative ml-2 space-y-5 border-l pl-6">
      {events.map((event, index) => (
        <li key={`${event.intelligence_id}-${index}`} className="relative">
          <span className="absolute -left-[31px] top-1.5 grid h-3 w-3 place-items-center rounded-full border-2 border-primary bg-background" />
          <div className="rounded-lg border bg-card p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <h4 className="text-sm font-semibold leading-snug">{event.title}</h4>
                <p className="tabular mt-0.5 text-xs text-muted-foreground">{event.date}</p>
              </div>
              <DecisionBadge value={event.decision} />
            </div>

            {event.summary && (
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {event.summary}
              </p>
            )}

            {event.topic_ids.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {event.topic_ids.map((id) => (
                  <Link key={id} href={`/topics/${encodeURIComponent(id)}`}>
                    <Tag className="hover:opacity-70">{topicLabels[id] ?? id}</Tag>
                  </Link>
                ))}
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-3 border-t pt-3 text-xs">
              <a
                href={`/evidence#${event.intelligence_id}`}
                className="font-medium text-primary underline underline-offset-2 hover:opacity-80"
              >
                View originating intelligence &amp; evidence →
              </a>
              <span className="tabular break-all text-muted-foreground">
                change: {event.change_id}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
