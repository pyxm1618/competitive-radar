"use client";

/* eslint-disable @next/next/no-img-element */
import { useState } from "react";

import { Tag } from "@/components/radar/badges";
import { Card } from "@/components/ui/card";
import type { Evidence } from "@/lib/radar-types";

function TextSide({
  label,
  evidence,
}: {
  label: string;
  evidence: Evidence | null;
}) {
  return (
    <div className="min-w-0">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        {evidence?.captured_at && (
          <span className="tabular text-[11px] text-muted-foreground">{evidence.captured_at}</span>
        )}
      </div>
      {evidence ? (
        <pre className="scrollbar-thin max-h-56 overflow-auto whitespace-pre-wrap rounded-md border bg-background p-3 text-xs leading-relaxed text-foreground">
          {evidence.extract ?? evidence.title}
        </pre>
      ) : (
        <p className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
          No {label.toLowerCase()} snapshot was captured.
        </p>
      )}
      {evidence?.url && (
        <a
          href={evidence.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 block break-all text-[11px] text-primary underline underline-offset-2 hover:opacity-80"
        >
          {evidence.url}
        </a>
      )}
    </div>
  );
}

/**
 * Lightweight before/after comparison. When both sides have screenshots we
 * render a simple wipe slider (range input); otherwise we show the raw text
 * extracts side by side plus the unified diff. No image editor, by design.
 */
export function BeforeAfter({
  before,
  after,
  diff,
  url,
}: {
  before: Evidence | null;
  after: Evidence | null;
  diff: string;
  url: string;
}) {
  const [wipe, setWipe] = useState(50);
  const bothImages = Boolean(before?.image_path && after?.image_path);

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/30 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide">Before / After evidence</span>
          <Tag>RAW</Tag>
        </div>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="max-w-[16rem] truncate text-[11px] text-primary underline underline-offset-2 hover:opacity-80"
          >
            {url}
          </a>
        )}
      </div>

      <div className="p-4">
        {bothImages ? (
          <div>
            <div className="relative w-full overflow-hidden rounded-md border bg-background">
              <img
                src={before?.image_path ?? ""}
                alt="Before state"
                className="block h-auto w-full"
                loading="lazy"
              />
              <img
                src={after?.image_path ?? ""}
                alt="After state"
                className="absolute inset-0 block h-full w-full object-cover object-left"
                style={{ clipPath: `inset(0 0 0 ${wipe}%)` }}
                loading="lazy"
              />
              <span className="absolute left-2 top-2 rounded bg-foreground/80 px-2 py-0.5 text-[10px] font-semibold uppercase text-background">
                Before
              </span>
              <span className="absolute right-2 top-2 rounded bg-foreground/80 px-2 py-0.5 text-[10px] font-semibold uppercase text-background">
                After
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={wipe}
              onChange={(event) => setWipe(Number(event.target.value))}
              aria-label="Reveal before vs after"
              className="mt-3 w-full accent-primary"
            />
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <TextSide label="Before" evidence={before} />
            <TextSide label="After" evidence={after} />
          </div>
        )}

        <div className="mt-4">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Unified diff (raw)
          </p>
          <pre className="scrollbar-thin max-h-64 overflow-auto whitespace-pre-wrap rounded-md border bg-background p-3 text-xs leading-relaxed text-foreground">
            {diff || "No diff was produced for this change."}
          </pre>
        </div>
      </div>
    </Card>
  );
}
