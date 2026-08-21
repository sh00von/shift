"use client";

import React, { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import { api, ShorelineFieldsResponse } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal,
  Layers,
  FileSpreadsheet,
  Info,
  Clock,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

const COMMON_FORMATS = [
  { value: "auto", label: "Auto-detect (Smart parser & Year extract)" },
  { value: "%d/%m/%Y", label: "DD/MM/YYYY (e.g. 01/01/1995)" },
  { value: "%Y-%m-%d", label: "YYYY-MM-DD (e.g. 1995-01-01)" },
  { value: "%m/%d/%Y", label: "MM/DD/YYYY (e.g. 01/01/1995)" },
  { value: "%d-%m-%Y", label: "DD-MM-YYYY (e.g. 01-01-1995)" },
  { value: "%Y", label: "Year Only / YYYY (e.g. 1995)" },
  { value: "custom", label: "Custom format (specify strftime)…" },
];

export function FieldMappingModal() {
  const {
    sessionId,
    isFieldMappingOpen,
    setFieldMappingOpen,
    refreshShorelines,
    log,
  } = useStore();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState<ShorelineFieldsResponse | null>(null);

  const [dateCol, setDateCol] = useState<string>("");
  const [dateFormatPreset, setDateFormatPreset] = useState<string>("auto");
  const [customFormat, setCustomFormat] = useState<string>("");
  const [uncertaintyCol, setUncertaintyCol] = useState<string>("__none__");
  const [newUncertaintyName, setNewUncertaintyName] = useState<string>("Uncertainty");
  const [defaultUncertainty, setDefaultUncertainty] = useState<number>(10.0);

  useEffect(() => {
    if (isFieldMappingOpen && sessionId) {
      setLoading(true);
      api
        .getShorelineFields(sessionId)
        .then((res) => {
          setData(res);
          setDateCol(res.date_col || (res.columns.length > 0 ? res.columns[0] : ""));

          const isPreset = COMMON_FORMATS.some(
            (f) => f.value === res.date_format && f.value !== "custom"
          );
          if (isPreset) {
            setDateFormatPreset(res.date_format || "auto");
            setCustomFormat("");
          } else {
            setDateFormatPreset("custom");
            setCustomFormat(res.date_format || "");
          }

          setUncertaintyCol(res.uncertainty_col || "__none__");
          setDefaultUncertainty(res.default_uncertainty || 10.0);
        })
        .catch((err) => {
          console.error("Failed to load shoreline fields:", err);
          toast.error("Failed to load shoreline attributes");
        })
        .finally(() => setLoading(false));
    }
  }, [isFieldMappingOpen, sessionId]);

  const activeDateFormat = dateFormatPreset === "custom" ? customFormat : dateFormatPreset;

  const updatePreview = async (
    newDateCol = dateCol,
    newDateFmt = activeDateFormat,
    newUncCol = uncertaintyCol,
    newDefUnc = defaultUncertainty,
    newCreateCol?: string | null
  ) => {
    if (!sessionId) return;
    try {
      const res = await api.setShorelineFields(sessionId, {
        date_col: newDateCol,
        date_format: newDateFmt,
        uncertainty_col: newUncCol === "__none__" || newUncCol === "__create__" ? null : newUncCol,
        default_uncertainty: newDefUnc,
        create_uncertainty_col: newUncCol === "__create__" ? (newCreateCol || newUncertaintyName) : null,
      });
      setData(res);
    } catch (e) {
      console.warn("Preview update issue:", e);
    }
  };

  const handleSave = async () => {
    if (!sessionId || !dateCol) {
      toast.error("Please select a date column");
      return;
    }
    setSaving(true);
    try {
      const isCreate = uncertaintyCol === "__create__";
      const res = await api.setShorelineFields(sessionId, {
        date_col: dateCol,
        date_format: activeDateFormat,
        uncertainty_col: uncertaintyCol === "__none__" || isCreate ? null : uncertaintyCol,
        default_uncertainty: defaultUncertainty,
        create_uncertainty_col: isCreate ? newUncertaintyName : null,
      });
      setData(res);
      await refreshShorelines();
      log(
        `Configured shoreline fields: Date="${dateCol}" (${activeDateFormat}), Uncertainty="${
          isCreate
            ? `New field '${newUncertaintyName}' (±${defaultUncertainty}m)`
            : uncertaintyCol === "__none__"
            ? `Default ${defaultUncertainty}m`
            : uncertaintyCol
        }"`,
        "SUCCESS"
      );
      toast.success("Shoreline fields configured successfully!");
      setFieldMappingOpen(false);
    } catch (err: any) {
      toast.error(`Failed to save field mapping: ${err.message || "Unknown error"}`);
    } finally {
      setSaving(false);
    }
  };

  const invalidDates =
    data?.preview_rows.filter((r) => !r.parsed_year || r.parsed_date === "Invalid Date") || [];

  return (
    <Dialog open={isFieldMappingOpen} onOpenChange={setFieldMappingOpen}>
      <DialogContent className="w-[94vw] sm:w-[94vw] max-w-6xl sm:max-w-6xl h-[86vh] sm:h-[86vh] max-h-[86vh] flex flex-col !p-0 !gap-0 overflow-hidden bg-white text-slate-900 border border-slate-200 shadow-2xl rounded-2xl">
        
        {/* Top Workbench Header */}
        <DialogHeader className="px-6 py-4 pr-14 border-b border-slate-100 bg-slate-50/60 shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-sky-600 text-white flex items-center justify-center shadow-md shadow-sky-600/20 shrink-0">
                <SlidersHorizontal className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="text-lg font-bold text-slate-900 font-sans tracking-tight">
                  Shoreline Survey Field Mapping & Date Calibration
                </DialogTitle>
                <DialogDescription className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                  <span>Match survey attributes to date and uncertainty channels for time-series extraction & forecasting.</span>
                  {data?.filename && (
                    <>
                      <span>•</span>
                      <span className="font-semibold text-slate-700">{data.filename}</span>
                    </>
                  )}
                </DialogDescription>
              </div>
            </div>

            {data?.detected_years && data.detected_years.length > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold mr-4 shrink-0">
                <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                <span>
                  {data.detected_years.length} Survey Epochs ({data.detected_years[0]} –{" "}
                  {data.detected_years[data.detected_years.length - 1]})
                </span>
              </div>
            )}
          </div>
        </DialogHeader>

        {/* Workbench Body (Split View) */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-xs text-slate-400">
            Loading shoreline attribute schema…
          </div>
        ) : !data?.has_shoreline ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-500">
            <FileSpreadsheet className="h-12 w-12 text-slate-300 mb-3" />
            <div className="text-sm font-semibold text-slate-700">No shoreline layer loaded</div>
            <div className="text-xs text-slate-400 max-w-sm mt-1">
              Please load the demo dataset or upload a shoreline GeoJSON file first.
            </div>
          </div>
        ) : (
          <div className="flex-1 min-h-0 flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-slate-100 overflow-hidden bg-white">
            
            {/* Left Control Panel */}
            <div className="w-full lg:w-96 p-6 overflow-y-auto shrink-0 space-y-5 bg-slate-50/40">
              
              <div className="space-y-1">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-sans">
                  Field Configuration
                </h3>
                <p className="text-[11px] text-slate-400">
                  Select which attributes represent the survey timeline and measurement errors.
                </p>
              </div>

              {/* 1. Date Field */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                <Label className="text-xs font-semibold text-slate-800 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5 text-sky-600" />
                    Date / Time Attribute <span className="text-rose-500">*</span>
                  </span>
                </Label>
                <Select
                  value={dateCol}
                  onValueChange={(val) => {
                    if (val) {
                      setDateCol(val);
                      updatePreview(val, activeDateFormat, uncertaintyCol, defaultUncertainty);
                    }
                  }}
                >
                  <SelectTrigger className="h-9 text-xs bg-slate-50/50 border-slate-300 font-medium">
                    <SelectValue placeholder="Select Date Column" />
                  </SelectTrigger>
                  <SelectContent>
                    {data.columns.map((c) => (
                      <SelectItem key={c} value={c} className="text-xs font-medium">
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-slate-400">
                  Column containing timestamps, survey dates, or 4-digit years.
                </p>
              </div>

              {/* 2. Date Format */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                <Label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <Clock className="h-3.5 w-3.5 text-blue-600" />
                  Date Format Parser
                </Label>
                <Select
                  value={dateFormatPreset}
                  onValueChange={(val) => {
                    if (val) {
                      setDateFormatPreset(val);
                      const fmt = val === "custom" ? customFormat : val;
                      updatePreview(dateCol, fmt, uncertaintyCol, defaultUncertainty);
                    }
                  }}
                >
                  <SelectTrigger className="h-9 text-xs bg-slate-50/50 border-slate-300 font-medium">
                    <SelectValue placeholder="Select Date Format" />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_FORMATS.map((f) => (
                      <SelectItem key={f.value} value={f.value} className="text-xs font-medium">
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {dateFormatPreset === "custom" && (
                  <div className="pt-1.5 space-y-1">
                    <Label className="text-[11px] font-medium text-slate-600">Custom strftime pattern</Label>
                    <Input
                      className="h-8 text-xs font-mono bg-slate-50/50 border-slate-300"
                      placeholder="e.g. %Y%m%d or %d-%b-%Y"
                      value={customFormat}
                      onChange={(e) => {
                        setCustomFormat(e.target.value);
                        updatePreview(dateCol, e.target.value, uncertaintyCol, defaultUncertainty);
                      }}
                    />
                  </div>
                )}
                <p className="text-[11px] text-slate-400">
                  Extracts fractional decimal years (e.g. 1995.0) for linear & changepoint regressions.
                </p>
              </div>

              {/* 3. Uncertainty Field */}
              <div className="space-y-1.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                <Label className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  <ShieldAlert className="h-3.5 w-3.5 text-indigo-600" />
                  Uncertainty Attribute
                </Label>
                <Select
                  value={uncertaintyCol}
                  onValueChange={(val) => {
                    if (val) {
                      setUncertaintyCol(val);
                      updatePreview(dateCol, activeDateFormat, val, defaultUncertainty);
                    }
                  }}
                >
                  <SelectTrigger className="h-9 text-xs bg-slate-50/50 border-slate-300 font-medium">
                    <SelectValue placeholder="Select Uncertainty Column" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__" className="text-xs text-slate-600 font-medium">
                      (None — Use Fixed Default Value)
                    </SelectItem>
                    {data.columns.map((c) => (
                      <SelectItem key={c} value={c} className="text-xs font-medium">
                        {c}
                      </SelectItem>
                    ))}
                    <SelectItem value="__create__" className="text-xs text-sky-700 font-bold bg-sky-50/60">
                      + Add / Create New Uncertainty Field…
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[11px] text-slate-400">
                  Per-shoreline positional error or digitizing uncertainty.
                </p>
              </div>

              {/* Show New Column Name if __create__ selected */}
              {uncertaintyCol === "__create__" && (
                <div className="space-y-1.5 p-3.5 rounded-xl bg-sky-50/60 border border-sky-200/80 shadow-xs">
                  <Label className="text-xs font-semibold text-sky-900 flex items-center gap-1.5">
                    New Column Name
                  </Label>
                  <Input
                    className="h-8 text-xs font-medium bg-white border-sky-300"
                    placeholder="e.g. Uncertainty or Pos_Error"
                    value={newUncertaintyName}
                    onChange={(e) => {
                      setNewUncertaintyName(e.target.value);
                      updatePreview(dateCol, activeDateFormat, uncertaintyCol, defaultUncertainty, e.target.value);
                    }}
                  />
                  <p className="text-[11px] text-sky-700">
                    Will create attribute <code className="font-mono font-bold">{newUncertaintyName || "Uncertainty"}</code> on all shoreline features with the assigned default value below.
                  </p>
                </div>
              )}

              {/* Show Default Uncertainty ONLY if __none__ or __create__ (Hide when existing column is chosen) */}
              {(uncertaintyCol === "__none__" || uncertaintyCol === "__create__") && (
                <div className="space-y-1.5 p-3.5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
                  <Label className="text-xs font-semibold text-slate-800">
                    {uncertaintyCol === "__create__" ? "Initial Uncertainty Value (± meters)" : "Default Uncertainty (± meters)"}
                  </Label>
                  <Input
                    type="number"
                    step="0.5"
                    min="0.1"
                    className="h-9 text-xs bg-slate-50/50 border-slate-300 font-medium"
                    value={defaultUncertainty}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value) || 10.0;
                      setDefaultUncertainty(v);
                      updatePreview(dateCol, activeDateFormat, uncertaintyCol, v);
                    }}
                  />
                  <p className="text-[11px] text-slate-400">
                    {uncertaintyCol === "__create__"
                      ? "Applied to every survey in the newly created uncertainty field."
                      : "Fallback tolerance applied since no uncertainty column is selected."}
                  </p>
                </div>
              )}

              {/* Detected Epoch Badges */}
              {data.detected_years.length > 0 && (
                <div className="space-y-2 p-3.5 rounded-xl bg-sky-50/60 border border-sky-200/80">
                  <div className="text-xs font-bold text-sky-900 flex items-center justify-between">
                    <span>Survey Timeline</span>
                    <span className="text-[10px] font-mono text-sky-700">
                      {data.detected_years.length} epochs
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {data.detected_years.map((y) => (
                      <span
                        key={y}
                        className="px-2 py-0.5 rounded-md bg-white text-sky-800 font-mono font-bold text-[11px] border border-sky-200 shadow-2xs"
                      >
                        {y}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Right Interactive Table Preview */}
            <div className="flex-1 flex flex-col min-w-0 p-6 overflow-hidden space-y-4">
              
              <div className="flex items-center justify-between shrink-0">
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 font-sans">
                    Live Data & Extraction Preview
                  </h3>
                  <p className="text-xs text-slate-500">
                    Inspecting real-time date and uncertainty parsing for the first {data.preview_rows.length} features.
                  </p>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono text-slate-500">
                  <Info className="h-4 w-4 text-sky-600" />
                  <span>Real-time calibration</span>
                </div>
              </div>

              {/* Invalid Dates Alert */}
              {invalidDates.length > 0 && (
                <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-xs shrink-0">
                  <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold text-rose-950">Date Parsing Warning</div>
                    <div className="text-[11px] text-rose-800 mt-0.5">
                      {invalidDates.length} of {data.preview_rows.length} preview rows could not be parsed with the selected format. Try choosing a specific format from the dropdown.
                    </div>
                  </div>
                </div>
              )}

              {/* Full Width Scrollable Table */}
              <div className="flex-1 min-h-0 border border-slate-200 rounded-xl overflow-hidden shadow-xs flex flex-col bg-white">
                <div className="flex-1 overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse font-sans">
                    <thead className="sticky top-0 bg-slate-100/90 backdrop-blur-md border-b border-slate-200 z-10">
                      <tr className="text-slate-700 font-bold text-[11px] uppercase tracking-wider">
                        <th className="px-4 py-3 w-12 text-slate-400">#</th>
                        <th className="px-4 py-3">Raw Attribute Value</th>
                        <th className="px-4 py-3">Parsed Calendar Date</th>
                        <th className="px-4 py-3">Extracted Survey Year</th>
                        <th className="px-4 py-3">Uncertainty Channel</th>
                        <th className="px-4 py-3 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-150 text-slate-700 font-sans">
                      {data.preview_rows.map((row) => {
                        const isValid = row.parsed_year && row.parsed_date !== "Invalid Date";
                        return (
                          <tr
                            key={row.index}
                            className={`hover:bg-slate-50/80 transition-colors ${
                              !isValid ? "bg-rose-50/30" : ""
                            }`}
                          >
                            <td className="px-4 py-2.5 text-slate-400 font-mono text-[11px]">
                              {row.index + 1}
                            </td>
                            <td className="px-4 py-2.5 font-mono font-medium text-slate-900">
                              {row.raw_date || (
                                <span className="text-slate-400 italic font-sans font-normal">
                                  Empty
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 font-mono">
                              {row.parsed_date === "Invalid Date" ? (
                                <span className="text-rose-600 font-bold">Invalid Format</span>
                              ) : (
                                <span className="text-sky-700 font-semibold">{row.parsed_date}</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5">
                              {row.parsed_year ? (
                                <span className="inline-block px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-mono font-bold text-[11px] border border-emerald-200">
                                  {row.parsed_year}
                                </span>
                              ) : (
                                <span className="text-slate-400 font-mono">—</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 font-mono text-slate-600">
                              ±{row.parsed_uncertainty} m
                              {row.raw_uncertainty === "(Default)" && (
                                <span className="text-[10px] text-slate-400 ml-1 font-sans">
                                  (fixed)
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-right font-medium text-[11px]">
                              {isValid ? (
                                <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50/80 px-2 py-0.5 rounded border border-emerald-200">
                                  <CheckCircle2 className="h-3 w-3" /> Ready
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                                  <AlertTriangle className="h-3 w-3" /> Fix Format
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Workbench Footer */}
        <DialogFooter className="px-6 py-3.5 border-t border-slate-100 bg-slate-50/60 shrink-0 flex items-center justify-between gap-4">
          <div className="text-xs text-slate-500 flex items-center gap-2">
            <span className="font-semibold text-slate-700">Active Mapping:</span>
            <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
              Date: {dateCol || "None"} ({activeDateFormat})
            </span>
            <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-700">
              Uncertainty: {uncertaintyCol === "__none__" ? `Default (${defaultUncertainty}m)` : uncertaintyCol}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              className="text-xs h-9 font-medium px-4 border-slate-300"
              onClick={() => setFieldMappingOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="text-xs h-9 bg-sky-600 hover:bg-sky-700 text-white font-semibold px-6 shadow-sm"
              disabled={saving || !data?.has_shoreline || !dateCol}
              onClick={handleSave}
            >
              {saving ? "Applying Schema…" : "Save & Apply Field Mapping"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
