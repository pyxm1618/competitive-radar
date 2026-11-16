/* eslint-disable @next/next/no-img-element */
import type { ReactNode } from "react";

import { Tag, VerificationBadge } from "@/components/radar/badges";
import { Card } from "@/components/ui/card";
import type { Evidence } from "@/lib/radar-types";
import { cn } from "@/lib/utils";

const MISSING_VERIFICATION: Set<Evidence["verification_state"]> = new Set([
  "missing",
  "unverified",
  "demo_placeholder",
]);

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 break-words text-sm text-foreground">{children}</dd>
    </div>
  );
}

function Value({ children }: { children: ReactNode }) {
  return <span className="text-muted-foreground">{children ?? "—"}</span>;
}

/** Renders a single RAW evidence record (snapshots, extracts, hash, URL). */
export function EvidenceView({
  evidence,
  className,
}: {
  evidence: Evidence;
  className?: string;
}) {
  const isRaw = evidence.kind === "raw";

  return (
    <Card className={cn("overflow-hidden", className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b bg-muted/30 px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                isRaw
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
              )}
            >
              {isRaw ? "RAW evidence" : "MANUAL evidence"}
            </span>
            <Tag>{evidence.type}</Tag>
          </div>
          <h3 className="mt-2 text-sm font-semibold leading-snug">{evidence.title}</h3>
        </div>
        <VerificationBadge value={evidence.verification_state} />
      </div>

      <div className="px-4 py-3">
        {MISSING_VERIFICATION.has(evidence.verification_state) && (
          <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
            This evidence is <strong>not verified</strong> ({evidence.verification_state}). Treat it
            as provisional until a snapshot or hash confirms it.
          </p>
        )}

        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <Field label="Original URL">
            {evidence.url ? (
              <a
                href={evidence.url}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-sm text-primary underline underline-offset-2 hover:opacity-80"
              >
                {evidence.url}
              </a>
            ) : (
              <Value>Not available</Value>
            )}
          </Field>
          <Field label="Snapshot ref">
            {evidence.snapshot_ref ? (
              <span className="tabular text-xs">{evidence.snapshot_ref}</span>
            ) : (
              <Value>Not available</Value>
            )}
          </Field>
          <Field label="Content hash">
            {evidence.content_hash ? (
              <span className="tabular break-all text-xs">{evidence.content_hash}</span>
            ) : (
              <Value>Not available</Value>
            )}
          </Field>
          <Field label="Captured at">
            {evidence.captured_at ? (
              <span className="tabular text-xs">{evidence.captured_at}</span>
            ) : (
              <Value>Not available</Value>
            )}
          </Field>
          <Field label="File path">
            {evidence.file_path ? (
              <span className="tabular break-all text-xs">{evidence.file_path}</span>
            ) : (
              <Value>Not available</Value>
            )}
          </Field>
          <Field label="Evidence id">
            <span className="tabular break-all text-xs">{evidence.evidence_id}</span>
          </Field>
        </dl>

        {evidence.extract && (
          <div className="mt-4">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Extracted text (raw)
            </p>
            <pre className="scrollbar-thin max-h-64 overflow-auto whitespace-pre-wrap rounded-md border bg-background p-3 text-xs leading-relaxed text-foreground">
              {evidence.extract}
            </pre>
          </div>
        )}

        {evidence.image_path && (
          <div className="mt-4">
            <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Screenshot (raw)
            </p>
            <img
              src={evidence.image_path}
              alt={`Raw screenshot for ${evidence.title}`}
              className="h-auto w-full rounded-md border object-contain"
              loading="lazy"
            />
          </div>
        )}
      </div>
    </Card>
  );
}
