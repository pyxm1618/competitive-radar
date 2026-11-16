"use client";

import { Home, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
        Something broke
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">This page failed to render.</h1>
      <p className="mt-3 max-w-md text-sm text-muted-foreground">
        An unexpected error interrupted the page. Retrying usually fixes it.
      </p>
      {error.digest && <p className="tabular mt-2 text-xs text-muted-foreground">ref {error.digest}</p>}

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 rounded-lg border px-4 py-2 text-sm font-medium hover:bg-secondary"
        >
          <Home className="h-4 w-4" /> Back to Radar
        </Link>
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-1.5 rounded-lg bg-foreground px-4 py-2 text-sm font-semibold text-background hover:opacity-90"
        >
          <RotateCcw className="h-4 w-4" /> Try again
        </button>
      </div>
    </div>
  );
}
