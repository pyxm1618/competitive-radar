"use client";

import { ThemeProvider } from "next-themes";
import type { ReactNode } from "react";

/** Minimal providers: theming only. No data fetching, no caches, no toasts. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  );
}
