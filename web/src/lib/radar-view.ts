import type {
  BeforeAfter,
  Competitor,
  Evidence,
  Intelligence,
  Topic,
} from "@/lib/radar-types";

/**
 * A fully-resolved, serializable view of a single intelligence record.
 *
 * Built on the server (see `buildIntelligenceView`), then passed as plain
 * props into client components. It contains no server-only references, so it
 * is safe to hand across the server/client boundary.
 */
export interface IntelligenceView {
  item: Intelligence;
  competitor: Competitor | null;
  topics: Topic[];
  evidence: Evidence[];
  beforeAfter: BeforeAfter | null;
}

/** One RAW evidence row on the Evidence page, with derived filter helpers. */
export interface EvidenceItemView {
  evidence: Evidence;
  competitorName: string;
  topicIds: string[];
  date: string;
}

/** One AI-interpretation anchor block on the Evidence page. */
export interface InterpretationView {
  intelligence: Intelligence;
  competitorName: string;
  topics: Topic[];
  evidence: Evidence[];
}
