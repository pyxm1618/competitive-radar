/**
 * The single compiled data contract for the Xiaoshuyin Competitive Radar.
 *
 * These types mirror the shape produced by `radar build` into
 * `public/radar-static/radar.json`. The frontend is a pure, read-only
 * renderer: it MUST NOT define a second competitor list or any other
 * business-data truth. Everything displayed comes from `RadarData`.
 */

export type Impact = "high" | "medium" | "low";
export type Confidence = "high" | "medium" | "low";
export type Relevance = "high" | "medium" | "low";
export type Decision = "act" | "investigate" | "watch" | "ignore";
export type ReviewStatus = "unreviewed" | "reviewed" | "disputed" | "corrected";
export type VerificationState =
  | "unverified"
  | "verified"
  | "missing"
  | "demo_placeholder";

export interface Topic {
  id: string;
  label: string;
  description: string;
  intelligence_count: number;
  competitor_ids: string[];
  evidence_ids: string[];
}

export interface TrackedSource {
  source_id: string;
  url: string;
  source_type: string;
}

export interface TimelineEvent {
  date: string;
  intelligence_id: string;
  title: string;
  summary: string;
  decision: Decision;
  topic_ids: string[];
  change_id: string;
}

export interface Competitor {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  tier: number;
  why_tracked: string | null;
  tracked_sources: TrackedSource[];
  topic_ids: string[];
  latest_intelligence_at: string | null;
  intelligence_count: number;
  evidence_count: number;
  timeline: TimelineEvent[];
}

export interface Intelligence {
  intelligence_id: string;
  change_id: string;
  competitor_id: string;
  date: string;
  summary: string;
  topic_ids: string[];
  change_type: string;
  impact: Impact;
  confidence: Confidence;
  relevance: Relevance;
  decision: Decision;
  xiaoshuyin_relevance: string;
  mechanism: string;
  why_it_matters: string;
  evidence_ids: string[];
  human_review_status: ReviewStatus;
  analyst: string;
  provenance: {
    pending_file: string;
    snapshot_before: string | null;
    snapshot_after: string | null;
    url: string;
  };
}

export interface Evidence {
  evidence_id: string;
  intelligence_ids: string[];
  competitor_id: string;
  type: string;
  kind: "raw" | "manual";
  url: string | null;
  snapshot_ref: string | null;
  content_hash: string | null;
  captured_at: string | null;
  title: string;
  extract: string | null;
  image_path: string | null;
  file_path: string | null;
  verification_state: VerificationState;
  before_evidence_id: string | null;
  after_evidence_id: string | null;
}

export interface BeforeAfter {
  change_id: string;
  competitor_id: string;
  url: string;
  before: Evidence | null;
  after: Evidence | null;
  diff: string;
}

export interface ManualResearch {
  request_id: string;
  competitor_id: string | null;
  topic_ids: string[];
  research_question: string;
  why_needed: string;
  suggested_steps: string[];
  required_evidence: { label: string; required: boolean; satisfied: boolean }[];
  status: string;
  created_at: string;
  created_by: string;
}

export interface WeeklyPulse {
  week_start: string;
  week_end: string;
  total_changes: number;
  important_changes: number;
  top_changes: {
    intelligence_id: string;
    competitor_id: string;
    summary: string;
    impact: Impact;
    decision: Decision;
  }[];
  cross_competitor_themes: {
    topic_id: string;
    label: string;
    intelligence_count: number;
    competitor_ids: string[];
  }[];
  by_decision: { act: number; investigate: number; watch: number; ignore: number };
  manual_research_needed: number;
}

export interface RadarData {
  generated_at: string;
  demo: boolean;
  authority: Record<string, string>;
  summary: {
    tracked_competitors: number;
    tracked_sources: number;
    detected_changes: number;
    important_changes: number;
    pending_intelligence: number;
    manual_research_requests: number;
  };
  topics: Topic[];
  competitors: Competitor[];
  intelligence: Intelligence[];
  evidence: Evidence[];
  before_after: BeforeAfter[];
  manual_research: ManualResearch[];
  weekly: WeeklyPulse;
}
