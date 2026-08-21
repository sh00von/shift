"use client";

import { useEffect, useRef, useState } from "react";
import { Copy, Trash2, Search } from "lucide-react";
import { toast } from "sonner";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const LEVEL_DOT: Record<string, string> = {
  ERROR: "bg-rose-500",
  WARN: "bg-amber-500",
  SUCCESS: "bg-emerald-500",
  INFO: "bg-sky-500",
};

const LEVEL_TEXT: Record<string, string> = {
  ERROR: "text-rose-600",
  WARN: "text-amber-600",
  SUCCESS: "text-emerald-700",
  INFO: "text-slate-600",
};

export function ConsoleLog() {
  const { logs, clearLogs } = useStore();
  const endRef = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const filtered = logs.filter((l) => l.text.toLowerCase().includes(filter.toLowerCase()));

  const copyAll = () => {
    navigator.clipboard.writeText(logs.map((l) => `[${l.time}] [${l.level}] ${l.text}`).join("\n"));
    toast.success("Logs copied to clipboard.");
  };

  return (
    <div className="gb-panel">
      {/* Toolbar */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 px-3 py-2">
        <span className="text-[13px] text-slate-500">
          <span className="font-semibold text-slate-800">{filtered.length}</span> of {logs.length} events
        </span>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
            <Input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter…"
              className="h-9 w-48 pl-8 text-sm" />
          </div>
          <Button size="sm" variant="ghost" className="h-9 gap-1.5 text-slate-500" onClick={copyAll}>
            <Copy className="h-4 w-4" /> Copy
          </Button>
          <Button size="sm" variant="ghost" className="h-9 gap-1.5 text-slate-500 hover:text-rose-600" onClick={clearLogs}>
            <Trash2 className="h-4 w-4" /> Clear
          </Button>
        </div>
      </div>

      {/* Log body */}
      <div className="shift-scroll flex-1 overflow-y-auto px-3 py-2">
        {filtered.length === 0 ? (
          <div className="py-8 text-center text-[13px] text-slate-400">
            {logs.length === 0 ? "No events logged yet." : "No logs match the filter."}
          </div>
        ) : (
          <div className="space-y-0.5">
            {filtered.map((log) => (
              <div key={log.id} className="flex items-baseline gap-2.5 rounded-md px-1.5 py-1 hover:bg-slate-50">
                <span className={cn("mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full", LEVEL_DOT[log.level] || "bg-slate-400")} />
                <span className="gb-num text-[11px] text-slate-400">{log.time}</span>
                <span className={cn("gb-num text-[13px] leading-relaxed", LEVEL_TEXT[log.level] || "text-slate-600")}>
                  {log.text}
                </span>
              </div>
            ))}
          </div>
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
