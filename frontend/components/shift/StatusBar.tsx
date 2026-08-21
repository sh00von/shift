"use client";

import {
  PanelLeft,
  PanelRight,
  PanelBottom,
  Loader2,
  MapPin,
} from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function StatusBar() {
  const {
    cursorCoords,
    mapZoom,
    status,
    progress,
    running,
    activeJobName,
    logs,
    tocOpen,
    setTocOpen,
    inspectorOpen,
    setInspectorOpen,
    bottomDockOpen,
    setBottomDockOpen,
    setActiveBottomTab,
  } = useStore();

  const pct = Math.min(100, Math.max(0, Math.round(progress * 100)));

  const toggle = (
    active: boolean,
    onClick: () => void,
    Icon: any,
    label: string
  ) => (
    <button
      onClick={onClick}
      title={label}
      className={cn(
        "flex h-6 w-6 items-center justify-center rounded-md transition-colors",
        active ? "bg-primary/10 text-primary" : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"
      )}
    >
      <Icon className="h-3.5 w-3.5" />
    </button>
  );

  return (
    <footer className="flex h-8 flex-shrink-0 items-center justify-between border-t border-slate-200 bg-white px-3 text-[12px] text-slate-500 select-none">
      {/* Left: coordinates + zoom */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 text-slate-400" />
          {cursorCoords ? (
            <span className="gb-num text-slate-600">
              {cursorCoords.lat >= 0 ? `${cursorCoords.lat.toFixed(4)}°N` : `${Math.abs(cursorCoords.lat).toFixed(4)}°S`},{" "}
              {cursorCoords.lng >= 0 ? `${cursorCoords.lng.toFixed(4)}°E` : `${Math.abs(cursorCoords.lng).toFixed(4)}°W`}
            </span>
          ) : (
            <span className="text-slate-400">—</span>
          )}
        </div>
        <span className="hidden gb-num text-slate-400 sm:inline">z{mapZoom.toFixed(1)}</span>
      </div>

      {/* Center: status */}
      <div className="flex min-w-0 items-center gap-2">
        {running ? (
          <div className="flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span className="truncate text-slate-600">{activeJobName}: {status}</span>
            <span className="gb-num text-slate-400">{pct}%</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="truncate text-slate-500">{status}</span>
          </div>
        )}
      </div>

      {/* Right: CRS + panel toggles */}
      <div className="flex items-center gap-3">
        <span className="hidden gb-num text-slate-400 md:inline">EPSG:4326</span>
        <button
          onClick={() => { setBottomDockOpen(true); setActiveBottomTab("console"); }}
          className="gb-num text-slate-400 transition-colors hover:text-slate-700"
          title="Open console"
        >
          {logs.length} msgs
        </button>
        <div className="flex items-center gap-0.5 border-l border-slate-200 pl-2">
          {toggle(tocOpen, () => setTocOpen(!tocOpen), PanelLeft, "Toggle layers panel")}
          {toggle(bottomDockOpen, () => setBottomDockOpen(!bottomDockOpen), PanelBottom, "Toggle bottom dock")}
          {toggle(inspectorOpen, () => setInspectorOpen(!inspectorOpen), PanelRight, "Toggle inspector")}
        </div>
      </div>
    </footer>
  );
}
