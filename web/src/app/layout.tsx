import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "@/components/providers";
import { AppShell } from "@/components/radar/app-shell";
import { getRadarData } from "@/lib/radar-data";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Xiaoshuyin Competitive Radar",
    template: "%s · Xiaoshuyin Competitive Radar",
  },
  description:
    "A static, read-only renderer of compiled competitive intelligence: tracked competitors, topics, detected changes, raw evidence and AI interpretation.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/radar-logo.svg", type: "image/svg+xml" },
    ],
    shortcut: "/favicon.ico",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const data = getRadarData();

  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <Providers>
          <AppShell generatedAt={data.generated_at} demo={data.demo}>
            {children}
          </AppShell>
        </Providers>
      </body>
    </html>
  );
}
