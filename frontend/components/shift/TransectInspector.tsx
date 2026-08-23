"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Crosshair,
  TableProperties,
} from "lucide-react";
import { api, ChartData, TableRow as ApiTableRow } from "@/lib/api";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

let Plotly: any = null;

// Color a signed rate string: accretion (>0) green, erosion (<0) red, else neutral.
function rateClass(v: string) {
  const n = parseFloat(v);
  if (isNaN(n)) return "text-slate-400";
  if (n > 0.05) return "text-emerald-600";
  if (n < -0.05) return "text-rose-600";
  return "text-slate-800";
}

function Metric({
  label,
  value,
  unit,
  tone = "neutral",
  wide = false,
}: {
  label: string;
  value: string;
  unit: string;
  tone?: "neutral" | "rate" | "accent";
  wide?: boolean;
}) {
  const valueClass =
    tone === "rate" ? rateClass(value) : tone === "accent" ? "text-primary" : "text-slate-900";
  return (
    <div className={cn("px-3 py-2.5", wide && "col-span-2")}>
      <div className="gb-metric-label">{label}</div>
      <div className={cn("gb-metric-value", valueClass)}>
        {value}
        <span className="ml-1 text-[11px] font-normal text-slate-400">{unit}</span>
      </div>
    </div>
  );
}

export function TransectInspector() {
  const store = useStore();
  const {
    sessionId,
    selectedTransect,
    setSelectedTransect,
    params,
    transects,
    setActiveBottomTab,
    setBottomDockOpen,
    choropleth,
  } = store;

  const plotRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<ChartData | null>(null);
  const [ready, setReady] = useState(false);
  const [activeRow, setActiveRow] = useState<ApiTableRow | null>(null);

  useEffect(() => {
    import("plotly.js-dist-min").then((m) => {
      Plotly = m.default ?? m;
      setReady(true);
    });
  }, []);

  useEffect(() => {
    if (selectedTransect != null && sessionId && params?.has_results) {
      api.chart(sessionId, selectedTransect).then(setData).catch(() => setData(null));
      api
        .table(sessionId)
        .then((res) => setActiveRow(res.rows.find((r) => r.id === selectedTransect) || null))
        .catch(() => setActiveRow(null));
    } else {
      setData(null);
      setActiveRow(null);
    }
  }, [selectedTransect, sessionId, params?.has_results]);

  const nTotal = transects?.features?.length || 0;

  const onPrev = () =>
    setSelectedTransect(selectedTransect === null ? 0 : Math.max(0, selectedTransect - 1));
  const onNext = () =>
    setSelectedTransect(
      selectedTransect === null ? 0 : Math.min(nTotal - 1, selectedTransect + 1)
    );

  const zoomToTransect = () => {
    if (selectedTransect === null || !(window as any).__shiftMap) return;
    const feats = choropleth?.geojson?.features || transects?.features || [];
    const feat = feats.find(
      (f: any) =>
        f.properties?.transect_id === selectedTransect || f.properties?.id === selectedTransect
    );
    const coords = feat?.geometry?.coordinates;
    if (coords && coords.length >= 2) {
      const p1 = coords[0];
      const p2 = coords[coords.length - 1];
      (window as any).__shiftMap.fitBounds(
        [
          [p1[1], p1[0]],
          [p2[1], p2[0]],
        ],
        { padding: [50, 50], maxZoom: 14 }
      );
    }
  };

  const viewInTable = () => {
    setBottomDockOpen(true);
    setActiveBottomTab("table");
  };

  useEffect(() => {
    if (!ready || !plotRef.current) return;

    const baseLayout = {
      paper_bgcolor: "transparent",
      plot_bgcolor: "#ffffff",
      font: { family: "Plus Jakarta Sans, sans-serif", color: "#475569", size: 10 },
    };

    if (!data) {
      Plotly.react(
        plotRef.current,
        [],
        {
          ...baseLayout,
          margin: { l: 50, r: 15, t: 15, b: 35 },
          annotations: [
            {
              text: "Select a transect on the map or table to view its<br>time-series profile and detected regime shifts.",
              x: 0.5,
              y: 0.5,
              xref: "paper",
              yref: "paper",
              showarrow: false,
              font: { color: "#94a3b8", size: 11 },
            },
          ],
        },
        { responsive: true, displaylogo: false }
      );
      return;
    }

    const traces: any[] = data.traces.map((t) => ({
      x: t.x,
      y: t.y,
      name: t.name,
      mode: t.kind === "markers+lines" ? "markers+lines" : "lines",
      marker: { size: 7, color: t.color },
      line: { color: t.color, width: t.kind === "markers+lines" ? 2.2 : 1.6, dash: t.dash ?? "solid" },
    }));

    if (data.forecast) {
      const f = data.forecast;
      traces.push({ x: f.years, y: f.distances, mode: "lines", name: `Forecast (${f.model})`, line: { color: "#9333ea", width: 2.2, dash: "dot" } });
      traces.push({
        x: [...f.years, ...[...f.years].reverse()],
        y: [...f.upper, ...[...f.lower].reverse()],
        fill: "toself",
        fillcolor: "rgba(147, 51, 234, 0.15)",
        line: { color: "rgba(0,0,0,0)" },
        name: `${f.ci_pct}% CI Band`,
      });
    }

    const shapes = data.breaks.map((b) => ({
      type: "line", x0: b.year, x1: b.year, yref: "paper", y0: 0, y1: 1,
      line: { color: "#e11d48", width: 1.25, dash: "dot" },
    }));
    const annotations = data.breaks.map((b) => ({
      x: b.year, yref: "paper", y: 1, showarrow: false,
      text: `<b>${Math.round(b.year)}</b>`,
      font: { size: 9, color: "#e11d48", family: "JetBrains Mono, monospace" },
      xanchor: "left", yanchor: "top",
    }));

    Plotly.react(
      plotRef.current,
      traces,
      {
        ...baseLayout,
        margin: { l: 52, r: 15, t: 15, b: 38 },
        xaxis: { title: "Survey year", gridcolor: "#f1f5f9", zerolinecolor: "#e2e8f0", tickfont: { size: 9, family: "JetBrains Mono, monospace" } },
        yaxis: { title: "Shoreline dist. (m)", gridcolor: "#f1f5f9", zerolinecolor: "#e2e8f0", tickfont: { size: 9, family: "JetBrains Mono, monospace" } },
        legend: { orientation: "h", y: 1.16, x: 0, font: { size: 9 } },
        shapes,
        annotations,
      },
      { responsive: true, displaylogo: false }
    );
  }, [ready, data]);

  return (
    <aside className="gb-panel border-l border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="gb-section-title">Inspector</span>
          {selectedTransect !== null && (
            <span className="gb-num rounded-md bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary">
              #{selectedTransect}
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-500"
            onClick={onPrev} disabled={selectedTransect === null || selectedTransect <= 0} title="Previous">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-500"
            onClick={onNext} disabled={selectedTransect === null || selectedTransect >= nTotal - 1} title="Next">
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" className="h-8 w-8 text-slate-500"
            onClick={zoomToTransect} disabled={selectedTransect === null} title="Zoom to transect">
            <Crosshair className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Chart */}
      <div className="h-[260px] flex-shrink-0 border-y border-slate-100 p-2">
        <div ref={plotRef} className="h-full w-full" />
      </div>

      {/* Metrics */}
      <div className="shift-scroll flex-1 overflow-y-auto p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="gb-section-title">Fitted rate metrics</span>
          <Button size="sm" variant="ghost" className="h-7 gap-1.5 px-2 text-[12px] text-slate-500"
            onClick={viewInTable}>
            <TableProperties className="h-3.5 w-3.5" /> Table
          </Button>
        </div>

        {activeRow ? (
          <div className="space-y-2">
          {/* Trend verdict from the LRR 95% confidence interval */}
          <div
            className={cn(
              "flex items-center justify-between rounded-xl border px-3 py-2 text-[12px]",
              activeRow.trend === "Erosion"
                ? "border-rose-200 bg-rose-50/60 text-rose-700"
                : activeRow.trend === "Accretion"
                ? "border-emerald-200 bg-emerald-50/60 text-emerald-700"
                : "border-slate-200 bg-slate-50/60 text-slate-500"
            )}
          >
            <span className="font-semibold">
              {activeRow.trend === "Stable"
                ? "Stable — not statistically significant"
                : activeRow.trend === "—"
                ? "Trend undetermined"
                : `Significant ${activeRow.trend.toLowerCase()}`}
            </span>
            <span className="gb-num text-[11px] text-slate-500">
              95% CI {activeRow.lrr_ci} m/yr
            </span>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="grid grid-cols-2 divide-x divide-y divide-slate-100">
              <Metric label="Linear rate (LRR)" value={activeRow.lrr} unit="m/yr" tone="rate" />
              <Metric label="Endpoint rate (EPR)" value={activeRow.epr} unit="m/yr" tone="rate" />
              <Metric label="Theil-Sen robust" value={activeRow.tsr} unit="m/yr" tone="rate" />
              <Metric label="RANSAC robust" value={activeRow.ransac} unit="m/yr" tone="rate" />
              <div className="col-span-2 border-t border-slate-100 bg-slate-50/60 px-3 py-2.5">
                <div className="flex items-center justify-between">
                  <span className="gb-metric-label">Breakpoint post-break rate</span>
                  <span className="gb-num rounded bg-white px-1.5 py-0.5 text-[10px] text-slate-500 ring-1 ring-slate-200">
                    {activeRow.n_brk} regimes
                  </span>
                </div>
                <div className="mt-0.5 flex items-baseline justify-between">
                  <span className={cn("gb-metric-value", rateClass(activeRow.bp_rate))}>
                    {activeRow.bp_rate}
                    <span className="ml-1 text-[11px] font-normal text-slate-400">m/yr</span>
                  </span>
                  <span className="text-[12px] text-slate-500">Inflection {activeRow.bp_year || "—"}</span>
                </div>
              </div>
            </div>
          </div>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-8 text-center text-[13px] text-slate-400">
            {selectedTransect === null
              ? "Select a transect on the map to inspect its rates."
              : "No rates calculated for this transect yet."}
          </div>
        )}
      </div>
    </aside>
  );
}
