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
    <div className="relative flex h-full min-h-screen flex-col items-center justify-center overflow-hidden bg-[#0d1117]">
      {/* Background grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Radial glow */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-rose-500/5 blur-3xl" />

      <div className="relative z-10 flex w-full max-w-md flex-col items-center gap-6 px-6 text-center">
        {/* Icon */}
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-500/10">
          <AlertTriangle className="h-7 w-7 text-rose-400" />
        </div>

        {/* Heading */}
        <div className="space-y-2">
          <h1 className="text-xl font-semibold text-white">Something went wrong</h1>
          <p className="text-sm text-[#6b7280]">
            The analysis engine hit an unexpected error. Your session data is safe — try refreshing to recover.
          </p>
        </div>

        {/* Error detail */}
        {error.message && (
          <div className="w-full rounded-lg border border-[#252830] bg-[#1a1d23] p-4 text-left">
            <div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-[#555]">
              <Terminal className="h-3 w-3" />
              Error detail
            </div>
            <p className="break-all font-mono text-[11px] leading-relaxed text-rose-300/80">
              {error.message}
            </p>
            {error.digest && (
              <p className="mt-2 font-mono text-[10px] text-[#444]">
                digest: {error.digest}
              </p>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={reset}
            className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm font-medium text-rose-400 transition-colors hover:bg-rose-500/20 hover:text-rose-300"
          >
            <RefreshCw className="h-4 w-4" />
            Try again
          </button>
          <a
            href="/"
            className="flex items-center gap-2 rounded-lg border border-[#252830] bg-[#1a1d23] px-4 py-2 text-sm font-medium text-[#888] transition-colors hover:border-[#333] hover:text-[#bbb]"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to map
          </a>
        </div>

        {/* Branding */}
        <p className="font-mono text-[10px] uppercase tracking-widest text-[#333]">
          SHIFT · Shoreline Intelligence
        </p>
      </div>
    </div>
  );
}
