import type { ReactNode } from "react";

import type {
  Confidence,
  Decision,
  Impact,
  Relevance,
  ReviewStatus,
  VerificationState,
} from "@/lib/radar-types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Small, readable status chips. Explicit light-surface colors (dark text on a
 * light background) keep everything legible in the IDE light theme; dark:
 * variants keep them legible if dark mode is enabled.
 */
const TONE: Record<string, string> = {
  high: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300",
  medium:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300",
  low: "border-stone-200 bg-stone-100 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300",
  act: "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300",
  investigate:
    "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300",
  watch:
    "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/50 dark:text-sky-300",
  ignore:
    "border-stone-200 bg-stone-100 text-stone-600 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300",
  verified:
    "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300",
  review:
    "border-violet-200 bg-violet-50 text-violet-700 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-300",
  neutral:
    "border-stone-200 bg-stone-50 text-stone-600 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300",
};

function Chip({
  label,
  tone,
  className,
}: {
  label: string;
  tone: string;
  className?: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn("whitespace-nowrap font-medium", TONE[tone] ?? TONE.neutral, className)}
    >
      {label}
    </Badge>
  );
}

const title = (value: string): string => value.charAt(0).toUpperCase() + value.slice(1);

export function ImpactBadge({ value }: { value: Impact }) {
  return <Chip label={`Impact: ${title(value)}`} tone={value} />;
}

export function ConfidenceBadge({ value }: { value: Confidence }) {
  return <Chip label={`Confidence: ${title(value)}`} tone={value} />;
}

export function RelevanceBadge({ value }: { value: Relevance }) {
  return <Chip label={`Relevance: ${title(value)}`} tone={value} />;
}

export function DecisionBadge({ value }: { value: Decision }) {
  return <Chip label={`Decision: ${title(value)}`} tone={value} />;
}

const REVIEW_TONE: Record<ReviewStatus, string> = {
  unreviewed: "neutral",
  reviewed: "verified",
  disputed: "high",
  corrected: "review",
};

export function ReviewBadge({ value }: { value: ReviewStatus }) {
  return <Chip label={`Review: ${title(value)}`} tone={REVIEW_TONE[value]} />;
}

const VERIFICATION_TONE: Record<VerificationState, string> = {
  verified: "verified",
  unverified: "medium",
  missing: "high",
  demo_placeholder: "review",
};

export function VerificationBadge({ value }: { value: VerificationState }) {
  return <Chip label={`Verification: ${title(value.replace(/_/g, " "))}`} tone={VERIFICATION_TONE[value]} />;
}

/** A neutral label chip (topics, change types, source types, tiers). */
export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "whitespace-nowrap border-stone-200 bg-stone-50 font-normal text-stone-600 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300",
        className,
      )}
    >
      {children}
    </Badge>
  );
}
