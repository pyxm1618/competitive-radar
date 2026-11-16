"use client";

import { useMemo, useState } from "react";

import { IntelligenceCard } from "@/components/radar/intelligence-card";
import type { IntelligenceView } from "@/lib/radar-view";
import { cn } from "@/lib/utils";

type Range = "7d" | "30d" | "all";

const RANGES: { value: Range; label: string; days: number }[] = [
  { value: "7d", label: "7 days", days: 7 },
  { value: "30d", label: "30 days", days: 30 },
  { value: "all", label: "All", days: 0 },
];

const DAY_MS = 86_400_000;

function referenceMs(referenceDate: string, views: IntelligenceView[]): number {
  const parsed = Date.parse(referenceDate);
  if (!Number.isNaN(parsed)) return parsed;
  let max = 0;
  for (const view of views) {
    const t = Date.parse(view.item.date);
    if (!Number.isNaN(t) && t > max) max = t;
  }
  return max;
}

function inWindow(dateStr: string, refMs: number, days: number): boolean {
  if (days <= 0 || refMs === 0) return true;
  const t = Date.parse(dateStr);
  if (Number.isNaN(t)) return true; // unknown date -> never hide it
  return t >= refMs - days * DAY_MS;
}

/**
 * Client-side time window for the "值得你看的变化" list. It receives the
 * already-sorted intelligence views and only filters them — it never re-sorts,
 * so the build step's ranking (impact/relevance/confidence/recency) is kept.
 */
export function RadarBrowser({
  views,
  referenceDate,
}: {
  views: IntelligenceView[];
  referenceDate: string;
}) {
  const [range, setRange] = useState<Range>("7d");

  const filtered = useMemo(() => {
    const config = RANGES.find((r) => r.value === range) ?? RANGES[0];
    const refMs = referenceMs(referenceDate, views);
    return views.filter((view) => inWindow(view.item.date, refMs, config.days));
  }, [views, referenceDate, range]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div
          className="inline-flex rounded-lg border bg-muted/40 p-1"
          role="group"
          aria-label="Time window"
        >
          {RANGES.map((option) => (
            <button
              key={option.value}
              type="button"
              aria-pressed={range === option.value}
              onClick={() => setRange(option.value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                range === option.value
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Showing <span className="tabular font-semibold text-foreground">{filtered.length}</span> of{" "}
          <span className="tabular font-semibold text-foreground">{views.length}</span> changes
        </p>
      </div>

      {filtered.length > 0 ? (
        <div className="space-y-5">
          {filtered.map((view) => (
            <IntelligenceCard key={view.item.intelligence_id} view={view} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="text-sm font-medium">No changes in this window</p>
          <p className="mt-1 text-xs text-muted-foreground">
            There are compiled changes, but none fall within the selected time range.
          </p>
          <button
            type="button"
            onClick={() => setRange("all")}
            className="mt-3 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-secondary"
          >
            Show all changes
          </button>
        </div>
      )}
    </div>
  );
}
