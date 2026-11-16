"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

import { Tag } from "@/components/radar/badges";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { Competitor, Topic } from "@/lib/radar-types";

const ALL = "__all__";

/** Client-side search + tier + topic filter over ALL configured competitors. */
export function CompetitorsBrowser({
  competitors,
  topics,
}: {
  competitors: Competitor[];
  topics: Topic[];
}) {
  const [query, setQuery] = useState("");
  const [tier, setTier] = useState(ALL);
  const [topic, setTopic] = useState(ALL);

  const tiers = useMemo(
    () => Array.from(new Set(competitors.map((c) => c.tier))).sort((a, b) => a - b),
    [competitors],
  );
  const topicLabels = useMemo(() => {
    const map: Record<string, string> = {};
    for (const t of topics) map[t.id] = t.label;
    return map;
  }, [topics]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return competitors.filter((c) => {
      if (tier !== ALL && c.tier !== Number(tier)) return false;
      if (topic !== ALL && !c.topic_ids.includes(topic)) return false;
      if (q) {
        const haystack = `${c.name} ${c.domain ?? ""} ${c.industry ?? ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
  }, [competitors, query, tier, topic]);

  return (
    <div>
      <div className="mb-5 grid gap-3 sm:grid-cols-3">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search name, domain, industry…"
          aria-label="Search competitors"
        />
        <Select value={tier} onChange={(event) => setTier(event.target.value)} aria-label="Tier">
          <option value={ALL}>All tiers</option>
          {tiers.map((value) => (
            <option key={value} value={String(value)}>
              Tier {value}
            </option>
          ))}
        </Select>
        <Select value={topic} onChange={(event) => setTopic(event.target.value)} aria-label="Topic">
          <option value={ALL}>All topics</option>
          {topics.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </Select>
      </div>

      <p className="mb-3 text-xs text-muted-foreground">
        <span className="tabular font-semibold text-foreground">{filtered.length}</span> of{" "}
        <span className="tabular font-semibold text-foreground">{competitors.length}</span>{" "}
        competitors
      </p>

      {filtered.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((competitor) => (
            <Card key={competitor.id} className="flex flex-col">
              <CardContent className="flex flex-1 flex-col gap-3 pt-5">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    href={`/competitors/${encodeURIComponent(competitor.id)}`}
                    className="text-base font-semibold leading-tight hover:underline"
                  >
                    {competitor.name}
                  </Link>
                  <Tag>Tier {competitor.tier}</Tag>
                </div>
                <p className="text-xs text-muted-foreground">
                  {competitor.domain ?? "No domain"} · {competitor.industry ?? "No industry"}
                </p>

                <div className="flex flex-wrap gap-1.5">
                  {competitor.topic_ids.length > 0 ? (
                    competitor.topic_ids.map((id) => (
                      <Tag key={id}>{topicLabels[id] ?? id}</Tag>
                    ))
                  ) : (
                    <Tag>No topics</Tag>
                  )}
                </div>

                <dl className="mt-auto grid grid-cols-3 gap-2 border-t pt-3 text-center">
                  <div>
                    <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      Changes
                    </dt>
                    <dd className="tabular text-sm font-semibold">{competitor.intelligence_count}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      Evidence
                    </dt>
                    <dd className="tabular text-sm font-semibold">{competitor.evidence_count}</dd>
                  </div>
                  <div>
                    <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
                      Latest
                    </dt>
                    <dd className="tabular text-xs font-medium">
                      {competitor.latest_intelligence_at ?? "—"}
                    </dd>
                  </div>
                </dl>

                <Link
                  href={`/competitors/${encodeURIComponent(competitor.id)}`}
                  className="text-xs font-medium text-primary underline underline-offset-2 hover:opacity-80"
                >
                  View profile &amp; timeline →
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
          No competitors match these filters.
        </div>
      )}
    </div>
  );
}
