"use client";

import { useState, useRef, useEffect, ReactNode } from "react";
import {
  Eye,
  EyeOff,
  ChevronRight,
  ChevronDown,
  TableProperties,
  Trash2,
  SlidersHorizontal,
  GripVertical,
  Crosshair,
  ArrowUpToLine,
  ArrowDownToLine,
  RotateCcw,
  Check,
  Minus,
  Map as MapIcon,
  Layers,
  Activity,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import { toast } from "sonner";
import {
  useStore,
  LayerVisibility,
  LayerOpacity,
  LayerGroupId,
  LAYER_GROUPS,
} from "@/lib/store";
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

const GROUP_ICONS: Record<LayerGroupId, ReactNode> = {
  comparison:      <BarChart3 className="h-3 w-3" />,
  transects_rates: <Activity className="h-3 w-3" />,
  inputs:          <Layers className="h-3 w-3" />,
  aln2d:           <TrendingUp className="h-3 w-3" />,
  diagnostics:     <BarChart3 className="h-3 w-3" />,
};

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

function Swatch({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-5 w-6 flex-shrink-0 items-center justify-center">
      {children}
    </span>
  );
}

function VisCheck({ state, onClick }: { state: "on" | "off" | "mixed"; onClick: (e: React.MouseEvent) => void }) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(e); }}
      title="Toggle visibility"
      className={cn(
        "flex h-[15px] w-[15px] flex-shrink-0 items-center justify-center rounded-[3px] border transition-all",
        state === "on"
          ? "border-slate-700 bg-slate-700 text-white"
          : state === "mixed"
          ? "border-slate-400 bg-slate-200 text-slate-600"
          : "border-slate-300 bg-white text-transparent hover:border-slate-400"
      )}
    >
      {state === "mixed" ? <Minus className="h-2 w-2" /> : <Check className="h-2 w-2" />}
    </button>
  );
}

function GradientBar({ gradient, min, max, unit = "", midLabel }: {
  gradient: string; min: number; max: number; unit?: string; midLabel?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="h-2 w-full rounded border border-slate-200" style={{ background: gradient }} />
      <div className="flex justify-between font-mono text-[10px] text-slate-500">
        <span>{min.toFixed(1)}{unit}</span>
        {midLabel && <span>{midLabel}</span>}
        <span>+{max.toFixed(1)}{unit}</span>
      </div>
    </div>
  );
}

export function LayersTOC() {
  const store = useStore();
  const {
    params, shorelines, baseline, transects, choropleth, forecast,
    visibility, opacity, setVisibility, setAllVisibility, setLayerOpacity,
    setActiveBottomTab, setBottomDockOpen, basemap, setBasemap,
    groupOrder, layerOrderByGroup, collapsedGroups,
    toggleGroupCollapse, reorderLayerInGroup, reorderGroups,
    moveLayerToEdge, resetLayerOrder,
  } = store;

  const [expanded, setExpanded] = useState<string | null>("rates");
  const dragRef = useRef<{ type: "group" | "layer"; group?: LayerGroupId; id: string } | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [menu, setMenu] = useState<{ x: number; y: number; id: string; group: LayerGroupId } | null>(null);

  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => { window.removeEventListener("click", close); window.removeEventListener("scroll", close, true); };
  }, [menu]);

  const nSl = shorelines?.features?.length ?? 0;
  const nBl = baseline?.features?.length ?? 0;
  const nTr = transects?.features?.length ?? 0;

  const layerFC = (id: string): any => {
    switch (id) {
      case "shorelines":    return shorelines;
      case "baseline":      return baseline;
      case "transects":     return transects;
      case "rates":         return choropleth?.geojson ?? null;
      case "forecast":      return forecast?.line ?? null;
      case "aln2d_change":  return store.aln2dChange?.geojson ?? null;
      case "aln2d_reaches": return store.aln2dReaches?.geojson ?? null;
      case "cbc":           return store.cbcLayer?.geojson ?? null;
      default:              return null;
    }
  };

  const zoomToLayer = (id: string) => {
    const fc = layerFC(id);
    const map = (window as any).__shiftMap;
    if (!fc?.features?.length || !map) { toast.warning("Nothing to zoom to."); return; }
    let minLng = Infinity, minLat = Infinity, maxLng = -Infinity, maxLat = -Infinity;
    const scan = (c: any) => {
      if (typeof c[0] === "number") {
        minLng = Math.min(minLng, c[0]); maxLng = Math.max(maxLng, c[0]);
        minLat = Math.min(minLat, c[1]); maxLat = Math.max(maxLat, c[1]);
      } else c.forEach(scan);
    };
    fc.features.forEach((f: any) => f.geometry?.coordinates && scan(f.geometry.coordinates));
    if (minLng === Infinity) return;
    map.fitBounds([[minLat, minLng], [maxLat, maxLng]], { padding: [30, 30] });
  };

  const openLayerTable = (id: string) => {
    setBottomDockOpen(true);
    if (id === "aln2d_change" || id === "aln2d_reaches") setActiveBottomTab("aln2d");
    else setActiveBottomTab("table");
  };

  const onGroupDrop = (target: LayerGroupId) => {
    const d = dragRef.current;
    if (d?.type === "group") reorderGroups(d.id as LayerGroupId, target);
    dragRef.current = null; setDragOverId(null);
  };
  const onLayerDrop = (group: LayerGroupId, targetId: string) => {
    const d = dragRef.current;
    if (d?.type === "layer" && d.group === group) reorderLayerInGroup(group, d.id, targetId);
    dragRef.current = null; setDragOverId(null);
  };

  const onRestyle = (key: "color_ramp" | "style_metric") => async (v: string | null) => {
    if (!v) return;
    await store.setParam(key, v);
    await store.refreshResultsLayers();
  };
  const onPaletteChange = async (v: string | null) => {
    if (!v) return;
    await store.setParam("shoreline_palette", v);
    await store.refreshShorelines();
  };
  const onForecastModelChange = async (v: string | null) => {
    if (!v) return;
    await store.setParam("forecast_model", v);
    await store.refreshResultsLayers();
  };

  const removeLayer = (l: LayerDef) => {
    const patch: Record<string, null> = {};
    if (l.id === "shorelines")     patch.shorelines = null;
    else if (l.id === "baseline")  patch.baseline = null;
    else if (l.id === "transects") patch.transects = null;
    else if (l.id === "rates")     patch.choropleth = null;
    else if (l.id === "forecast")  patch.forecast = null;
    else if (l.id === "aln2d_change")  patch.aln2dChange = null;
    else if (l.id === "aln2d_reaches") patch.aln2dReaches = null;
    else if (l.id === "cbc")           patch.cbcLayer = null;
    useStore.setState(patch as any);
    toast.info(`Removed "${l.name}" from the map`);
  };

  const slDated = (shorelines?.features ?? [])
    .map((f: any) => ({ d: String(f.properties?.date_str ?? ""), c: f.properties?.color as string }))
    .filter((x) => x.c && x.d)
    .sort((a, b) => a.d.localeCompare(b.d));
  const slGradient =
    slDated.length >= 2
      ? `linear-gradient(to right, ${slDated.map((x) => x.c).join(", ")})`
      : slDated.length === 1 ? slDated[0].c : null;

  const computedMetrics: string[] = [];
  if (params?.run_classic) computedMetrics.push("LRR (m/yr)", "Sen's Slope (m/yr)", "EPR (m/yr)", "WLR (m/yr)", "NSM (m)", "SCE (m)");
  if (params?.run_ekf)     computedMetrics.push("EKF (m/yr)");
  const activeMetrics = computedMetrics.length > 0 ? computedMetrics : ["LRR (m/yr)", "Sen's Slope (m/yr)", "EPR (m/yr)", "WLR (m/yr)", "EKF (m/yr)"];

  const forecastModels: string[] = params?.forecast_models ?? [];
  const currentForecastModel = params?.forecast_model ?? forecastModels[0] ?? "LRR";

  const layers: LayerDef[] = [
    {
      id: "shorelines",
      name: "Shoreline surveys",
      swatch: <Swatch><span className="block h-1 w-5 rounded-full bg-gradient-to-r from-sky-500 via-emerald-500 to-amber-500" /></Swatch>,
      visKeys: ["shorelines"],
      opacityKey: "shorelines",
      count: nSl,
      meta: params?.shoreline_filename ?? "Date-coded surveys",
      available: nSl > 0,
      legend: (
        <div className="space-y-3">
          {slGradient && (
            <div className="space-y-1.5">
              <span className="gb-metric-label">Survey date</span>
              <div className="h-2 w-full rounded border border-slate-200" style={{ background: slGradient }} />
              <div className="flex justify-between font-mono text-[10px] text-slate-500">
                <span>{slDated[0]?.d}</span><span>{slDated[slDated.length - 1]?.d}</span>
              </div>
            </div>
          )}
          <div className="space-y-1">
            <Label className="gb-metric-label">Date palette</Label>
            <Select value={params?.shoreline_palette ?? "turbo"} onValueChange={onPaletteChange}>
              <SelectTrigger className="h-7 w-full text-[11px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                {SHORELINE_PALETTES.map(([label, val]) => <SelectItem key={val} value={val}>{label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <button
            onClick={() => store.setFieldMappingOpen(true)}
            className="flex w-full items-center gap-1.5 rounded border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-[11px] text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
          >
            <SlidersHorizontal className="h-3 w-3" /> Edit Date &amp; Uncertainty Fields…
          </button>
        </div>
      ),
    },
    {
      id: "baseline",
      name: "Baseline reference",
      swatch: <Swatch><span className="block h-0 w-5 border-t-2 border-dashed border-orange-500" /></Swatch>,
      visKeys: ["baseline"],
      opacityKey: "baseline",
      count: nBl,
      meta: params?.baseline_filename ?? "Offshore reference",
      available: nBl > 0,
    },
    {
      id: "transects",
      name: "Orthogonal transects",
      swatch: <Swatch><span className="block h-0.5 w-5 rounded-full bg-sky-500" /></Swatch>,
      visKeys: ["transects"],
      opacityKey: "transects",
      count: nTr,
      meta: params ? `${params.spacing} m spacing · ${params.transect_length} m reach` : undefined,
      available: nTr > 0,
    },
    {
      id: "rates",
      name: "Rate choropleth",
      swatch: (
        <Swatch>
          <span className="block h-3 w-5 rounded border border-slate-200"
            style={{ background: choropleth?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }} />
        </Swatch>
      ),
      visKeys: ["rates"],
      opacityKey: "rates",
      available: Boolean(choropleth?.legend),
      legend: choropleth?.legend ? (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <span className="gb-metric-label">{choropleth.legend.title}</span>
            <GradientBar gradient={choropleth.legend.gradient} min={choropleth.legend.min} max={choropleth.legend.max} unit=" m/yr" midLabel="0.0" />
          </div>
          <div className="space-y-1">
            <Label className="gb-metric-label">Style metric</Label>
            <Select
              value={params?.style_metric && activeMetrics.includes(params.style_metric) ? params.style_metric : activeMetrics[0]}
              onValueChange={onRestyle("style_metric")}
            >
              <SelectTrigger className="h-7 w-full text-[11px]"><SelectValue /></SelectTrigger>
              <SelectContent>{activeMetrics.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="gb-metric-label">Color ramp</Label>
            <Select value={params?.color_ramp ?? RAMPS[0]} onValueChange={onRestyle("color_ramp")}>
              <SelectTrigger className="h-7 w-full text-[11px]"><SelectValue /></SelectTrigger>
              <SelectContent>{RAMPS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </div>
      ) : <p className="text-[11px] italic text-slate-400">Run analysis to compute rates</p>,
    },
    {
      id: "forecast",
      name: "Forecast projection",
      swatch: (
        <Swatch>
          <span className="relative flex h-4 w-5 items-center">
            <span className="absolute inset-0 rounded bg-violet-100" />
            <span className="absolute left-0 right-0 h-0 border-t-2 border-dashed border-violet-500" />
          </span>
        </Swatch>
      ),
      visKeys: ["forecastLine", "forecastRibbon"],
      opacityKey: "forecast",
      available: Boolean(forecast?.line),
      meta: forecast?.target_year
        ? `${currentForecastModel} · horizon ${forecast.target_year}`
        : params ? `${params.forecast_horizon} yr · ${currentForecastModel}` : undefined,
      legend: (
        <div className="space-y-3">
          {forecastModels.length > 0 && (
            <div className="space-y-1.5">
              <Label className="gb-metric-label">Model</Label>
              <div className="flex flex-col gap-1">
                {forecastModels.map((m) => (
                  <button
                    key={m}
                    onClick={() => onForecastModelChange(m)}
                    className={cn(
                      "flex items-center gap-2 rounded border px-2.5 py-1.5 text-[12px] transition-all text-left",
                      m === currentForecastModel
                        ? "border-violet-300 bg-violet-50 text-violet-800 font-medium"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    )}
                  >
                    <span className={cn("h-2 w-2 flex-shrink-0 rounded-full", m === currentForecastModel ? "bg-violet-500" : "bg-slate-300")} />
                    {m}
                    {m === currentForecastModel && <Check className="ml-auto h-3 w-3 text-violet-500" />}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-1.5">
            <Label className="gb-metric-label">Sub-layers</Label>
            <div className="space-y-1">
              {[
                { key: "forecastLine" as keyof LayerVisibility, label: "Projection line", swatch: <span className="block h-0 w-4 border-t-2 border-dashed border-violet-500" /> },
                { key: "forecastRibbon" as keyof LayerVisibility, label: "Uncertainty ribbon", swatch: <span className="block h-3 w-4 rounded bg-violet-200" /> },
              ].map(({ key, label, swatch }) => (
                <button
                  key={key}
                  onClick={() => setVisibility(key, !visibility[key])}
                  className={cn(
                    "flex w-full items-center gap-2 rounded border px-2 py-1.5 text-[12px] transition-all",
                    visibility[key] ? "border-slate-200 bg-slate-50 text-slate-700" : "border-slate-100 bg-white text-slate-400"
                  )}
                >
                  {visibility[key] ? <Eye className="h-3 w-3 text-slate-400" /> : <EyeOff className="h-3 w-3 text-slate-300" />}
                  <span className="flex items-center">{swatch}</span>
                  {label}
                </button>
              ))}
            </div>
          </div>
          {forecast?.target_year && (
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 font-mono text-[10px] text-violet-700">
                horizon {forecast.target_year}
              </span>
              {forecast.ci_pct && (
                <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 font-mono text-[10px] text-violet-700">
                  {forecast.ci_pct}% CI
                </span>
              )}
            </div>
          )}
        </div>
      ),
    },
    {
      id: "aln2d_change",
      name: "2D-ALN Change",
      swatch: (
        <Swatch>
          <span className="block h-3 w-5 rounded border border-slate-200"
            style={{ background: store.aln2dChange?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }} />
        </Swatch>
      ),
      visKeys: ["aln2dChange"],
      opacityKey: "aln2dChange",
      available: Boolean(store.aln2dChange?.geojson?.features?.length),
      count: store.aln2dChange?.geojson?.features?.length ?? 0,
      meta: store.aln2dChange?.legend ? `±${store.aln2dChange.legend.max.toFixed(2)} km²/yr` : "Erosion ↔ Accretion",
      legend: store.aln2dChange?.legend ? (
        <div className="space-y-1.5">
          <span className="gb-metric-label">{store.aln2dChange.legend.title}</span>
          <GradientBar gradient={store.aln2dChange.legend.gradient} min={store.aln2dChange.legend.min} max={store.aln2dChange.legend.max} unit=" km²/yr" midLabel="0.0" />
          <div className="flex justify-between text-[10px] text-slate-500"><span>◀ Erosion</span><span>Accretion ▶</span></div>
        </div>
      ) : undefined,
    },
    {
      id: "aln2d_reaches",
      name: "2D-ALN Reach Rates",
      swatch: (
        <Swatch>
          <span className="block h-3 w-5 rounded border border-slate-200"
            style={{ background: store.aln2dReaches?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }} />
        </Swatch>
      ),
      visKeys: ["aln2dReaches"],
      opacityKey: "aln2dReaches",
      available: Boolean(store.aln2dReaches?.geojson?.features?.length),
      count: store.aln2dReaches?.geojson?.features?.length ?? 0,
      meta: store.aln2dReaches?.legend
        ? `${store.aln2dReaches.legend.min.toFixed(1)} → +${store.aln2dReaches.legend.max.toFixed(1)} m/yr`
        : "Normalised reach rates",
      legend: store.aln2dReaches?.legend ? (
        <div className="space-y-1.5">
          <span className="gb-metric-label">Migration Rate</span>
          <GradientBar gradient={store.aln2dReaches.legend.gradient} min={store.aln2dReaches.legend.min} max={store.aln2dReaches.legend.max} unit=" m/yr" midLabel="0.0" />
        </div>
      ) : undefined,
    },
    {
      id: "cbc",
      name: "Coastal Behaviour (CBC)",
      swatch: (
        <Swatch>
          <span className="flex gap-0.5">
            {["#ef4444","#10b981","#8b5cf6","#f59e0b","#06b6d4","#94a3b8"].map((c) => (
              <span key={c} className="block h-3 w-1 rounded-sm" style={{ background: c }} />
            ))}
          </span>
        </Swatch>
      ),
      visKeys: ["cbc"],
      opacityKey: "cbc",
      available: Boolean(store.cbcLayer?.geojson?.features?.length),
      count: store.cbcLayer?.geojson?.features?.length ?? 0,
      meta: "Run CBC in Diagnostics tab",
      legend: store.cbcLayer?.legend ? (
        <div className="space-y-1.5">
          <span className="gb-metric-label">Behaviour Class</span>
          <div className="flex flex-col gap-1">
            {store.cbcLayer.legend.categories.map((cat) => (
              <div key={cat.label} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 flex-shrink-0 rounded-sm" style={{ background: cat.color }} />
                <span className="text-[11px] text-slate-700">{cat.label}</span>
                <span className="text-[10px] text-slate-400">{cat.count}</span>
              </div>
            ))}
          </div>
        </div>
      ) : undefined,
    },
  ];

  const byId = new Map(layers.map((l) => [l.id, l] as const));
  const groupLayerDefs = (g: LayerGroupId): LayerDef[] =>
    (layerOrderByGroup[g] ?? []).map((id) => byId.get(id)).filter(Boolean) as LayerDef[];

  const groupState = (defs: LayerDef[]): "on" | "off" | "mixed" => {
    const avail = defs.filter((d) => d.available);
    if (!avail.length) return "off";
    const on = avail.filter((d) => d.visKeys.every((k) => visibility[k])).length;
    return on === avail.length ? "on" : on === 0 ? "off" : "mixed";
  };
  const setGroupVis = (defs: LayerDef[], v: boolean) =>
    defs.forEach((d) => d.visKeys.forEach((k) => setVisibility(k, v)));

  const menuLayer = menu ? byId.get(menu.id) : undefined;

  return (
    <aside className="gb-panel flex h-full w-full flex-col overflow-hidden border-r border-slate-200 bg-white">
      {/* Header */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-slate-100 px-3 py-2">
        <div className="flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-slate-400" />
          <span className="gb-section-title">Layers</span>
        </div>
        <div className="flex items-center gap-0.5">
          {[
            { icon: <Eye className="h-3.5 w-3.5" />, title: "Show all", action: () => setAllVisibility(true) },
            { icon: <EyeOff className="h-3.5 w-3.5" />, title: "Hide all", action: () => setAllVisibility(false) },
            { icon: <RotateCcw className="h-3 w-3" />, title: "Reset layer order", action: resetLayerOrder },
          ].map(({ icon, title, action }) => (
            <button key={title} onClick={action} title={title}
              className="flex h-6 w-6 items-center justify-center rounded text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-700">
              {icon}
            </button>
          ))}
        </div>
      </div>

      {/* Layer tree */}
      <div className="shift-scroll flex-1 overflow-y-auto py-1">
        {groupOrder.map((gid) => {
          const gdef = LAYER_GROUPS.find((g) => g.id === gid)!;
          const defs = groupLayerDefs(gid);
          const collapsed = collapsedGroups.includes(gid);
          const gState = groupState(defs);
          const loaded = defs.filter((d) => d.available).length;

          return (
            <div key={gid} className="mb-0.5">
              {/* Group header */}
              <div
                draggable
                onDragStart={() => (dragRef.current = { type: "group", id: gid })}
                onDragOver={(e) => { if (dragRef.current?.type === "group") { e.preventDefault(); setDragOverId("g:" + gid); } }}
                onDragLeave={() => setDragOverId((p) => (p === "g:" + gid ? null : p))}
                onDrop={() => onGroupDrop(gid)}
                onClick={() => toggleGroupCollapse(gid)}
                className={cn(
                  "group/gh flex cursor-pointer items-center gap-1.5 rounded-md px-2 py-1.5 transition-colors hover:bg-slate-50",
                  dragOverId === "g:" + gid && "border-t-2 border-slate-400"
                )}
              >
                <GripVertical className="h-3 w-3 flex-shrink-0 cursor-grab text-slate-200 group-hover/gh:text-slate-400" />
                <VisCheck state={gState} onClick={(e) => { e.stopPropagation(); setGroupVis(defs, gState !== "on"); }} />
                <span className="text-slate-400">
                  {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                </span>
                <span className="text-slate-400">{GROUP_ICONS[gid]}</span>
                <span className="flex-1 truncate text-[10px] font-semibold uppercase tracking-widest text-slate-500">
                  {gdef.label}
                </span>
                {loaded > 0 && (
                  <span className="rounded-full bg-slate-100 px-1.5 py-0.5 font-mono text-[9px] text-slate-500">
                    {loaded}/{defs.length}
                  </span>
                )}
              </div>

              {/* Layer rows */}
              {!collapsed && defs.map((l) => {
                const isOn = l.visKeys.every((k) => visibility[k]);
                const isExpanded = expanded === l.id;
                const hasDetail = Boolean(l.legend) || Boolean(l.opacityKey);

                return (
                  <div key={l.id}>
                    <div
                      draggable
                      onDragStart={(e) => { dragRef.current = { type: "layer", group: gid, id: l.id }; e.stopPropagation(); }}
                      onDragOver={(e) => { if (dragRef.current?.type === "layer" && dragRef.current.group === gid) { e.preventDefault(); setDragOverId("l:" + l.id); } }}
                      onDragLeave={() => setDragOverId((p) => (p === "l:" + l.id ? null : p))}
                      onDrop={() => onLayerDrop(gid, l.id)}
                      onContextMenu={(e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, id: l.id, group: gid }); }}
                      className={cn(
                        "group/lr ml-5 flex cursor-default items-center gap-1.5 rounded-md px-2 py-1.5 transition-colors hover:bg-slate-50",
                        !l.available && "opacity-45",
                        isExpanded && "bg-slate-50",
                        dragOverId === "l:" + l.id && "border-t-2 border-slate-300"
                      )}
                    >
                      <GripVertical className="h-3 w-3 flex-shrink-0 cursor-grab text-slate-200 group-hover/lr:text-slate-400" />
                      <VisCheck state={isOn ? "on" : "off"} onClick={() => l.visKeys.forEach((k) => setVisibility(k, !isOn))} />
                      <button
                        onClick={() => hasDetail && setExpanded(isExpanded ? null : l.id)}
                        className={cn("text-slate-300 transition-transform hover:text-slate-500", isExpanded && "text-slate-500", !hasDetail && "invisible")}
                      >
                        <ChevronRight className={cn("h-3 w-3 transition-transform", isExpanded && "rotate-90")} />
                      </button>
                      {l.swatch}
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[12px] font-medium text-slate-800">{l.name}</div>
                        {l.meta && <div className="truncate font-mono text-[10px] text-slate-400">{l.meta}</div>}
                      </div>
                      {typeof l.count === "number" && l.count > 0 && (
                        <span className="font-mono text-[10px] text-slate-400">{l.count}</span>
                      )}
                      {l.available && (
                        <button
                          onClick={() => removeLayer(l)}
                          title="Remove layer"
                          className="flex h-5 w-5 items-center justify-center rounded text-slate-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover/lr:opacity-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>

                    {/* Expanded panel */}
                    {isExpanded && hasDetail && (
                      <div className="ml-5 space-y-3 border-l border-slate-100 px-3 pb-3 pt-2">
                        {l.legend}
                        {l.opacityKey && (
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <Label className="gb-metric-label">Opacity</Label>
                              <span className="font-mono text-[10px] text-slate-500">
                                {Math.round(opacity[l.opacityKey] * 100)}%
                              </span>
                            </div>
                            <Slider
                              min={0.1} max={1} step={0.05}
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
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 space-y-2 border-t border-slate-100 p-3">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5">
            <MapIcon className="h-3 w-3 text-slate-400" />
            <Label className="gb-metric-label">Basemap</Label>
          </div>
          <Select value={basemap} onValueChange={(v) => v && setBasemap(v)}>
            <SelectTrigger className="h-7 w-full text-[11px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              {BASEMAPS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <button
          onClick={() => { setBottomDockOpen(true); setActiveBottomTab("table"); }}
          className="flex w-full items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
        >
          <TableProperties className="h-3.5 w-3.5" /> Open attribute table
        </button>
      </div>

      {/* Context menu */}
      {menu && menuLayer && (
        <div
          className="fixed z-[9999] w-52 overflow-hidden rounded-md border border-slate-200 bg-white py-1 text-[12px] shadow-lg"
          style={{ top: menu.y, left: menu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          {[
            { icon: <Crosshair className="h-3.5 w-3.5 text-slate-400" />, label: "Zoom to layer", action: () => { zoomToLayer(menu.id); setMenu(null); } },
            { icon: <TableProperties className="h-3.5 w-3.5 text-slate-400" />, label: "Open attribute table", action: () => { openLayerTable(menu.id); setMenu(null); } },
          ].map(({ icon, label, action }) => (
            <button key={label} onClick={action} className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 transition-colors hover:bg-slate-50">
              {icon} {label}
            </button>
          ))}
          <div className="my-1 border-t border-slate-100" />
          {[
            { icon: <ArrowUpToLine className="h-3.5 w-3.5 text-slate-400" />, label: "Move to top", action: () => { moveLayerToEdge(menu.group, menu.id, "top"); setMenu(null); } },
            { icon: <ArrowDownToLine className="h-3.5 w-3.5 text-slate-400" />, label: "Move to bottom", action: () => { moveLayerToEdge(menu.group, menu.id, "bottom"); setMenu(null); } },
          ].map(({ icon, label, action }) => (
            <button key={label} onClick={action} className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 transition-colors hover:bg-slate-50">
              {icon} {label}
            </button>
          ))}
          <div className="my-1 border-t border-slate-100" />
          <button
            onClick={() => { removeLayer(menuLayer); setMenu(null); }}
            className="flex w-full items-center gap-2 px-3 py-1.5 text-red-600 transition-colors hover:bg-red-50"
          >
            <Trash2 className="h-3.5 w-3.5" /> Remove layer
          </button>
        </div>
      )}
    </aside>
  );
}
