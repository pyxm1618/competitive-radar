import { Building2 } from "lucide-react";
import type { Metadata } from "next";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { CompetitorsBrowser } from "@/components/radar/competitors-browser";
import { getRadarData } from "@/lib/radar-data";

export const metadata: Metadata = { title: "Competitors" };

export default function CompetitorsPage() {
  const data = getRadarData();

  return (
    <div>
      <PageHeader
        title="Competitors"
        description="Every competitor configured in the authoritative artifact. Search and filter locally; nothing is added, edited or removed."
      />
      {data.competitors.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No competitors are configured"
          description="The compiled artifact contains no competitors. They come from the authoritative config/competitors.yaml and are produced by `radar build`."
        />
      ) : (
        <CompetitorsBrowser competitors={data.competitors} topics={data.topics} />
      )}
    </div>
  );
}
