import "server-only";

import { readFileSync } from "node:fs";
import { join } from "node:path";

import type {
  BeforeAfter,
  Competitor,
  Evidence,
  Intelligence,
  RadarData,
  Topic,
} from "@/lib/radar-types";
import type { IntelligenceView } from "@/lib/radar-view";

/**
 * Server-only loader for the single compiled radar artifact.
 *
 * The frontend is a STATIC, READ-ONLY renderer. `radar.json` is the only
 * source of truth; it is produced by `radar build` from the authoritative
 * configs + intelligence files. We read it at build time with Node's fs and
 * never maintain a second competitor list or business-data copy.
 */
const DATA_PATH = join(process.cwd(), "public", "radar-static", "radar.json");

/** A complete, safe, empty dataset used when the artifact is missing/broken. */
export function emptyRadarData(): RadarData {
  return {
    generated_at: "",
    demo: false,
    authority: {},
    summary: {
      tracked_competitors: 0,
      tracked_sources: 0,
      detected_changes: 0,
      important_changes: 0,
      pending_intelligence: 0,
      manual_research_requests: 0,
    },
    topics: [],
    competitors: [],
    intelligence: [],
    evidence: [],
    before_after: [],
    manual_research: [],
    weekly: {
      week_start: "",
      week_end: "",
      total_changes: 0,
      important_changes: 0,
      top_changes: [],
      cross_competitor_themes: [],
      by_decision: { act: 0, investigate: 0, watch: 0, ignore: 0 },
      manual_research_needed: 0,
    },
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Lightweight structural guard so a malformed artifact never crashes a build. */
function isRadarData(value: unknown): value is RadarData {
  if (!isRecord(value)) return false;
  if (typeof value.generated_at !== "string" || typeof value.demo !== "boolean") return false;
  if (!isRecord(value.authority) || !isRecord(value.summary) || !isRecord(value.weekly)) {
    return false;
  }
  const arrayKeys = [
    "topics",
    "competitors",
    "intelligence",
    "evidence",
    "before_after",
    "manual_research",
  ] as const;
  return arrayKeys.every((key) => Array.isArray(value[key]));
}

let cached: RadarData | null = null;

/** Read + parse the artifact once. Missing/malformed -> safe empty dataset. */
export function getRadarData(): RadarData {
  if (cached !== null) return cached;
  try {
    const parsed: unknown = JSON.parse(readFileSync(DATA_PATH, "utf8"));
    cached = isRadarData(parsed) ? parsed : emptyRadarData();
  } catch {
    cached = emptyRadarData();
  }
  return cached;
}

/* -------------------------------------------------------------------------- */
/* Selectors                                                                  */
/* -------------------------------------------------------------------------- */

interface RadarIndex {
  topics: Map<string, Topic>;
  competitors: Map<string, Competitor>;
  evidence: Map<string, Evidence>;
  intelligence: Map<string, Intelligence>;
  beforeAfterByChange: Map<string, BeforeAfter>;
  intelligenceByCompetitor: Map<string, Intelligence[]>;
  evidenceByCompetitor: Map<string, Evidence[]>;
  intelligenceByTopic: Map<string, Intelligence[]>;
}

function push<K, V>(map: Map<K, V[]>, key: K, value: V): void {
  const list = map.get(key);
  if (list) list.push(value);
  else map.set(key, [value]);
}

function buildIndex(data: RadarData): RadarIndex {
  const index: RadarIndex = {
    topics: new Map(),
    competitors: new Map(),
    evidence: new Map(),
    intelligence: new Map(),
    beforeAfterByChange: new Map(),
    intelligenceByCompetitor: new Map(),
    evidenceByCompetitor: new Map(),
    intelligenceByTopic: new Map(),
  };
  for (const topic of data.topics) index.topics.set(topic.id, topic);
  for (const competitor of data.competitors) index.competitors.set(competitor.id, competitor);
  for (const evidence of data.evidence) index.evidence.set(evidence.evidence_id, evidence);
  for (const intelligence of data.intelligence) {
    index.intelligence.set(intelligence.intelligence_id, intelligence);
    push(index.intelligenceByCompetitor, intelligence.competitor_id, intelligence);
    for (const topicId of intelligence.topic_ids) {
      push(index.intelligenceByTopic, topicId, intelligence);
    }
  }
  for (const beforeAfter of data.before_after) {
    index.beforeAfterByChange.set(beforeAfter.change_id, beforeAfter);
  }
  for (const evidence of data.evidence) {
    push(index.evidenceByCompetitor, evidence.competitor_id, evidence);
  }
  return index;
}

// The index is memoized per dataset object; selectors stay O(1) on repeat use.
const indexCache = new WeakMap<RadarData, RadarIndex>();

function indexFor(data: RadarData): RadarIndex {
  let index = indexCache.get(data);
  if (!index) {
    index = buildIndex(data);
    indexCache.set(data, index);
  }
  return index;
}

export function topicById(data: RadarData, id: string): Topic | undefined {
  return indexFor(data).topics.get(id);
}

export function competitorById(data: RadarData, id: string): Competitor | undefined {
  return indexFor(data).competitors.get(id);
}

export function evidenceById(data: RadarData, id: string): Evidence | undefined {
  return indexFor(data).evidence.get(id);
}

export function intelligenceById(data: RadarData, id: string): Intelligence | undefined {
  return indexFor(data).intelligence.get(id);
}

export function intelligenceForCompetitor(
  data: RadarData,
  competitorId: string,
): Intelligence[] {
  return indexFor(data).intelligenceByCompetitor.get(competitorId) ?? [];
}

export function evidenceForCompetitor(data: RadarData, competitorId: string): Evidence[] {
  return indexFor(data).evidenceByCompetitor.get(competitorId) ?? [];
}

export function beforeAfterForChange(
  data: RadarData,
  changeId: string,
): BeforeAfter | undefined {
  return indexFor(data).beforeAfterByChange.get(changeId);
}

export function intelligenceForTopic(data: RadarData, topicId: string): Intelligence[] {
  return indexFor(data).intelligenceByTopic.get(topicId) ?? [];
}

/** Resolve a list of topic ids to Topic objects, dropping unknown ids. */
export function topicsForIds(data: RadarData, ids: string[]): Topic[] {
  const index = indexFor(data);
  const result: Topic[] = [];
  for (const id of ids) {
    const topic = index.topics.get(id);
    if (topic) result.push(topic);
  }
  return result;
}

/** Resolve a list of evidence ids to Evidence objects, dropping unknown ids. */
export function evidenceByIds(data: RadarData, ids: string[]): Evidence[] {
  const index = indexFor(data);
  const result: Evidence[] = [];
  for (const id of ids) {
    const evidence = index.evidence.get(id);
    if (evidence) result.push(evidence);
  }
  return result;
}

/** Build the serializable view passed into client-side intelligence cards. */
export function buildIntelligenceView(
  data: RadarData,
  item: Intelligence,
): IntelligenceView {
  return {
    item,
    competitor: competitorById(data, item.competitor_id) ?? null,
    topics: topicsForIds(data, item.topic_ids),
    evidence: evidenceByIds(data, item.evidence_ids),
    beforeAfter: beforeAfterForChange(data, item.change_id) ?? null,
  };
}

/** id -> display name map for all configured competitors. */
export function competitorNamesMap(data: RadarData): Record<string, string> {
  const map: Record<string, string> = {};
  for (const competitor of data.competitors) map[competitor.id] = competitor.name;
  return map;
}

/** id -> label map for all taxonomy topics. */
export function topicLabelsMap(data: RadarData): Record<string, string> {
  const map: Record<string, string> = {};
  for (const topic of data.topics) map[topic.id] = topic.label;
  return map;
}
