"use client";

import Link from "next/link";
import { MapPin, ArrowLeft, BookOpen } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50 font-sans text-slate-900">
      {/* Thin top bar matching TopAppBar height */}
      <div className="flex h-10 flex-shrink-0 items-center border-b border-slate-200 bg-white px-4">
        <span className="text-[13px] font-semibold tracking-tight text-slate-900">SHIFT</span>
        <span className="ml-1.5 text-[11px] font-medium text-slate-400">Shoreline Intelligence</span>
      </div>

      {/* Body */}
      <main className="flex flex-1 items-center justify-center">
        <div className="flex flex-col items-center gap-6 text-center">
          {/* Icon */}
          <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
            <MapPin className="h-6 w-6 text-slate-400" />
          </div>

          {/* Code + message */}
          <div className="space-y-2">
            <p className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              404
            </p>
            <h1 className="text-xl font-semibold text-slate-900">Page not found</h1>
            <p className="max-w-xs text-sm text-slate-500">
              This coordinate doesn&apos;t exist in the workspace. The page may have moved or never existed.
            </p>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to map
            </Link>
            <Link
              href="/docs"
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <BookOpen className="h-3.5 w-3.5" />
              Documentation
            </Link>
          </div>
        </div>
      </main>

      {/* Status bar matching the app */}
      <div className="flex h-6 flex-shrink-0 items-center border-t border-slate-200 bg-white px-4">
        <span className="font-mono text-[10px] text-slate-400">EPSG:4326 · WGS 84</span>
      </div>
    </div>
  );
}
