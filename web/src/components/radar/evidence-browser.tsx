"use client";

import { useMemo, useState } from "react";

import {
  DecisionBadge,
  ImpactBadge,
  Tag,
  VerificationBadge,
} from "@/components/radar/badges";
import { EvidenceView } from "@/components/radar/evidence-view";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import type { Topic } from "@/lib/radar-types";
import type { EvidenceItemView, InterpretationView } from "@/lib/radar-view";

const ALL = "__all__";
const VERIFICATION_STATES = ["verified", "unverified", "missing", "demo_placeholder"] as const;
const WEAK_VERIFICATION = new Set(["unverified", "missing", "demo_placeholder"]);

interface CompetitorOption {
  id: string;
  name: string;
}

interface EvidenceBrowserProps {
  items: EvidenceItemView[];
  interpretations: InterpretationView[];
  topics: Topic[];
  competitors: CompetitorOption[];
}

function Distinct({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <Select value={value} onChange={(event) => onChange(event.target.value)} aria-label={label}>
        <option value={ALL}>All</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </label>
  );
}

/**
 * Evidence browser. RAW evidence and AI INTERPRETATION are deliberately kept
 * in separate, explicitly-labelled sections. Interpretations are always
 * rendered (never filtered) so that `/evidence#<intelligence_id>` anchors from
 * other pages always resolve on this static page.
 */
export function EvidenceBrowser({
  items,
  interpretations,
  topics,
  competitors,
}: EvidenceBrowserProps) {
  const [competitor, setCompetitor] = useState(ALL);
  const [date, setDate] = useState(ALL);
  const [topic, setTopic] = useState(ALL);
  const [sourceType, setSourceType] = useState(ALL);
  const [verification, setVerification] = useState(ALL);

  const competitorNames = useMemo(() => {
    const map: Record<string, string> = {};
    for (const c of competitors) map[c.id] = c.name;
    return map;
  }, [competitors]);

  const topicLabels = useMemo(() => {
    const map: Record<string, string> = {};
    for (const t of topics) map[t.id] = t.label;
    return map;
  }, [topics]);

  const dates = useMemo(
    () =>
      Array.from(new Set(items.map((item) => item.date).filter((d) => d.length > 0))).sort(
        (a, b) => b.localeCompare(a),
      ),
    [items],
  );
  const sourceTypes = useMemo(
    () => Array.from(new Set(items.map((item) => item.evidence.type))).sort(),
    [items],
  );

  const filtered = useMemo(
    () =>
      items.filter((item) => {
        if (competitor !== ALL && item.evidence.competitor_id !== competitor) return false;
        if (date !== ALL && item.date !== date) return false;
        if (topic !== ALL && !item.topicIds.includes(topic)) return false;
        if (sourceType !== ALL && item.evidence.type !== sourceType) return false;
        if (verification !== ALL && item.evidence.verification_state !== verification) return false;
        return true;
      }),
    [items, competitor, date, topic, sourceType, verification],
  );

  const weakCount = items.filter((item) =>
    WEAK_VERIFICATION.has(item.evidence.verification_state),
  ).length;

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader className="border-b bg-muted/30">
          <p className="text-sm font-semibold">Filter RAW evidence</p>
        </CardHeader>
        <CardContent className="grid gap-3 pt-5 sm:grid-cols-2 lg:grid-cols-5">
          <Distinct
            label="Competitor"
            value={competitor}
            onChange={setCompetitor}
            options={competitors.map((c) => ({ value: c.id, label: c.name }))}
          />
          <Distinct
            label="Date"
            value={date}
            onChange={setDate}
            options={dates.map((d) => ({ value: d, label: d }))}
          />
          <Distinct
            label="Topic"
            value={topic}
            onChange={setTopic}
            options={topics.map((t) => ({ value: t.id, label: t.label }))}
          />
          <Distinct
            label="Source / type"
            value={sourceType}
            onChange={setSourceType}
            options={sourceTypes.map((s) => ({ value: s, label: s }))}
          />
          <Distinct
            label="Verification"
            value={verification}
            onChange={setVerification}
            options={VERIFICATION_STATES.map((s) => ({
              value: s,
              label: s.replace(/_/g, " "),
            }))}
          />
        </CardContent>
      </Card>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-10 text-center">
          <p className="text-sm font-semibold">No raw evidence has been compiled yet</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Evidence snapshots, extracts and hashes appear here once an authoritative{" "}
            <code className="rounded bg-muted px-1">radar build</code> has produced them.
          </p>
        </div>
      ) : (
        <>
          {weakCount > 0 && (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
              <strong>Missing verification:</strong> {weakCount} of {items.length} evidence record(s)
              are unverified, missing, or demo placeholders. They are flagged on each card below.
            </p>
          )}

          {/* ---- RAW EVIDENCE section ---- */}
          <section>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                  RAW evidence
                </span>
                <span className="text-xs text-muted-foreground">
                  snapshots · extracts · screenshots · original URLs
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                <span className="tabular font-semibold text-foreground">{filtered.length}</span> of{" "}
                <span className="tabular font-semibold text-foreground">{items.length}</span> shown
              </span>
            </div>

            {filtered.length > 0 ? (
              <div className="grid gap-4 lg:grid-cols-2">
                {filtered.map((item) => (
                  <div key={item.evidence.evidence_id} id={`evidence-${item.evidence.evidence_id}`}>
                    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                      {item.topicIds.length > 0 ? (
                        item.topicIds.map((id) => (
                          <Tag key={id}>{topicLabels[id] ?? id}</Tag>
                        ))
                      ) : (
                        <Tag>No topic</Tag>
                      )}
                      <span className="ml-auto text-[11px] text-muted-foreground">
                        {competitorNames[item.evidence.competitor_id] ?? item.evidence.competitor_id}
                      </span>
                    </div>
                    <EvidenceView evidence={item.evidence} />
                    {item.evidence.intelligence_ids.length > 0 && (
                      <p className="mt-1.5 text-[11px] text-muted-foreground">
                        Related AI interpretation:{" "}
                        {item.evidence.intelligence_ids.map((id) => (
                          <a
                            key={id}
                            href={`#${id}`}
                            className="mr-1 font-medium text-primary underline underline-offset-2 hover:opacity-80"
                          >
                            {id}
                          </a>
                        ))}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
                No RAW evidence matches these filters.
              </div>
            )}
          </section>
        </>
      )}

      {/* ---- AI INTERPRETATION section (always rendered for anchors) ---- */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded bg-violet-100 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-violet-800 dark:bg-violet-950 dark:text-violet-300">
            AI interpretation
          </span>
          <span className="text-xs text-muted-foreground">
            generated analysis — each block is an anchor target (#intelligence_id)
          </span>
        </div>
        {interpretations.length > 0 ? (
          <div className="space-y-4">
            {interpretations.map((interp) => (
              <Card
                key={interp.intelligence.intelligence_id}
                id={interp.intelligence.intelligence_id}
                className="scroll-mt-24 border-violet-200 dark:border-violet-900"
              >
                <CardHeader className="gap-2 border-b bg-muted/30">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold">{interp.competitorName}</p>
                      <p className="tabular text-xs text-muted-foreground">
                        {interp.intelligence.date}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      <ImpactBadge value={interp.intelligence.impact} />
                      <DecisionBadge value={interp.intelligence.decision} />
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3 pt-4">
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                    {interp.intelligence.summary || "No summary was produced for this record."}
                  </p>
                  {interp.topics.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {interp.topics.map((t) => (
                        <Tag key={t.id}>{t.label}</Tag>
                      ))}
                    </div>
                  )}
                  <div className="border-t pt-3">
                    <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                      Underlying RAW evidence
                    </p>
                    {interp.evidence.length > 0 ? (
                      <ul className="flex flex-wrap gap-2">
                        {interp.evidence.map((ev) => (
                          <li key={ev.evidence_id}>
                            <a
                              href={`#evidence-${ev.evidence_id}`}
                              className="inline-flex items-center gap-1.5 rounded-md border bg-background px-2 py-1 text-xs hover:bg-secondary"
                            >
                              <span className="max-w-[16rem] truncate">{ev.title}</span>
                              <VerificationBadge value={ev.verification_state} />
                            </a>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-muted-foreground">No RAW evidence linked.</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            No AI interpretations have been compiled yet. Anchors will appear here once intelligence
            records are produced.
          </div>
        )}
      </section>
    </div>
  );
}
