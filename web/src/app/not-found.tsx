import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
        404 — Not found
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">This page is off the radar.</h1>
      <p className="mt-3 max-w-md text-sm text-muted-foreground">
        The page you&apos;re looking for doesn&apos;t exist in this static snapshot.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-secondary"
      >
        <ArrowLeft className="h-4 w-4" /> Back to Radar
      </Link>
    </div>
  );
}
