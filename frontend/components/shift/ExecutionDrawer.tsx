"use client";

import { useEffect, useRef, useState } from "react";
import {
  Layers,
  Activity,
  BarChart3,
  Sparkles,
  TrendingUp,
  Clock,
  ChevronDown,
  ChevronUp,
  X,
} from "lucide-react";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const STAGES = [
  { id: "ingest", label: "Ingest", minP: 0.05, maxP: 0.12, icon: Layers },
  { id: "cast", label: "Transects", minP: 0.15, maxP: 0.22, icon: Activity },
  { id: "series", label: "Intersect", minP: 0.25, maxP: 0.4, icon: BarChart3 },
  { id: "models", label: "Models", minP: 0.45, maxP: 0.88, icon: Sparkles },
  { id: "forecast", label: "Forecast", minP: 0.9, maxP: 1.0, icon: TrendingUp },
];

const DOT: Record<string, string> = {
  ERROR: "bg-rose-500",
  WARN: "bg-amber-500",
  SUCCESS: "bg-emerald-500",
  INFO: "bg-sky-500",
};

export function ExecutionDrawer() {
  const { running, status, progress, activeJobName, jobStartTime, logs, isExecutionDrawerOpen, setExecutionDrawerOpen } =
    useStore();

  const [elapsed, setElapsed] = useState("0.0s");
  const [minimized, setMinimized] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!running || !jobStartTime) return;
    const t = setInterval(() => setElapsed(`${((Date.now() - jobStartTime) / 1000).toFixed(1)}s`), 100);
    return () => clearInterval(t);
  }, [running, jobStartTime]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logs]);

  if (!isExecutionDrawerOpen && !running) return null;

  const pct = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <div
      className={cn(
        "gb-surface fixed bottom-4 right-4 z-[9999] w-[420px] max-w-[calc(100vw-2rem)] overflow-hidden",
        minimized ? "h-auto" : "h-[400px]"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="gb-section-title">{activeJobName || "Execution"}</span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-medium",
              running ? "bg-primary/10 text-primary" : pct === 100 ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"
            )}
          >
            {running ? "Running" : pct === 100 ? "Done" : "Idle"}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {running && (
            <span className="mr-1 flex items-center gap-1 gb-num text-[11px] text-slate-400">
              <Clock className="h-3.5 w-3.5" /> {elapsed}
            </span>
          )}
          <Button size="icon" variant="ghost" className="h-7 w-7 text-slate-400" onClick={() => setMinimized(!minimized)}>
            {minimized ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button size="icon" variant="ghost" className="h-7 w-7 text-slate-400" onClick={() => setExecutionDrawerOpen(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Progress + stages */}
      <div className="space-y-3 border-b border-slate-100 p-4">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[12px]">
            <span className="truncate text-slate-600">{status}</span>
            <span className="gb-num font-semibold text-primary">{pct}%</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-primary transition-all duration-300 ease-out" style={{ width: `${pct}%` }} />
          </div>
        </div>

        {!minimized && (
          <div className="grid grid-cols-5 gap-1.5">
            {STAGES.map((s) => {
              const past = progress >= s.maxP || pct === 100;
              const current = progress >= s.minP && progress < s.maxP && running;
              const Icon = s.icon;
              return (
                <div
                  key={s.id}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg border px-1 py-2 text-center transition-colors",
                    current ? "border-primary/30 bg-primary/5 text-primary"
                      : past ? "border-emerald-200 bg-emerald-50/50 text-emerald-700"
                      : "border-slate-100 text-slate-300"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-[10px] font-medium leading-tight">{s.label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Log stream */}
      {!minimized && (
        <div ref={logRef} className="shift-scroll h-[200px] space-y-0.5 overflow-y-auto p-3">
          {logs.length === 0 ? (
            <div className="py-6 text-center text-[13px] text-slate-400">Waiting for pipeline events…</div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className="flex items-baseline gap-2.5 rounded-md px-1.5 py-1 hover:bg-slate-50">
                <span className={cn("mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full", DOT[log.level] || "bg-slate-400")} />
                <span className="gb-num text-[11px] text-slate-400">{log.time}</span>
                <span className="gb-num flex-1 break-words text-[12px] text-slate-600">{log.text}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
