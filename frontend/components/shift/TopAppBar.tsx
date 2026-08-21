"use client";

import { useRef, useState, useEffect } from "react";
import {
  Waves,
  Play,
  Upload,
  Ruler,
  Sparkles,
  TrendingUp,
  Download,
  RotateCcw,
  HelpCircle,
  SlidersHorizontal,
  ChevronDown,
  Plus,
  FileSpreadsheet,
  MapPin,
  CheckCircle2,
  Loader2,
  Package,
  Layers,
} from "lucide-react";
import { toast } from "sonner";
import { useStore } from "@/lib/store";
import { api, runJob, Params } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { ProgressModal } from "./ProgressModal";
import { FieldMappingModal } from "./FieldMappingModal";

const FORECAST_MODELS: string[] = [
  "Breakpoint (Post-break Rate)",
  "Theil-Sen Robust Rate",
  "RANSAC Robust Rate",
  "Linear Regression (LRR)",
  "Classic Endpoint Rate (EPR)",
  "Random Forest Benchmark",
];
const MODELS: [keyof Params, string][] = [
  ["run_classic", "USGS DSAS (EPR / LRR / WLR)"],
  ["run_theilsen", "Theil-Sen Robust"],
  ["run_ransac", "RANSAC Robust"],
  ["run_breakpoint", "Breakpoint (Pelt)"],
  ["run_rf", "Random Forest"],
];

interface Props {
  onLoadDemo: () => void;
  onClear: () => void;
}

function NumField({
  label,
  pKey,
  min,
  step,
  transform,
}: {
  label: string;
  pKey: keyof Params;
  min?: number;
  step?: number;
  transform?: { get: (v: number) => number; set: (v: number) => number };
}) {
  const { params, setParam } = useStore();
  const raw = (params?.[pKey] as number) ?? 0;
  const shown = transform ? transform.get(raw) : raw;
  return (
    <div className="space-y-1">
      <Label className="gb-metric-label">{label}</Label>
      <Input
        type="number"
        min={min}
        step={step}
        value={shown}
        onChange={(e) => {
          const n = parseFloat(e.target.value);
          if (isNaN(n)) return;
          setParam(pKey, (transform ? transform.set(n) : n) as any);
        }}
        className="h-9 gb-num text-right text-sm"
      />
    </div>
  );
}

export function TopAppBar({ onLoadDemo, onClear }: Props) {
  const store = useStore();
  const { sessionId, params, running } = store;

  const slRef = useRef<HTMLInputElement>(null);
  const blRef = useRef<HTMLInputElement>(null);

  // Only the models actually computed during analysis are offered for forecasting.
  const [fcModels, setFcModels] = useState<string[]>([]);
  useEffect(() => {
    if (params?.has_results && sessionId) {
      api.forecastModels(sessionId).then((r) => setFcModels(r.models)).catch(() => setFcModels([]));
    } else {
      setFcModels([]);
    }
  }, [params?.has_results, sessionId]);

  const withRun = async (fn: () => Promise<void>, jobName: string) => {
    store.setRunning(true, jobName);
    try {
      await fn();
    } catch (e: any) {
      store.log(e.message || "Operation failed", "ERROR");
      toast.error(e.message || "Operation failed");
    } finally {
      store.setRunning(false);
    }
  };

  const onUploadShoreline = (file: File) =>
    withRun(async () => {
      if (!sessionId) return;
      const info = await api.uploadShoreline(sessionId, file);
      await store.reload();
      await store.refreshShorelines();
      store.log(`Shorelines loaded: ${info.filename} (${info.n_features} surveys)`, "SUCCESS");
      store.setStatus("Shorelines loaded. Configure field mapping or add baseline.", 0.2);
      toast.success(`Uploaded ${info.filename} (${info.n_features} surveys)`);
      store.setFieldMappingOpen(true);
    }, "Upload Shorelines");

  const onUploadBaseline = (file: File) =>
    withRun(async () => {
      if (!sessionId) return;
      const info = await api.uploadBaseline(sessionId, file);
      await store.reload();
      await store.refreshBaseline();
      store.log(`Baseline loaded: ${info.filename} (${info.n_features} features)`, "SUCCESS");
      store.setStatus("Baseline ready. Cast transects to continue.", 0.4);
      toast.success(`Uploaded baseline ${info.filename}`);
    }, "Upload Baseline");

  const onPreview = () =>
    withRun(async () => {
      if (!params?.has_shoreline || !params?.has_baseline) {
        toast.warning("Load both shorelines and baseline first.");
        return;
      }
      await runJob(sessionId!, "preview", (f) => {
        if (f.type === "progress") {
          store.setStatus(f.message || "", f.progress);
          if (f.message) store.log(f.message);
        }
      });
      await store.refreshTransects();
      store.setStatus("Transects cast. Ready to compute rates.", 0.6);
      toast.success("Generated orthogonal transects on map.");
    }, "Cast Transects");

  const onCalculate = () =>
    withRun(async () => {
      if (!params?.has_shoreline || !params?.has_baseline) {
        toast.warning("Load both shorelines and baseline first.");
        return;
      }
      await runJob(sessionId!, "analyze", (f) => {
        if (f.type === "progress") {
          store.setStatus(f.message || "", f.progress);
          if (f.message) store.log(f.message);
        }
      });
      await store.reload();
      await store.refreshResultsLayers();
      try {
        const r = await api.forecastModels(sessionId!);
        setFcModels(r.models);
        if (!params?.forecast_model && r.models.length > 0) {
          await store.setParam("forecast_model", r.models[0]);
        }
      } catch {}
      store.setStatus("Analysis complete across all models.", 1.0);
      toast.success("Calculated shoreline rates across all models.");
    }, "Run Rate Analysis");

  const onForecast = () =>
    withRun(async () => {
      if (!params?.has_results) {
        toast.warning("Calculate change rates first.");
        return;
      }
      let model = params?.forecast_model;
      if (!model) {
        const available = fcModels.length ? fcModels : FORECAST_MODELS;
        model = available[0] || "Breakpoint (Post-break Rate)";
        await store.setParam("forecast_model", model);
      }
      await runJob(sessionId!, "forecast", (f) => {
        if (f.type === "progress") {
          store.setStatus(f.message || "", f.progress);
          if (f.message) store.log(f.message);
        }
      });
      await store.refreshResultsLayers();
      store.setVisibility("forecastLine", true);
      store.setVisibility("forecastRibbon", true);
      store.setStatus(`Forecast updated (${params?.forecast_horizon ?? 10} yrs using ${model}).`, 1.0);
      toast.success(`Updated shoreline forecast positions (${params?.forecast_horizon ?? 10} yrs).`);
    }, "Update Forecast");

  const download = (
    kind: "bundle" | "csv" | "intersections" | "transects" | "transects_rates" | "forecast"
  ) => {
    if (!sessionId) return;
    if (!params?.has_results && !params?.has_shoreline && kind !== "bundle") {
      toast.warning("No results to export. Run rate calculations first.");
      return;
    }
    toast.info(`Downloading ${kind === "bundle" ? "Full GIS Package (.ZIP)" : kind}…`);
    window.open(api.exportUrl(sessionId, kind), "_blank");
  };

  const applyPreset = (spacing: number, smoothing: number, length: number) => {
    store.setParam("spacing", spacing);
    store.setParam("smoothing", smoothing);
    store.setParam("transect_length", length);
    toast.info(`Preset applied — ${spacing}m spacing`);
  };

  const hasInputs = Boolean(params?.has_shoreline && params?.has_baseline);
  const hasResults = Boolean(params?.has_results);

  return (
    <header className="flex h-14 flex-shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 select-none">
      {/* Brand */}
      <div className="flex items-center gap-2.5 pr-1">
        <img
          src="/logo.png"
          alt="SHIFT"
          className="h-8 w-8 rounded-lg object-cover flex-shrink-0"
        />
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight text-slate-900">SHIFT</div>
          <div className="text-[11px] text-slate-500">Shoreline & River Bank Dynamics</div>
        </div>
      </div>

      <div className="h-6 w-px bg-slate-200" />

      {/* Data */}
      <input ref={slRef} type="file" accept=".geojson,.json" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onUploadShoreline(f); }} />
      <input ref={blRef} type="file" accept=".geojson,.json" className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onUploadBaseline(f); }} />

      <DropdownMenu>
        <DropdownMenuTrigger
          render={
            <Button variant="outline" size="sm" className="h-9 gap-1.5" disabled={running}>
              <Plus className="h-4 w-4 text-slate-500" /> Add data
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </Button>
          }
        />
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Load layers</DropdownMenuLabel>
            <DropdownMenuItem onClick={onLoadDemo}>
              <Play className="h-4 w-4 text-primary" /> Load demo dataset
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => slRef.current?.click()}>
              <Upload className="h-4 w-4 text-slate-500" /> Upload shorelines…
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => blRef.current?.click()}>
              <Upload className="h-4 w-4 text-slate-500" /> Upload baseline…
            </DropdownMenuItem>
            {params?.has_shoreline && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => store.setFieldMappingOpen(true)}>
                  <SlidersHorizontal className="h-4 w-4 text-sky-600" /> Configure Date & Fields…
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Cast transects + geometry popover */}
      <div className="flex items-center rounded-md border border-slate-200">
        <Button variant="ghost" size="sm" className="h-9 gap-1.5 rounded-r-none px-3"
          onClick={onPreview} disabled={!hasInputs || running}>
          <Ruler className="h-4 w-4 text-slate-500" /> Cast
        </Button>
        <Popover>
          <PopoverTrigger
            render={
              <Button variant="ghost" size="icon" className="h-9 w-8 rounded-l-none border-l border-slate-200 text-slate-500">
                <SlidersHorizontal className="h-3.5 w-3.5" />
              </Button>
            }
          />
          <PopoverContent align="start" className="w-72 space-y-3">
            <div className="gb-section-title">Transect geometry</div>
            <div className="grid grid-cols-3 gap-2">
              <NumField label="Spacing (m)" pKey="spacing" min={10} step={10} />
              <NumField label="Smooth (m)" pKey="smoothing" min={100} step={500} />
              <NumField label="Length (m)" pKey="transect_length" min={500} step={500} />
            </div>
            <div className="space-y-1.5">
              <Label className="gb-metric-label">Cast direction</Label>
              <div className="grid grid-cols-2 gap-1.5">
                <Button
                  type="button"
                  size="sm"
                  variant={params?.cast_side === "left" ? "default" : "outline"}
                  className="h-8 text-xs font-semibold"
                  onClick={() => store.setParam("cast_side", "left")}
                >
                  Left of baseline
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={params?.cast_side === "right" ? "default" : "outline"}
                  className="h-8 text-xs font-semibold"
                  onClick={() => store.setParam("cast_side", "right")}
                >
                  Right of baseline
                </Button>
              </div>
              <p className="text-[11px] text-slate-400">
                Click to cast perpendicular to the left or right of the baseline flow.
              </p>
            </div>
            <div className="flex gap-1.5">
              {([["50 m", 50, 1000, 3000], ["250 m", 250, 4000, 8000], ["1 km", 1000, 10000, 20000]] as const).map(
                ([lbl, sp, sm, ln]) => (
                  <Button key={lbl} variant="secondary" size="sm" className="h-8 flex-1 text-xs"
                    onClick={() => applyPreset(sp, sm, ln)}>
                    {lbl}
                  </Button>
                )
              )}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Run analysis (primary) + models popover */}
      <div className="flex items-center rounded-md">
        <Button size="sm" className="h-9 gap-1.5 rounded-r-none px-3 font-semibold"
          onClick={onCalculate} disabled={!hasInputs || running}>
          <Play className="h-4 w-4" /> Run analysis
        </Button>
        <Popover>
          <PopoverTrigger
            render={
              <Button size="icon" className="h-9 w-8 rounded-l-none border-l border-white/25">
                <ChevronDown className="h-3.5 w-3.5" />
              </Button>
            }
          />
          <PopoverContent align="start" className="w-64 space-y-2.5">
            <div className="gb-section-title">Statistical models</div>
            <div className="space-y-2">
              {MODELS.map(([key, label]) => (
                <label key={key} className="flex items-center justify-between text-sm text-slate-700">
                  <span>{label}</span>
                  <Switch checked={Boolean(params?.[key])} onCheckedChange={(v) => store.setParam(key, v as any)} />
                </label>
              ))}
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Forecast + config popover */}
      <div className="flex items-center rounded-md border border-slate-200">
        <Button variant="ghost" size="sm" className="h-9 gap-1.5 rounded-r-none px-3"
          onClick={onForecast} disabled={!hasResults || running}>
          <TrendingUp className="h-4 w-4 text-slate-500" /> Forecast
        </Button>
        <Popover>
          <PopoverTrigger
            render={
              <Button variant="ghost" size="icon" className="h-9 w-8 rounded-l-none border-l border-slate-200 text-slate-500">
                <SlidersHorizontal className="h-3.5 w-3.5" />
              </Button>
            }
          />
          <PopoverContent align="start" className="w-72 space-y-3">
            <div className="gb-section-title">Forecast configuration</div>
            <div className="space-y-1">
              <Label className="gb-metric-label">Driving model</Label>
              <Select
                value={params?.forecast_model || undefined}
                onValueChange={(v) => v && store.setParam("forecast_model", v)}
              >
                <SelectTrigger className="h-9 w-full text-sm">
                  <SelectValue placeholder="Choose model" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from(new Set(fcModels.length ? fcModels : FORECAST_MODELS)).map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!params?.has_results ? (
                <p className="text-[11px] text-slate-400">Run an analysis to unlock models.</p>
              ) : !params?.forecast_model ? (
                <p className="text-[11px] text-amber-600 font-medium">Choose a model to forecast.</p>
              ) : null}
            </div>
            <div className="grid grid-cols-2 gap-2">
              <NumField label="Horizon (yrs)" pKey="forecast_horizon" min={1} step={1} />
              <NumField label="Confidence (%)" pKey="forecast_ci" min={50} step={5}
                transform={{ get: (v) => Math.round(v * 100), set: (v) => v / 100 }} />
            </div>
          </PopoverContent>
        </Popover>
      </div>

      {/* Right cluster */}
      <div className="ml-auto flex items-center gap-1.5">
        {/* Export GIS Data */}
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <Button
                variant="outline"
                size="sm"
                className="h-9 gap-1.5 font-medium border-slate-200 text-slate-700 hover:text-slate-900"
                disabled={!hasResults && !hasInputs}
              >
                <Download className="h-4 w-4 text-sky-600" /> Export
                <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
              </Button>
            }
          />
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuGroup>
              <DropdownMenuLabel>GIS Data Products</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => download("bundle")}
                className="font-semibold text-sky-700 bg-sky-50/50 hover:bg-sky-100/70 cursor-pointer"
              >
                <Package className="h-4 w-4 text-sky-600" /> Download Full GIS Package (.ZIP)
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => download("csv")}>
                <FileSpreadsheet className="h-4 w-4 text-slate-500" /> Rate Metrics Summary (CSV)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => download("transects_rates")}>
                <Layers className="h-4 w-4 text-slate-500" /> Clipped Rate Transects (GeoJSON)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => download("transects")}>
                <MapPin className="h-4 w-4 text-slate-500" /> Full Orthogonal Transects (GeoJSON)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => download("intersections")}>
                <FileSpreadsheet className="h-4 w-4 text-slate-500" /> Raw Intersections Series (CSV)
              </DropdownMenuItem>
              {params?.forecast_model && (
                <DropdownMenuItem onClick={() => download("forecast")}>
                  <TrendingUp className="h-4 w-4 text-purple-600" /> Forecast Shoreline (GeoJSON)
                </DropdownMenuItem>
              )}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <Tooltip>
          <TooltipTrigger
            render={
              <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-500" onClick={onClear}>
                <RotateCcw className="h-4 w-4" />
              </Button>
            }
          />
          <TooltipContent>Reset session</TooltipContent>
        </Tooltip>

        <Dialog>
          <DialogTrigger
            render={
              <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-500">
                <HelpCircle className="h-4 w-4" />
              </Button>
            }
          />
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" /> SHIFT — Shoreline &amp; River Bank Dynamics System
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-3 text-sm leading-relaxed text-slate-600">
              <p>
                SHIFT combines USGS DSAS rates, robust regressions, and changepoint regime-shift
                detection to measure and forecast shoreline and river bank trends.
              </p>
              <ol className="list-decimal space-y-1.5 pl-5">
                <li><b>Add data</b> — load the demo or upload shorelines + baseline.</li>
                <li><b>Cast</b> — generate orthogonal transects along the baseline.</li>
                <li><b>Run analysis</b> — compute rates across all enabled models.</li>
                <li><b>Forecast</b> — project future positions with a confidence cone.</li>
              </ol>
              <p className="text-slate-500">
                Use the left panel to toggle layers, the right panel to inspect a transect, and the
                bottom dock for the attribute table, diagnostics, and console.
              </p>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      <FieldMappingModal />
    </header>
  );
}
