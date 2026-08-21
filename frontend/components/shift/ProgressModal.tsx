"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Layers, Activity, BarChart3, Sparkles, TrendingUp } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const LEVEL_DOT: Record<string, string> = {
  ERROR: "bg-rose-500",
  WARN: "bg-amber-500",
  SUCCESS: "bg-emerald-500",
  INFO: "bg-sky-500",
};

// Jobs that stream real progress over the websocket — get a % bar + stage stepper.
const PROGRESS_JOBS = new Set(["Run Rate Analysis", "Cast Transects", "Update Forecast"]);
// Jobs that run as a single REST call — get an indeterminate animated bar.
const INDETERMINATE_JOBS = new Set([
  "Load Demo Dataset",
  "Upload Shorelines",
  "Upload Baseline",
]);

const STAGES = [
  { label: "Ingest", minP: 0.05, maxP: 0.12, icon: Layers },
  { label: "Transects", minP: 0.15, maxP: 0.24, icon: Activity },
  { label: "Intersect", minP: 0.25, maxP: 0.4, icon: BarChart3 },
  { label: "Models", minP: 0.45, maxP: 0.88, icon: Sparkles },
  { label: "Forecast", minP: 0.9, maxP: 1.0, icon: TrendingUp },
];

export function ProgressModal() {
  const { running, status, progress, activeJobName, logs } = useStore();
  const jobStartTime = useStore((s) => s.jobStartTime);
  const [elapsed, setElapsed] = useState("0.0s");
  const logEndRef = useRef<HTMLDivElement>(null);

  const streamed = !!activeJobName && PROGRESS_JOBS.has(activeJobName);
  const indeterminate = !!activeJobName && INDETERMINATE_JOBS.has(activeJobName);
  const show = running && (streamed || indeterminate);

  // Jobs that run as one REST call have no real % — simulate a smooth climb
  // toward ~92% that eases out, so the user still sees a moving percentage.
  const [simPct, setSimPct] = useState(8);
  useEffect(() => {
    if (!show || !indeterminate) {
      setSimPct(8);
      return;
    }
    const t = setInterval(() => {
      setSimPct((p) => (p >= 92 ? 92 : p + (92 - p) * 0.07));
    }, 120);
    return () => clearInterval(t);
  }, [show, indeterminate, activeJobName]);

  useEffect(() => {
    if (!show || !jobStartTime) return;
    const t = setInterval(() => setElapsed(`${((Date.now() - jobStartTime) / 1000).toFixed(1)}s`), 100);
    return () => clearInterval(t);
  }, [show, jobStartTime]);

  useEffect(() => {
    if (show) logEndRef.current?.scrollIntoView({ block: "end" });
  }, [logs, show]);

  if (!show) return null;

  const realPct = Math.min(100, Math.max(0, Math.round(progress * 100)));
  const pct = indeterminate ? Math.round(simPct) : realPct;
  const showStages = activeJobName === "Run Rate Analysis";

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-900/30 p-4 backdrop-blur-sm">
      <div className="gb-surface w-[440px] max-w-full p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            </span>
            <div>
              <div className="text-[15px] font-semibold text-slate-900">{activeJobName}</div>
              <div className="text-[12px] text-slate-400">Working — this may take a moment</div>
            </div>
          </div>
          <span className="gb-num text-[12px] text-slate-400">{elapsed}</span>
        </div>

        {/* Progress bar */}
        <div className="mt-5 space-y-2">
          <div className="flex items-center justify-between text-[13px]">
            <span className="truncate pr-3 text-slate-600">
              {indeterminate ? "Processing…" : status}
            </span>
            <span className="gb-num font-semibold text-primary">{pct}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Stage stepper (analysis only) */}
        {showStages && (
          <div className="mt-5 grid grid-cols-5 gap-2">
            {STAGES.map((s) => {
              const past = progress >= s.maxP || pct === 100;
              const current = progress >= s.minP && progress < s.maxP;
              const Icon = s.icon;
              return (
                <div
                  key={s.label}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg border px-1 py-2 text-center transition-colors",
                    current
                      ? "border-primary/30 bg-primary/5 text-primary"
                      : past
                      ? "border-emerald-200 bg-emerald-50/60 text-emerald-700"
                      : "border-slate-100 text-slate-300"
                  )}
                >
                  <Icon className={cn("h-4 w-4", current && "animate-pulse")} />
                  <span className="text-[10px] font-medium leading-tight">{s.label}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Live log tail */}
        <div className="mt-5 h-28 overflow-y-auto rounded-lg border border-slate-100 bg-slate-50/60 p-2.5">
          {logs.length === 0 ? (
            <div className="py-4 text-center text-[12px] text-slate-400">Waiting for events…</div>
          ) : (
            <div className="space-y-0.5">
              {logs.slice(-40).map((log) => (
                <div key={log.id} className="flex items-baseline gap-2">
                  <span className={cn("mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full", LEVEL_DOT[log.level] || "bg-slate-400")} />
                  <span className="gb-num text-[10px] text-slate-400">{log.time}</span>
                  <span className="gb-num flex-1 break-words text-[12px] text-slate-600">{log.text}</span>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
