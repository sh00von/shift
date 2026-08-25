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
const STYLE_METRICS = [
  "LRR (m/yr)",
  "EPR (m/yr)",
  "WLR (m/yr)",
  "EKF (m/yr)",
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
  const {
    groupOrder,
    layerOrderByGroup,
    collapsedGroups,
    toggleGroupCollapse,
    reorderLayerInGroup,
    reorderGroups,
    moveLayerToEdge,
    resetLayerOrder,
  } = store;

  // Native HTML5 drag state
  const dragRef = useRef<{ type: "group" | "layer"; group?: LayerGroupId; id: string } | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

  // Right-click context menu
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

  const nSl = shorelines?.features?.length || 0;
  const nBl = baseline?.features?.length || 0;
  const nTr = transects?.features?.length || 0;

  const openTable = () => {
    setBottomDockOpen(true);
    setActiveBottomTab("table");
  };

  // Raw FeatureCollection behind a layer id (for zoom-to-layer extent).
  const layerFC = (id: string): any => {
    switch (id) {
      case "shorelines": return shorelines;
      case "baseline": return baseline;
      case "transects": return transects;
      case "rates": return choropleth?.geojson ?? null;
      case "forecast": return forecast?.line ?? null;
      case "best_method": return store.bestMethod?.geojson ?? null;
      case "aln2d_change": return store.aln2dChange?.geojson ?? null;
      case "aln2d_reaches": return store.aln2dReaches?.geojson ?? null;
      default: return null;
    }
  };

  const zoomToLayer = (id: string) => {
    const fc = layerFC(id);
    const map = (window as any).__shiftMap;
    if (!fc?.features?.length || !map) {
      toast.warning("Nothing to zoom to for this layer.");
      return;
    }
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

  // Open the bottom dock focused on the table best suited to a layer.
  const openLayerTable = (id: string) => {
    setBottomDockOpen(true);
    if (id === "aln2d_change" || id === "aln2d_reaches") setActiveBottomTab("aln2d");
    else if (id === "best_method") setActiveBottomTab("scorecard");
    else setActiveBottomTab("table");
  };

  // ── Native drag handlers ──
  const onGroupDrop = (target: LayerGroupId) => {
    const d = dragRef.current;
    if (d?.type === "group") reorderGroups(d.id as LayerGroupId, target);
    dragRef.current = null;
    setDragOverId(null);
  };
  const onLayerDrop = (group: LayerGroupId, targetId: string) => {
    const d = dragRef.current;
    if (d?.type === "layer" && d.group === group) reorderLayerInGroup(group, d.id, targetId);
    dragRef.current = null;
    setDragOverId(null);
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
    else if (l.id === "aln2d_change") patch.aln2dChange = null;
    else if (l.id === "aln2d_reaches") patch.aln2dReaches = null;
    else if (l.id === "best_method") patch.bestMethod = null;
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
  if (params?.run_ekf) {
    computedStyleMetrics.push("EKF (m/yr)");
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
              <div className="text-[11px] font-medium text-slate-700">Survey date</div>
              <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: slGradient }} />
              <div className="flex justify-between gb-num text-[10px] text-slate-600">
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
              className="h-7 w-full text-[11px] font-medium text-slate-700 bg-slate-50 border-slate-200 hover:bg-slate-100 hover:text-slate-900 gap-1.5"
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
            <div className="flex items-center justify-between text-[11px] font-medium text-slate-700">
              <span>{choropleth.legend.title}</span>
              <span>m/yr</span>
            </div>
            <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: choropleth.legend.gradient }} />
            <div className="flex justify-between gb-num text-[10px] text-slate-600">
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
        <span className="text-[11px] italic text-slate-500">Run analysis to calculate rates</span>
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
    {
      id: "aln2d_change",
      name: "2D-ALN Change (Mass)",
      swatch: (
        <span
          className="block h-2.5 w-5 rounded-sm"
          style={{ background: store.aln2dChange?.legend?.gradient || "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
        />
      ),
      visKeys: ["aln2dChange"],
      opacityKey: "aln2dChange",
      available: Boolean(store.aln2dChange?.geojson?.features?.length),
      count: store.aln2dChange?.geojson?.features?.length || 0,
      meta: store.aln2dChange?.legend
        ? `Erosion ↔ Accretion · ±${store.aln2dChange.legend.max.toFixed(2)} km²/yr`
        : "Erosion ↔ Accretion mass",
      legend: store.aln2dChange?.legend ? (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] font-medium text-slate-700">
            <span>{store.aln2dChange.legend.title}</span>
          </div>
          <div className="h-2.5 w-full rounded-sm border border-slate-200" style={{ background: store.aln2dChange.legend.gradient }} />
          <div className="flex justify-between gb-num text-[10px] text-slate-600">
            <span>Erosion {store.aln2dChange.legend.min.toFixed(2)}</span>
            <span>0.0</span>
            <span>+{store.aln2dChange.legend.max.toFixed(2)} Accretion</span>
          </div>
        </div>
      ) : undefined,
    },
    {
      id: "aln2d_reaches",
      name: "2D-ALN Reach Migration Rates",
      swatch: (
        <span
          className="block h-2.5 w-5 rounded-sm"
          style={{ background: store.aln2dReaches?.legend?.gradient || "linear-gradient(to right,#dc2626,#fef08a,#16a34a)" }}
        />
      ),
      visKeys: ["aln2dReaches"],
      opacityKey: "aln2dReaches",
      available: Boolean(store.aln2dReaches?.geojson?.features?.length),
      count: store.aln2dReaches?.geojson?.features?.length || 0,
      meta: store.aln2dReaches?.legend ? `${store.aln2dReaches.legend.min.toFixed(1)} to +${store.aln2dReaches.legend.max.toFixed(1)} m/yr` : "Normalized reach rates",
    },
    {
      id: "best_method",
      name: "Best Method (per transect)",
      swatch: <span className="block h-2.5 w-5 rounded-sm bg-gradient-to-r from-blue-600 via-emerald-500 to-orange-500" />,
      visKeys: ["bestMethod"],
      opacityKey: "bestMethod",
      available: Boolean(store.bestMethod?.geojson?.features?.length),
      count: store.bestMethod?.geojson?.features?.length || 0,
      meta: store.scorecard?.recommended ? `Recommended: ${store.scorecard.recommended}` : "Winning method per transect",
      legend: store.bestMethod?.legend?.categories?.length ? (
        <div className="space-y-1.5">
          <div className="text-[11px] font-medium text-slate-700">{store.bestMethod.legend.title}</div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-600">
            {store.bestMethod.legend.categories.map((c) => (
              <span key={c.label} className="inline-flex items-center gap-1">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: c.color }} />
                {c.label} <span className="gb-num">{c.count}</span>
              </span>
            ))}
          </div>
        </div>
      ) : undefined,
    },
  ];


  const byId = new Map(layers.map((l) => [l.id, l] as const));
  const groupLayerDefs = (g: LayerGroupId): LayerDef[] =>
    (layerOrderByGroup[g] || []).map((id) => byId.get(id)).filter(Boolean) as LayerDef[];

  const groupState = (defs: LayerDef[]): "on" | "off" | "mixed" => {
    const avail = defs.filter((d) => d.available);
    if (!avail.length) return "off";
    const on = avail.filter((d) => d.visKeys.every((k) => visibility[k])).length;
    return on === avail.length ? "on" : on === 0 ? "off" : "mixed";
  };
  const setGroupVis = (defs: LayerDef[], v: boolean) =>
    defs.forEach((d) => d.visKeys.forEach((k) => setVisibility(k, v)));

  const CheckBox = ({ state, onClick }: { state: "on" | "off" | "mixed"; onClick: (e: any) => void }) => (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(e); }}
      className={cn(
        "flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border transition-colors",
        state === "on" ? "border-primary bg-primary text-white"
          : state === "mixed" ? "border-primary bg-primary/20 text-primary"
          : "border-slate-300 bg-white text-transparent hover:border-slate-400"
      )}
      title="Toggle visibility"
    >
      {state === "mixed" ? <Minus className="h-3 w-3" /> : <Check className="h-3 w-3" />}
    </button>
  );

  const menuLayer = menu ? byId.get(menu.id) : undefined;

  return (
    <aside className="gb-panel relative border-r border-slate-200">
      {/* Header / toolbar */}
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
          <Button size="icon" variant="ghost" className="h-7 w-7 text-slate-400"
            onClick={resetLayerOrder} title="Reset layer order">
            <RotateCcw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Grouped, draggable layer tree */}
      <div className="shift-scroll flex-1 overflow-y-auto px-1.5 pb-2">
        {groupOrder.map((gid) => {
          const gdef = LAYER_GROUPS.find((g) => g.id === gid)!;
          const defs = groupLayerDefs(gid);
          const collapsed = collapsedGroups.includes(gid);
          const gState = groupState(defs);
          const loaded = defs.filter((d) => d.available).length;
          return (
            <div key={gid} className="mb-1">
              {/* Group header (draggable) */}
              <div
                draggable
                onDragStart={() => (dragRef.current = { type: "group", id: gid })}
                onDragOver={(e) => { if (dragRef.current?.type === "group") { e.preventDefault(); setDragOverId("g:" + gid); } }}
                onDragLeave={() => setDragOverId((p) => (p === "g:" + gid ? null : p))}
                onDrop={() => onGroupDrop(gid)}
                className={cn(
                  "group/gh flex items-center gap-1.5 rounded-md px-1.5 py-1.5 transition-colors hover:bg-slate-100/70",
                  dragOverId === "g:" + gid && "border-t-2 border-primary"
                )}
              >
                <GripVertical className="h-3.5 w-3.5 flex-shrink-0 cursor-grab text-slate-300 group-hover/gh:text-slate-400" />
                <CheckBox state={gState} onClick={() => setGroupVis(defs, gState !== "on")} />
                <button onClick={() => toggleGroupCollapse(gid)} className="text-slate-400 hover:text-slate-600">
                  {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
                <span className="flex-1 truncate text-[12px] font-semibold uppercase tracking-wide text-slate-600">{gdef.label}</span>
                <span className="gb-num text-[10px] text-slate-400">{loaded}/{defs.length}</span>
              </div>

              {/* Layers within the group */}
              {!collapsed && defs.map((l) => {
                const isOn = l.visKeys.every((k) => visibility[k]);
                const isExpanded = expanded === l.id;
                const hasDetail = Boolean(l.legend) || Boolean(l.opacityKey);
                return (
                  <div key={l.id} className="ml-3">
                    <div
                      draggable
                      onDragStart={(e) => { dragRef.current = { type: "layer", group: gid, id: l.id }; e.stopPropagation(); }}
                      onDragOver={(e) => { if (dragRef.current?.type === "layer" && dragRef.current.group === gid) { e.preventDefault(); setDragOverId("l:" + l.id); } }}
                      onDragLeave={() => setDragOverId((p) => (p === "l:" + l.id ? null : p))}
                      onDrop={() => onLayerDrop(gid, l.id)}
                      onContextMenu={(e) => { e.preventDefault(); setMenu({ x: e.clientX, y: e.clientY, id: l.id, group: gid }); }}
                      className={cn(
                        "group flex items-center gap-1.5 rounded-md px-1.5 py-1.5 transition-colors hover:bg-slate-50",
                        !l.available && "opacity-55",
                        dragOverId === "l:" + l.id && "border-t-2 border-primary"
                      )}
                    >
                      <GripVertical className="h-3.5 w-3.5 flex-shrink-0 cursor-grab text-slate-200 group-hover:text-slate-400" />
                      <CheckBox state={isOn ? "on" : "off"} onClick={() => l.visKeys.forEach((k) => setVisibility(k, !isOn))} />
                      <button
                        onClick={() => hasDetail && setExpanded(isExpanded ? null : l.id)}
                        className={cn("text-slate-300 transition-transform hover:text-slate-500", isExpanded && "rotate-90", !hasDetail && "invisible")}
                      >
                        <ChevronRight className="h-3.5 w-3.5" />
                      </button>
                      <span className="flex w-5 flex-shrink-0 items-center justify-center">{l.swatch}</span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[13px] font-medium text-slate-900">{l.name}</div>
                        {l.meta && <div className="truncate text-[11px] text-slate-600">{l.meta}</div>}
                      </div>
                      {typeof l.count === "number" && l.count > 0 && (
                        <span className="gb-num text-[11px] text-slate-600">{l.count}</span>
                      )}
                      {l.available && (
                        <button
                          onClick={() => removeLayer(l)}
                          className="flex h-6 w-6 items-center justify-center rounded-md text-slate-300 opacity-0 transition-all hover:bg-rose-50 hover:text-rose-600 group-hover:opacity-100"
                          title="Remove layer"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>

                    {isExpanded && hasDetail && (
                      <div className="space-y-3 pb-3 pl-11 pr-3 pt-1">
                        {l.legend}
                        {l.opacityKey && (
                          <div className="space-y-1.5">
                            <div className="flex justify-between text-[11px] text-slate-600">
                              <span>Opacity</span>
                              <span className="gb-num">{Math.round(opacity[l.opacityKey] * 100)}%</span>
                            </div>
                            <Slider min={0.1} max={1} step={0.05} value={[opacity[l.opacityKey]]}
                              onValueChange={(v) => setLayerOpacity(l.opacityKey!, Array.isArray(v) ? v[0] : v)} />
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

      {/* Right-click context menu */}
      {menu && menuLayer && (
        <div
          className="fixed z-[9999] w-52 rounded-md border border-slate-200 bg-white py-1 text-[13px] shadow-lg"
          style={{ top: menu.y, left: menu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
            onClick={() => { zoomToLayer(menu.id); setMenu(null); }}>
            <Crosshair className="h-3.5 w-3.5 text-slate-500" /> Zoom to layer
          </button>
          <button className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
            onClick={() => { openLayerTable(menu.id); setMenu(null); }}>
            <TableProperties className="h-3.5 w-3.5 text-slate-500" /> Open attribute table
          </button>
          <div className="my-1 border-t border-slate-100" />
          <button className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
            onClick={() => { moveLayerToEdge(menu.group, menu.id, "top"); setMenu(null); }}>
            <ArrowUpToLine className="h-3.5 w-3.5 text-slate-500" /> Move to top
          </button>
          <button className="flex w-full items-center gap-2 px-3 py-1.5 text-slate-700 hover:bg-slate-50"
            onClick={() => { moveLayerToEdge(menu.group, menu.id, "bottom"); setMenu(null); }}>
            <ArrowDownToLine className="h-3.5 w-3.5 text-slate-500" /> Move to bottom
          </button>
        </div>
      )}

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
        <Button size="sm" variant="ghost" className="h-9 w-full justify-start gap-2 text-[13px] text-slate-700"
          onClick={openTable}>
          <TableProperties className="h-4 w-4 text-slate-600" /> Open attribute table
        </Button>
      </div>
    </aside>
  );
}
