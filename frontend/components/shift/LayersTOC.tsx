"use client";

import { useState, ReactNode } from "react";
import {
  Eye,
  EyeOff,
  ChevronRight,
  TableProperties,
  Trash2,
  SlidersHorizontal,
} from "lucide-react";
import { toast } from "sonner";
import { useStore, LayerVisibility, LayerOpacity } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

const RAMPS = ["Red-Yellow-Green (DSAS)", "Turbo (Rainbow)", "Viridis", "Coolwarm", "Magma"];
const STYLE_METRICS = [
  "LRR (m/yr)",
  "EPR (m/yr)",
  "Theil-Sen (m/yr)",
  "RANSAC (m/yr)",
  "Post-break rate (m/yr)",
  "Break year",
  "BIC gain",
];
const BASEMAPS = ["OpenStreetMap", "Esri World Imagery", "Carto Light"];
const SHORELINE_PALETTES: [string, string][] = [
  ["Turbo", "turbo"],
  ["Viridis", "viridis"],
  ["Plasma", "plasma"],
  ["Magma", "magma"],
  ["Cividis", "cividis"],
  ["Cool", "cool"],
  ["Spring", "spring"],
];

interface LayerDef {
  id: string;
  name: string;
  swatch: ReactNode;
  visKeys: (keyof LayerVisibility)[];
  opacityKey?: keyof LayerOpacity;
  count?: number;
  meta?: string;
  legend?: ReactNode;
  available: boolean;
}

export function LayersTOC() {
  const store = useStore();
  const {
    params,
    shorelines,
    baseline,
    transects,
    choropleth,
    forecast,
    visibility,
    opacity,
    setVisibility,
    setAllVisibility,
    setLayerOpacity,
    setActiveBottomTab,
    setBottomDockOpen,
    basemap,
    setBasemap,
  } = store;

  const [expanded, setExpanded] = useState<string | null>("rates");

  const nSl = shorelines?.features?.length || 0;
  const nBl = baseline?.features?.length || 0;
  const nTr = transects?.features?.length || 0;

  const openTable = () => {
    setBottomDockOpen(true);
    setActiveBottomTab("table");
  };

  // Change a symbology param and re-fetch the styled choropleth in real time.
  const onRestyle = (key: "color_ramp" | "style_metric") => async (v: string | null) => {
    if (!v) return;
    await store.setParam(key, v);
    await store.refreshResultsLayers();
  };

  // Change the shoreline date palette and re-fetch the shoreline layer live.
  const onPaletteChange = async (v: string | null) => {
    if (!v) return;
    await store.setParam("shoreline_palette", v);
    await store.refreshShorelines();
  };

  // Remove a layer from the map/TOC (clears its client-side data).
  const removeLayer = (l: LayerDef) => {
    const patch: Record<string, null> = {};
    if (l.id === "shorelines") patch.shorelines = null;
    else if (l.id === "baseline") patch.baseline = null;
    else if (l.id === "transects") patch.transects = null;
    else if (l.id === "rates") patch.choropleth = null;
    else if (l.id === "forecast") {
      patch.forecast = null;
    }
    useStore.setState(patch as any);
    toast.info(`Removed ${l.name} from the map`);
  };

  // Build a date→color legend for shorelines from the actual survey colors.
  const slDated = (shorelines?.features ?? [])
    .map((f: any) => ({ d: String(f.properties?.date_str ?? ""), c: f.properties?.color as string }))
    .filter((x) => x.c && x.d)
    .sort((a, b) => a.d.localeCompare(b.d));
  const slGradient =
    slDated.length >= 2
      ? `linear-gradient(to right, ${slDated.map((x) => x.c).join(", ")})`
      : slDated.length === 1
      ? slDated[0].c
      : null;

  const computedStyleMetrics: string[] = [];
  if (params?.run_classic) {
    computedStyleMetrics.push("LRR (m/yr)", "EPR (m/yr)", "WLR (m/yr)", "NSM (m)", "SCE (m)");
  }
  if (params?.run_theilsen) {
    computedStyleMetrics.push("Theil-Sen (m/yr)");
  }
  if (params?.run_ransac) {
    computedStyleMetrics.push("RANSAC (m/yr)");
  }
  if (params?.run_breakpoint) {
    computedStyleMetrics.push("Post-break rate (m/yr)", "Break year", "BIC gain");
  }
  if (params?.run_rf) {
    computedStyleMetrics.push("Random Forest (m/yr)");
  }
  const activeMetrics = computedStyleMetrics.length > 0 ? computedStyleMetrics : STYLE_METRICS;

  const layers: LayerDef[] = [
    {
      id: "shorelines",
      name: "Shoreline surveys",
      swatch: <span className="block h-1 w-5 rounded-full bg-gradient-to-r from-blue-600 via-emerald-500 to-amber-500" />,
      visKeys: ["shorelines"],
      opacityKey: "shorelines",
      count: nSl,
      meta: params?.shoreline_filename || "Date-coded surveys",
      available: nSl > 0,
      legend: (
        <div className="space-y-2.5">
          {slGradient && (
            <div className="space-y-1">
              <div className="text-[11px] font-medium text-slate-500">Survey date</div>
              <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: slGradient }} />
              <div className="flex justify-between gb-num text-[10px] text-slate-500">
                <span>{slDated[0]?.d}</span>
                <span>{slDated[slDated.length - 1]?.d}</span>
              </div>
            </div>
          )}
          <div className="space-y-1">
            <Label className="gb-metric-label">Date color palette</Label>
            <Select value={params?.shoreline_palette ?? "turbo"} onValueChange={onPaletteChange}>
              <SelectTrigger className="h-8 w-full text-[12px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {SHORELINE_PALETTES.map(([label, val]) => (
                  <SelectItem key={val} value={val}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="pt-1">
            <Button
              variant="outline"
              size="sm"
              className="h-7 w-full text-[11px] font-medium text-sky-700 bg-sky-50/60 border-sky-200 hover:bg-sky-100 hover:text-sky-800 gap-1.5"
              onClick={() => store.setFieldMappingOpen(true)}
            >
              <SlidersHorizontal className="h-3 w-3" /> Edit Date & Uncertainty Fields…
            </Button>
          </div>
        </div>
      ),
    },
    {
      id: "baseline",
      name: "Baseline reference",
      swatch: <span className="block h-0 w-5 border-t-2 border-dashed border-orange-500" />,
      visKeys: ["baseline"],
      opacityKey: "baseline",
      count: nBl,
      meta: params?.baseline_filename || "Offshore reference",
      available: nBl > 0,
    },
    {
      id: "transects",
      name: "Orthogonal transects",
      swatch: <span className="block h-0.5 w-5 rounded-full bg-sky-500" />,
      visKeys: ["transects"],
      opacityKey: "transects",
      count: nTr,
      meta: params ? `${params.spacing}m spacing · ${params.transect_length}m reach` : undefined,
      available: nTr > 0,
    },
    {
      id: "rates",
      name: "Rate choropleth",
      swatch: (
        <span
          className="block h-2.5 w-5 rounded-sm"
          style={{ background: choropleth?.legend?.gradient || "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
        />
      ),
      visKeys: ["rates"],
      opacityKey: "rates",
      available: Boolean(choropleth?.legend),
      legend: choropleth?.legend ? (
        <div className="space-y-2.5">
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-medium text-slate-500">
              <span>{choropleth.legend.title}</span>
              <span>m/yr</span>
            </div>
            <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: choropleth.legend.gradient }} />
            <div className="flex justify-between gb-num text-[10px] text-slate-500">
              <span>{choropleth.legend.min.toFixed(1)}</span>
              <span>0.0</span>
              <span>+{choropleth.legend.max.toFixed(1)}</span>
            </div>
          </div>
          <div className="space-y-1">
            <Label className="gb-metric-label">Style by metric</Label>
            <Select
              value={
                params?.style_metric && activeMetrics.includes(params.style_metric)
                  ? params.style_metric
                  : activeMetrics[0]
              }
              onValueChange={onRestyle("style_metric")}
            >
              <SelectTrigger className="h-8 w-full text-[12px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {activeMetrics.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="gb-metric-label">Color ramp</Label>
            <Select value={params?.color_ramp ?? RAMPS[0]} onValueChange={onRestyle("color_ramp")}>
              <SelectTrigger className="h-8 w-full text-[12px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {RAMPS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      ) : (
        <span className="text-[11px] italic text-slate-400">Run analysis to calculate rates</span>
      ),
    },
    {
      id: "forecast",
      name: "Forecast projection",
      swatch: <span className="block h-0 w-5 border-t-2 border-dashed border-purple-600" />,
      visKeys: ["forecastLine", "forecastRibbon"],
      opacityKey: "forecast",
      available: Boolean(forecast?.line),
      meta: forecast?.target_year
        ? `Horizon ${forecast.target_year} · ${forecast.model}`
        : params
        ? `${params.forecast_horizon}yr forward horizon`
        : undefined,
    },
  ];

  return (
    <aside className="gb-panel border-r border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <span className="gb-section-title">Layers</span>
        <div className="flex items-center gap-0.5">
          <Button size="icon" variant="ghost" className="h-7 w-7 text-slate-400"
            onClick={() => setAllVisibility(true)} title="Show all">
            <Eye className="h-4 w-4" />
          </Button>
          <Button size="icon" variant="ghost" className="h-7 w-7 text-slate-400"
            onClick={() => setAllVisibility(false)} title="Hide all">
            <EyeOff className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* List */}
      <div className="shift-scroll flex-1 overflow-y-auto px-2 pb-2">
        {layers.map((l) => {
          const isOn = l.visKeys.every((k) => visibility[k]);
          const isExpanded = expanded === l.id;
          const hasDetail = Boolean(l.legend) || Boolean(l.opacityKey);
          return (
            <div key={l.id} className="rounded-lg">
              <div
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-2 py-2 transition-colors hover:bg-slate-50",
                  !l.available && "opacity-55"
                )}
              >
                <button
                  onClick={() => hasDetail && setExpanded(isExpanded ? null : l.id)}
                  className={cn(
                    "text-slate-300 transition-transform hover:text-slate-500",
                    isExpanded && "rotate-90",
                    !hasDetail && "invisible"
                  )}
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>

                <span className="flex w-5 flex-shrink-0 items-center justify-center">{l.swatch}</span>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium text-slate-800">{l.name}</div>
                  {l.meta && <div className="truncate text-[11px] text-slate-400">{l.meta}</div>}
                </div>

                {typeof l.count === "number" && l.count > 0 && (
                  <span className="gb-num text-[11px] text-slate-400">{l.count}</span>
                )}

                <button
                  onClick={() => l.visKeys.forEach((k) => setVisibility(k, !isOn))}
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-md transition-colors",
                    isOn ? "text-primary hover:bg-primary/10" : "text-slate-300 hover:bg-slate-100"
                  )}
                  title={isOn ? "Hide layer" : "Show layer"}
                >
                  {isOn ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                </button>

                {l.available && (
                  <button
                    onClick={() => removeLayer(l)}
                    className="flex h-7 w-7 items-center justify-center rounded-md text-slate-300 opacity-0 transition-all hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"
                    title="Remove layer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {isExpanded && hasDetail && (
                <div className="space-y-3 pb-3 pl-9 pr-3 pt-1">
                  {l.legend}
                  {l.opacityKey && (
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-[11px] text-slate-400">
                        <span>Opacity</span>
                        <span className="gb-num">{Math.round(opacity[l.opacityKey] * 100)}%</span>
                      </div>
                      <Slider
                        min={0.1}
                        max={1}
                        step={0.05}
                        value={[opacity[l.opacityKey]]}
                        onValueChange={(v) => setLayerOpacity(l.opacityKey!, Array.isArray(v) ? v[0] : v)}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="space-y-2 border-t border-slate-100 p-3">
        <div className="space-y-1">
          <Label className="gb-metric-label">Basemap</Label>
          <Select value={basemap} onValueChange={(v) => v && setBasemap(v)}>
            <SelectTrigger className="h-8 w-full text-[12px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {BASEMAPS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" variant="ghost" className="h-9 w-full justify-start gap-2 text-[13px] text-slate-600"
          onClick={openTable}>
          <TableProperties className="h-4 w-4 text-slate-400" /> Open attribute table
        </Button>
      </div>
    </aside>
  );
}
