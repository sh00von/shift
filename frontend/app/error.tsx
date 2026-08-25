"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw, ArrowLeft, Terminal } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[SHIFT error boundary]", error);
  }, [error]);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-slate-50 font-sans text-slate-900">
      {/* Thin top bar matching TopAppBar height */}
      <div className="flex h-10 flex-shrink-0 items-center border-b border-slate-200 bg-white px-4">
        <span className="text-[13px] font-semibold tracking-tight text-slate-900">SHIFT</span>
        <span className="ml-1.5 text-[11px] font-medium text-slate-400">Shoreline Intelligence</span>
      </div>

      {/* Body */}
      <main className="flex flex-1 items-center justify-center px-4">
        <div className="flex w-full max-w-md flex-col items-center gap-6 text-center">
          {/* Icon */}
          <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-red-100 bg-red-50 shadow-sm">
            <AlertTriangle className="h-6 w-6 text-red-500" />
          </div>

          {/* Heading */}
          <div className="space-y-2">
            <p className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Application error
            </p>
            <h1 className="text-xl font-semibold text-slate-900">Something went wrong</h1>
            <p className="text-sm text-slate-500">
              The analysis engine hit an unexpected error. Try refreshing — your session data should recover automatically.
            </p>
          </div>

          {/* Error detail */}
          {error.message && (
            <div className="w-full rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm">
              <div className="mb-2 flex items-center gap-1.5">
                <Terminal className="h-3 w-3 text-slate-400" />
                <span className="font-mono text-[10px] font-semibold uppercase tracking-widest text-slate-400">
                  Error detail
                </span>
              </div>
              <p className="break-all font-mono text-[11px] leading-relaxed text-red-600">
                {error.message}
              </p>
              {error.digest && (
                <p className="mt-2 font-mono text-[10px] text-slate-400">
                  digest: {error.digest}
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={reset}
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Try again
            </button>
            <a
              href="/"
              className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-[13px] font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to map
            </a>
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
