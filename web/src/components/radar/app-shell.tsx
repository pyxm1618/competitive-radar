"use client";

import { Building2, FileText, Radar, Tags } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const NAV: NavItem[] = [
  { href: "/", label: "Radar", icon: Radar },
  { href: "/topics", label: "Topics", icon: Tags },
  { href: "/competitors", label: "Competitors", icon: Building2 },
  { href: "/evidence", label: "Evidence", icon: FileText },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({
  children,
  generatedAt,
  demo,
}: {
  children: ReactNode;
  generatedAt: string;
  demo: boolean;
}) {
  const pathname = usePathname() || "/";

  return (
    <div className="min-h-screen">
      {demo && (
        <div className="border-b border-rose-300 bg-rose-100 px-4 py-2 text-center text-xs font-semibold text-rose-900 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-200">
          DEMO DATA — not authoritative. This is a demonstration build, not real competitive
          intelligence.
        </div>
      )}

      <div className="flex min-h-screen">
        {/* Desktop sidebar */}
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r bg-card md:flex">
          <div className="flex items-center gap-2.5 border-b px-4 py-4">
            <Image src="/radar-logo.svg" alt="" width={32} height={32} unoptimized />
            <div className="min-w-0">
              <p className="text-sm font-semibold leading-tight">Xiaoshuyin</p>
              <p className="text-xs text-muted-foreground">Competitive Radar</p>
            </div>
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Primary">
            {NAV.map((item) => {
              const active = isActive(pathname, item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-secondary text-foreground"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="space-y-2 border-t px-4 py-4 text-[11px] text-muted-foreground">
            <p className="font-semibold uppercase tracking-wide">READ-ONLY · static snapshot</p>
            <p className="tabular break-all">Generated: {generatedAt || "—"}</p>
            <div className="pt-1">
              <ThemeToggle />
            </div>
          </div>
        </aside>

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* Mobile top bar */}
          <header className="flex items-center justify-between gap-3 border-b bg-card px-4 py-3 md:hidden">
            <div className="flex items-center gap-2">
              <Image src="/radar-logo.svg" alt="" width={28} height={28} unoptimized />
              <span className="text-sm font-semibold">Xiaoshuyin Competitive Radar</span>
            </div>
            <ThemeToggle />
          </header>

          <main className="mx-auto w-full max-w-5xl min-w-0 flex-1 px-4 pb-28 pt-6 sm:px-6 md:px-8 md:pb-10 lg:px-10">
            {children}
          </main>

          <footer className="border-t px-4 py-4 text-center text-[11px] text-muted-foreground md:hidden">
            READ-ONLY · static snapshot · generated {generatedAt || "—"}
          </footer>
        </div>
      </div>

      {/* Mobile bottom nav: exactly four columns */}
      <nav
        className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 border-t bg-card/95 backdrop-blur md:hidden"
        aria-label="Primary mobile"
      >
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
                active ? "text-primary" : "text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
