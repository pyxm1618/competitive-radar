import type { Metadata } from "next";

import { PageHeader } from "@/components/page-header";
import { EvidenceBrowser } from "@/components/radar/evidence-browser";
import {
  competitorNamesMap,
  evidenceByIds,
  getRadarData,
  topicsForIds,
} from "@/lib/radar-data";
import type { EvidenceItemView, InterpretationView } from "@/lib/radar-view";

export const metadata: Metadata = { title: "Evidence" };

export default function EvidencePage() {
  const data = getRadarData();
  const competitorNames = competitorNamesMap(data);

  // Derive topic ids for each raw evidence record (config links + intelligence
  // links). Nothing is invented: only ids already present in the artifact.
  const topicsByEvidence = new Map<string, Set<string>>();
  const linkTopic = (evidenceId: string, topicId: string) => {
    let set = topicsByEvidence.get(evidenceId);
    if (!set) {
      set = new Set<string>();
      topicsByEvidence.set(evidenceId, set);
    }
    set.add(topicId);
  };
  for (const topic of data.topics) {
    for (const evidenceId of topic.evidence_ids) linkTopic(evidenceId, topic.id);
  }
  for (const intel of data.intelligence) {
    for (const topicId of intel.topic_ids) {
      for (const evidenceId of intel.evidence_ids) linkTopic(evidenceId, topicId);
    }
  }

  // Best-effort date for filtering: captured_at, else the linked intel date.
  const dateByEvidence = new Map<string, string>();
  for (const intel of data.intelligence) {
    for (const evidenceId of intel.evidence_ids) {
      if (!dateByEvidence.has(evidenceId)) dateByEvidence.set(evidenceId, intel.date);
    }
  }

  const items: EvidenceItemView[] = data.evidence.map((evidence) => ({
    evidence,
    competitorName: competitorNames[evidence.competitor_id] ?? evidence.competitor_id,
    topicIds: Array.from(topicsByEvidence.get(evidence.evidence_id) ?? []),
    date: evidence.captured_at ?? dateByEvidence.get(evidence.evidence_id) ?? "",
  }));

  const interpretations: InterpretationView[] = data.intelligence.map((intelligence) => ({
    intelligence,
    competitorName: competitorNames[intelligence.competitor_id] ?? intelligence.competitor_id,
    topics: topicsForIds(data, intelligence.topic_ids),
    evidence: evidenceByIds(data, intelligence.evidence_ids),
  }));

  return (
    <div>
      <PageHeader
        title="Evidence"
        description="RAW evidence (snapshots, extracts, hashes, screenshots) is kept visibly separate from AI interpretation. Filter locally; every block is a static anchor target."
      />
      <EvidenceBrowser
        items={items}
        interpretations={interpretations}
        topics={data.topics}
        competitors={data.competitors.map((competitor) => ({
          id: competitor.id,
          name: competitor.name,
        }))}
      />
    </div>
  );
}
