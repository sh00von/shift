import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { DocsSidebar } from "@/components/docs/DocsSidebar";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Documentation — SHIFT",
  description:
    "User guide and technical reference for SHIFT (Shoreline Intelligence, Forecasting & Trends).",
};

// The root layout locks <body> to `overflow-hidden` for the fullscreen GIS
// workbench. The docs section re-enables normal document scrolling inside its
// own height-bounded container, and mirrors the app's monochrome shell:
// white chrome on a slate-50 canvas with gb-surface cards.
export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen flex-col bg-slate-50 text-foreground">
      {/* Top bar — mirrors the workbench ribbon */}
      <header className="flex h-14 flex-shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 select-none">
        <Link href="/" className="flex items-center gap-2.5 pr-1">
          <img
            src="/logo.png"
            alt="SHIFT"
            className="h-8 w-8 rounded-lg object-cover"
          />
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight text-slate-900">
              SHIFT Docs
            </div>
            <div className="text-[11px] text-slate-500">
              Shoreline Intelligence, Forecasting &amp; Trends
            </div>
          </div>
        </Link>
        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
          >
            Open Workbench <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      {/* Body: sidebar + scrollable canvas */}
      <div className="flex min-h-0 flex-1">
        <aside className="docs-scroll hidden w-72 flex-shrink-0 overflow-y-auto border-r border-slate-200 bg-white md:block">
          <DocsSidebar />
        </aside>
        <main className="docs-scroll min-w-0 flex-1 overflow-y-auto bg-white">
          <div className="mx-auto max-w-3xl px-6 py-10 lg:px-10">
            {children}
            <p className="mt-10 border-t border-slate-200 pt-6 text-[11px] text-slate-400">
              SHIFT — Shoreline Intelligence, Forecasting &amp; Trends · Open source
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
