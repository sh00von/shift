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
  Map,
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
  comparison:     <BarChart3 className="h-3 w-3" />,
  transects_rates:<Activity className="h-3 w-3" />,
  inputs:         <Layers className="h-3 w-3" />,
  aln2d:          <TrendingUp className="h-3 w-3" />,
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

// ── Tiny colour pill showing layer symbology ──────────────────────────────
function Swatch({ children }: { children: ReactNode }) {
  return (
    <span className="flex h-5 w-6 flex-shrink-0 items-center justify-center">
      {children}
    </span>
  );
}

// ── Three-state GIS-style visibility checkbox ─────────────────────────────
function VisCheck({
  state,
  onClick,
}: {
  state: "on" | "off" | "mixed";
  onClick: (e: React.MouseEvent) => void;
}) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(e); }}
      title="Toggle visibility"
      className={cn(
        "flex h-[18px] w-[18px] flex-shrink-0 items-center justify-center rounded-[3px] border transition-all duration-100",
        state === "on"
          ? "border-sky-500 bg-sky-500 text-white"
          : state === "mixed"
          ? "border-sky-400 bg-sky-400/20 text-sky-500"
          : "border-[#444] bg-transparent text-transparent hover:border-[#666]"
      )}
    >
      {state === "mixed" ? <Minus className="h-2.5 w-2.5" /> : <Check className="h-2.5 w-2.5" />}
    </button>
  );
}

// ── Compact legend gradient bar ───────────────────────────────────────────
function GradientBar({
  gradient,
  min,
  max,
  unit = "",
  midLabel,
}: {
  gradient: string;
  min: number;
  max: number;
  unit?: string;
  midLabel?: string;
}) {
  return (
    <div className="space-y-1">
      <div
        className="h-2 w-full rounded-sm border border-white/10"
        style={{ background: gradient }}
      />
      <div className="flex justify-between font-mono text-[10px] text-[#888]">
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
    groupOrder,
    layerOrderByGroup,
    collapsedGroups,
    toggleGroupCollapse,
    reorderLayerInGroup,
    reorderGroups,
    moveLayerToEdge,
    resetLayerOrder,
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
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [menu]);

  const nSl = shorelines?.features?.length ?? 0;
  const nBl = baseline?.features?.length ?? 0;
  const nTr = transects?.features?.length ?? 0;

  // ── zoom-to helper ────────────────────────────────────────────────────────
  const layerFC = (id: string): any => {
    switch (id) {
      case "shorelines":   return shorelines;
      case "baseline":     return baseline;
      case "transects":    return transects;
      case "rates":        return choropleth?.geojson ?? null;
      case "forecast":     return forecast?.line ?? null;
      case "aln2d_change": return store.aln2dChange?.geojson ?? null;
      case "aln2d_reaches":return store.aln2dReaches?.geojson ?? null;
      default:             return null;
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

  // ── drag handlers ─────────────────────────────────────────────────────────
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

  // ── symbology helpers ─────────────────────────────────────────────────────
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
    if (l.id === "shorelines")    patch.shorelines = null;
    else if (l.id === "baseline") patch.baseline = null;
    else if (l.id === "transects")patch.transects = null;
    else if (l.id === "rates")    patch.choropleth = null;
    else if (l.id === "forecast") patch.forecast = null;
    else if (l.id === "aln2d_change")  patch.aln2dChange = null;
    else if (l.id === "aln2d_reaches") patch.aln2dReaches = null;
    useStore.setState(patch as any);
    toast.info(`Removed "${l.name}" from the map`);
  };

  // ── shoreline date legend ─────────────────────────────────────────────────
  const slDated = (shorelines?.features ?? [])
    .map((f: any) => ({ d: String(f.properties?.date_str ?? ""), c: f.properties?.color as string }))
    .filter((x) => x.c && x.d)
    .sort((a, b) => a.d.localeCompare(b.d));
  const slGradient =
    slDated.length >= 2
      ? `linear-gradient(to right, ${slDated.map((x) => x.c).join(", ")})`
      : slDated.length === 1 ? slDated[0].c : null;

  // ── available style metrics ───────────────────────────────────────────────
  const computedMetrics: string[] = [];
  if (params?.run_classic) computedMetrics.push("LRR (m/yr)", "EPR (m/yr)", "WLR (m/yr)", "NSM (m)", "SCE (m)");
  if (params?.run_ekf)     computedMetrics.push("EKF (m/yr)");
  const activeMetrics = computedMetrics.length > 0 ? computedMetrics : ["LRR (m/yr)", "EPR (m/yr)", "WLR (m/yr)", "EKF (m/yr)"];

  // ── available forecast models from params ─────────────────────────────────
  const forecastModels: string[] = params?.forecast_models ?? [];
  const currentForecastModel = params?.forecast_model ?? forecastModels[0] ?? "LRR";

  // ── layer definitions ─────────────────────────────────────────────────────
  const layers: LayerDef[] = [
    {
      id: "shorelines",
      name: "Shoreline surveys",
      swatch: (
        <Swatch>
          <span className="block h-1 w-5 rounded-full bg-gradient-to-r from-sky-400 via-emerald-400 to-amber-400" />
        </Swatch>
      ),
      visKeys: ["shorelines"],
      opacityKey: "shorelines",
      count: nSl,
      meta: params?.shoreline_filename ?? "Date-coded surveys",
      available: nSl > 0,
      legend: (
        <div className="space-y-3">
          {slGradient && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Survey Date</span>
              <div className="h-2 w-full rounded-sm border border-white/10" style={{ background: slGradient }} />
              <div className="flex justify-between font-mono text-[10px] text-[#888]">
                <span>{slDated[0]?.d}</span>
                <span>{slDated[slDated.length - 1]?.d}</span>
              </div>
            </div>
          )}
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Date Palette</span>
            <Select value={params?.shoreline_palette ?? "turbo"} onValueChange={onPaletteChange}>
              <SelectTrigger className="toc-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {SHORELINE_PALETTES.map(([label, val]) => (
                  <SelectItem key={val} value={val}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <button
            onClick={() => store.setFieldMappingOpen(true)}
            className="flex w-full items-center gap-1.5 rounded-[4px] border border-[#333] bg-[#1e2128] px-2.5 py-1.5 text-[11px] text-[#aaa] transition-colors hover:border-[#444] hover:text-[#ccc]"
          >
            <SlidersHorizontal className="h-3 w-3" /> Edit Date &amp; Uncertainty Fields…
          </button>
        </div>
      ),
    },
    {
      id: "baseline",
      name: "Baseline reference",
      swatch: (
        <Swatch>
          <span className="block h-0 w-5 border-t-2 border-dashed border-orange-400" />
        </Swatch>
      ),
      visKeys: ["baseline"],
      opacityKey: "baseline",
      count: nBl,
      meta: params?.baseline_filename ?? "Offshore reference",
      available: nBl > 0,
    },
    {
      id: "transects",
      name: "Orthogonal transects",
      swatch: (
        <Swatch>
          <span className="block h-0.5 w-5 rounded-full bg-sky-400" />
        </Swatch>
      ),
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
          <span
            className="block h-3 w-5 rounded-sm border border-white/10"
            style={{ background: choropleth?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
          />
        </Swatch>
      ),
      visKeys: ["rates"],
      opacityKey: "rates",
      available: Boolean(choropleth?.legend),
      legend: choropleth?.legend ? (
        <div className="space-y-3">
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">
              {choropleth.legend.title}
            </span>
            <GradientBar
              gradient={choropleth.legend.gradient}
              min={choropleth.legend.min}
              max={choropleth.legend.max}
              unit=" m/yr"
              midLabel="0.0"
            />
          </div>
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Style metric</span>
            <Select
              value={params?.style_metric && activeMetrics.includes(params.style_metric) ? params.style_metric : activeMetrics[0]}
              onValueChange={onRestyle("style_metric")}
            >
              <SelectTrigger className="toc-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {activeMetrics.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Color ramp</span>
            <Select value={params?.color_ramp ?? RAMPS[0]} onValueChange={onRestyle("color_ramp")}>
              <SelectTrigger className="toc-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                {RAMPS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      ) : (
        <p className="text-[11px] italic text-[#666]">Run analysis to compute rates</p>
      ),
    },
    {
      id: "forecast",
      name: "Forecast projection",
      swatch: (
        <Swatch>
          <span className="relative flex h-4 w-5 items-center">
            {/* ribbon */}
            <span className="absolute inset-0 rounded-sm bg-violet-500/20" />
            {/* centre line */}
            <span className="absolute left-0 right-0 h-0 border-t-2 border-dashed border-violet-400" />
          </span>
        </Swatch>
      ),
      visKeys: ["forecastLine", "forecastRibbon"],
      opacityKey: "forecast",
      available: Boolean(forecast?.line),
      meta: forecast?.target_year
        ? `${currentForecastModel} · horizon ${forecast.target_year}`
        : params
        ? `${params.forecast_horizon} yr · ${currentForecastModel}`
        : undefined,
      legend: (
        <div className="space-y-3">
          {/* Model switcher */}
          {forecastModels.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Model</span>
              <div className="flex flex-col gap-1">
                {forecastModels.map((m) => (
                  <button
                    key={m}
                    onClick={() => onForecastModelChange(m)}
                    className={cn(
                      "flex items-center gap-2 rounded-[4px] border px-2.5 py-1.5 text-[12px] transition-all",
                      m === currentForecastModel
                        ? "border-violet-500/60 bg-violet-500/15 text-violet-300"
                        : "border-[#333] bg-transparent text-[#888] hover:border-[#444] hover:text-[#bbb]"
                    )}
                  >
                    <span className={cn(
                      "h-2 w-2 rounded-full flex-shrink-0",
                      m === currentForecastModel ? "bg-violet-400" : "bg-[#444]"
                    )} />
                    {m}
                    {m === currentForecastModel && (
                      <Check className="ml-auto h-3 w-3 text-violet-400" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sub-layer toggles */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Sub-layers</span>
            <div className="space-y-1">
              {[
                { key: "forecastLine" as keyof LayerVisibility, label: "Projection line", swatch: <span className="block h-0 w-4 border-t-2 border-dashed border-violet-400" /> },
                { key: "forecastRibbon" as keyof LayerVisibility, label: "Uncertainty ribbon", swatch: <span className="block h-3 w-4 rounded-sm bg-violet-400/30" /> },
              ].map(({ key, label, swatch }) => (
                <button
                  key={key}
                  onClick={() => setVisibility(key, !visibility[key])}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-[4px] border px-2 py-1.5 text-[12px] transition-all",
                    visibility[key]
                      ? "border-[#3a3d44] bg-[#2a2d34] text-[#ccc]"
                      : "border-[#2a2a2a] bg-transparent text-[#666]"
                  )}
                >
                  {visibility[key]
                    ? <Eye className="h-3 w-3 text-[#888]" />
                    : <EyeOff className="h-3 w-3 text-[#555]" />}
                  <span className="flex items-center">{swatch}</span>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Info pills */}
          {forecast?.target_year && (
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 font-mono text-[10px] text-violet-400">
                horizon {forecast.target_year}
              </span>
              {forecast.ci_pct && (
                <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 font-mono text-[10px] text-violet-400">
                  {forecast.ci_pct}% CI
                </span>
              )}
              {forecast.model && (
                <span className="rounded-full border border-[#333] bg-[#252830] px-2 py-0.5 font-mono text-[10px] text-[#888]">
                  {forecast.model}
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
          <span
            className="block h-3 w-5 rounded-sm border border-white/10"
            style={{ background: store.aln2dChange?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
          />
        </Swatch>
      ),
      visKeys: ["aln2dChange"],
      opacityKey: "aln2dChange",
      available: Boolean(store.aln2dChange?.geojson?.features?.length),
      count: store.aln2dChange?.geojson?.features?.length ?? 0,
      meta: store.aln2dChange?.legend
        ? `±${store.aln2dChange.legend.max.toFixed(2)} km²/yr`
        : "Erosion ↔ Accretion",
      legend: store.aln2dChange?.legend ? (
        <div className="space-y-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">
            {store.aln2dChange.legend.title}
          </span>
          <GradientBar
            gradient={store.aln2dChange.legend.gradient}
            min={store.aln2dChange.legend.min}
            max={store.aln2dChange.legend.max}
            unit=" km²/yr"
            midLabel="0.0"
          />
          <div className="flex justify-between text-[10px] text-[#666]">
            <span>◀ Erosion</span>
            <span>Accretion ▶</span>
          </div>
        </div>
      ) : undefined,
    },
    {
      id: "aln2d_reaches",
      name: "2D-ALN Reach Rates",
      swatch: (
        <Swatch>
          <span
            className="block h-3 w-5 rounded-sm border border-white/10"
            style={{ background: store.aln2dReaches?.legend?.gradient ?? "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
          />
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
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">
            Migration Rate
          </span>
          <GradientBar
            gradient={store.aln2dReaches.legend.gradient}
            min={store.aln2dReaches.legend.min}
            max={store.aln2dReaches.legend.max}
            unit=" m/yr"
            midLabel="0.0"
          />
        </div>
      ) : undefined,
    },
  ];

  // ── group helpers ─────────────────────────────────────────────────────────
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
    <aside
      className="flex h-full w-full flex-col overflow-hidden"
      style={{ background: "#16181e", borderRight: "1px solid #252830" }}
    >
      {/* ── Header ── */}
      <div
        className="flex flex-shrink-0 items-center justify-between px-3 py-2.5"
        style={{ borderBottom: "1px solid #252830" }}
      >
        <div className="flex items-center gap-2">
          <Layers className="h-3.5 w-3.5 text-[#666]" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#888]">Layers</span>
        </div>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => setAllVisibility(true)}
            title="Show all"
            className="flex h-6 w-6 items-center justify-center rounded text-[#555] transition-colors hover:bg-[#252830] hover:text-[#aaa]"
          >
            <Eye className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setAllVisibility(false)}
            title="Hide all"
            className="flex h-6 w-6 items-center justify-center rounded text-[#555] transition-colors hover:bg-[#252830] hover:text-[#aaa]"
          >
            <EyeOff className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={resetLayerOrder}
            title="Reset layer order"
            className="flex h-6 w-6 items-center justify-center rounded text-[#555] transition-colors hover:bg-[#252830] hover:text-[#aaa]"
          >
            <RotateCcw className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* ── Layer tree ── */}
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
                className={cn(
                  "group/gh flex cursor-pointer items-center gap-1.5 px-2 py-1.5 transition-colors hover:bg-[#1e2028]",
                  dragOverId === "g:" + gid && "border-t border-sky-500/50"
                )}
                onClick={() => toggleGroupCollapse(gid)}
              >
                <GripVertical className="h-3 w-3 flex-shrink-0 cursor-grab text-[#333] group-hover/gh:text-[#555]" />
                <VisCheck state={gState} onClick={(e) => { e.stopPropagation(); setGroupVis(defs, gState !== "on"); }} />
                <span className="text-[#555]">
                  {collapsed
                    ? <ChevronRight className="h-3.5 w-3.5" />
                    : <ChevronDown className="h-3.5 w-3.5" />}
                </span>
                <span className="text-[#555]">{GROUP_ICONS[gid]}</span>
                <span className="flex-1 truncate text-[10px] font-semibold uppercase tracking-[0.1em] text-[#777]">
                  {gdef.label}
                </span>
                {loaded > 0 && (
                  <span className="rounded-full bg-[#252830] px-1.5 py-0.5 font-mono text-[9px] text-[#666]">
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
                    {/* Layer row */}
                    <div
                      draggable
                      onDragStart={(e) => { dragRef.current = { type: "layer", group: gid, id: l.id }; e.stopPropagation(); }}
                      onDragOver={(e) => { if (dragRef.current?.type === "layer" && dragRef.current.group === gid) { e.preventDefault(); setDragOverId("l:" + l.id); } }}
                      onDragLeave={() => setDragOverId((p) => (p === "l:" + l.id ? null : p))}
                      onDrop={() => onLayerDrop(gid, l.id)}
                      onContextMenu={(e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, id: l.id, group: gid }); }}
                      className={cn(
                        "group/lr ml-5 flex cursor-default items-center gap-1.5 rounded-[4px] px-2 py-1.5 transition-colors hover:bg-[#1e2028]",
                        !l.available && "opacity-40",
                        isExpanded && "bg-[#1e2028]",
                        dragOverId === "l:" + l.id && "border-t border-sky-500/50"
                      )}
                    >
                      <GripVertical className="h-3 w-3 flex-shrink-0 cursor-grab text-[#2a2d34] group-hover/lr:text-[#444]" />
                      <VisCheck
                        state={isOn ? "on" : "off"}
                        onClick={() => l.visKeys.forEach((k) => setVisibility(k, !isOn))}
                      />

                      {/* Expand chevron */}
                      <button
                        onClick={() => hasDetail && setExpanded(isExpanded ? null : l.id)}
                        className={cn(
                          "text-[#444] transition-all hover:text-[#777]",
                          isExpanded && "text-[#777]",
                          !hasDetail && "invisible"
                        )}
                      >
                        <ChevronRight className={cn("h-3 w-3 transition-transform", isExpanded && "rotate-90")} />
                      </button>

                      {l.swatch}

                      {/* Name + meta */}
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[12px] font-medium text-[#c8cad0]">{l.name}</div>
                        {l.meta && (
                          <div className="truncate font-mono text-[10px] text-[#555]">{l.meta}</div>
                        )}
                      </div>

                      {/* Feature count */}
                      {typeof l.count === "number" && l.count > 0 && (
                        <span className="font-mono text-[10px] text-[#555]">{l.count}</span>
                      )}

                      {/* Remove button */}
                      {l.available && (
                        <button
                          onClick={() => removeLayer(l)}
                          title="Remove layer"
                          className="flex h-5 w-5 items-center justify-center rounded text-[#444] opacity-0 transition-all hover:bg-rose-500/15 hover:text-rose-400 group-hover/lr:opacity-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>

                    {/* Expanded panel */}
                    {isExpanded && hasDetail && (
                      <div
                        className="ml-5 space-y-3 px-3 pb-3 pt-2"
                        style={{ borderLeft: "1px solid #252830", marginLeft: "1.5rem" }}
                      >
                        {l.legend}
                        {l.opacityKey && (
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Opacity</span>
                              <span className="font-mono text-[10px] text-[#666]">
                                {Math.round(opacity[l.opacityKey] * 100)}%
                              </span>
                            </div>
                            <Slider
                              min={0.1} max={1} step={0.05}
                              value={[opacity[l.opacityKey]]}
                              onValueChange={(v) => setLayerOpacity(l.opacityKey!, Array.isArray(v) ? v[0] : v)}
                              className="[&_[data-slot=slider-track]]:bg-[#252830] [&_[data-slot=slider-range]]:bg-sky-500 [&_[data-slot=slider-thumb]]:border-sky-500 [&_[data-slot=slider-thumb]]:bg-[#16181e]"
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

      {/* ── Footer: Basemap + table shortcut ── */}
      <div
        className="flex-shrink-0 space-y-2 p-3"
        style={{ borderTop: "1px solid #252830" }}
      >
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Map className="h-3 w-3 text-[#555]" />
            <span className="text-[10px] font-semibold uppercase tracking-widest text-[#666]">Basemap</span>
          </div>
          <Select value={basemap} onValueChange={(v) => v && setBasemap(v)}>
            <SelectTrigger className="toc-select"><SelectValue /></SelectTrigger>
            <SelectContent>
              {BASEMAPS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <button
          onClick={() => { setBottomDockOpen(true); setActiveBottomTab("table"); }}
          className="flex w-full items-center gap-2 rounded-[4px] border border-[#252830] bg-[#1e2028] px-3 py-1.5 text-[12px] text-[#888] transition-colors hover:border-[#333] hover:text-[#bbb]"
        >
          <TableProperties className="h-3.5 w-3.5" /> Open attribute table
        </button>
      </div>

      {/* ── Context menu ── */}
      {menu && menuLayer && (
        <div
          className="fixed z-[9999] w-52 overflow-hidden rounded-[6px] border border-[#333] py-1 text-[12px] shadow-2xl"
          style={{ top: menu.y, left: menu.x, background: "#1a1d23" }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[#bbb] transition-colors hover:bg-[#252830] hover:text-white"
            onClick={() => { zoomToLayer(menu.id); setMenu(null); }}
          >
            <Crosshair className="h-3.5 w-3.5 text-[#666]" /> Zoom to layer
          </button>
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[#bbb] transition-colors hover:bg-[#252830] hover:text-white"
            onClick={() => { openLayerTable(menu.id); setMenu(null); }}
          >
            <TableProperties className="h-3.5 w-3.5 text-[#666]" /> Open attribute table
          </button>
          <div className="my-1 border-t border-[#252830]" />
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[#bbb] transition-colors hover:bg-[#252830] hover:text-white"
            onClick={() => { moveLayerToEdge(menu.group, menu.id, "top"); setMenu(null); }}
          >
            <ArrowUpToLine className="h-3.5 w-3.5 text-[#666]" /> Move to top
          </button>
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-[#bbb] transition-colors hover:bg-[#252830] hover:text-white"
            onClick={() => { moveLayerToEdge(menu.group, menu.id, "bottom"); setMenu(null); }}
          >
            <ArrowDownToLine className="h-3.5 w-3.5 text-[#666]" /> Move to bottom
          </button>
          <div className="my-1 border-t border-[#252830]" />
          <button
            className="flex w-full items-center gap-2 px-3 py-1.5 text-rose-400 transition-colors hover:bg-rose-500/10"
            onClick={() => { removeLayer(menuLayer); setMenu(null); }}
          >
            <Trash2 className="h-3.5 w-3.5" /> Remove layer
          </button>
        </div>
      )}

      {/* ── Scoped styles for select triggers inside the dark TOC ── */}
      <style>{`
        .toc-select {
          height: 28px;
          width: 100%;
          background: #1e2028;
          border: 1px solid #2e3038;
          border-radius: 4px;
          color: #aaa;
          font-size: 11px;
          padding: 0 8px;
          transition: border-color 0.1s;
        }
        .toc-select:hover { border-color: #3e4048; }
        .toc-select:focus { border-color: #5b8dee; outline: none; }
      `}</style>
    </aside>
  );
}
