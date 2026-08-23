"use client";

import { useEffect, useState } from "react";
import { api, DiagnosticsResponse } from "@/lib/api";
import { useStore } from "@/lib/store";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const BASE_COLS = [
  { key: "model", label: "Model / method", align: "left" },
  { key: "rate", label: "Mean rate", align: "right" },
  { key: "r2", label: "Mean R²", align: "right" },
] as const;

const ERROR_COLS = [
  { key: "rmse", label: "Residual RMSE", align: "right" },
  { key: "mae", label: "Mean MAE", align: "right" },
  { key: "bic", label: "Mean BIC", align: "right" },
] as const;

const COMP_COL = { key: "comp", label: "Complexity / regimes", align: "center" } as const;

const alignClass = (a: string) =>
  a === "right" ? "text-right" : a === "center" ? "text-center" : "text-left";

export function Diagnostics() {
  const { sessionId, params } = useStore();
  const [data, setData] = useState<DiagnosticsResponse | null>(null);

  // Re-fetch when analysis completes and again after Rank Methods runs (which
  // unlocks the error metrics RMSE/MAE/BIC).
  useEffect(() => {
    if (params?.has_results && sessionId) api.diagnostics(sessionId).then(setData);
    else setData(null);
  }, [params?.has_results, params?.has_scorecard, sessionId]);

  if (!data || !data.rows.length) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-[13px] text-slate-400">
        No diagnostics yet — run an analysis to compare model goodness-of-fit.
      </div>
    );
  }

  const cols = data.has_errors
    ? [...BASE_COLS, ...ERROR_COLS, COMP_COL]
    : [...BASE_COLS, COMP_COL];

  return (
    <div className="shift-scroll h-full space-y-4 overflow-auto p-4">
      <div className="flex items-center justify-between">
        <span className="gb-section-title">
          Cross-model benchmarks{data.has_errors ? " — in-sample fit" : ""}
        </span>
        <span className="text-[12px] text-slate-400">{data.n_transects} transects evaluated</span>
      </div>

      {/* Takeaway */}
      {data.has_errors ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50/60 px-4 py-3 text-[13px] leading-relaxed text-slate-600">
          Breakpoint regression reduces residual RMSE by{" "}
          <span className="gb-num font-semibold text-primary">{data.rmse_improvement}%</span> versus static
          linear regression, while Theil-Sen and RANSAC stay robust to tidal-spike outliers.
          <span className="mt-1 block text-[11px] text-slate-400">
            These are <b>in-sample</b> fit statistics. For <b>out-of-sample</b> predictive skill,
            see the Model Scorecard.
          </span>
        </div>
      ) : (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 px-4 py-3 text-[13px] leading-relaxed text-amber-800">
          Showing the fitted <b>R²</b> for each method. Run <b>Rank Methods</b> to compute the
          error metrics (RMSE / MAE / BIC) and the out-of-sample Scorecard ranking.
        </div>
      )}

      {/* Comparison table */}
      <div className="overflow-hidden rounded-xl border border-slate-200">
        <Table className="w-full">
          <TableHeader className="bg-slate-50">
            <TableRow className="border-slate-200 hover:bg-transparent">
              {cols.map((c) => (
                <TableHead key={c.key} className={cn("h-9 px-3 text-[12px] font-semibold text-slate-500", alignClass(c.align))}>
                  {c.label}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.rows.map((r) => {
              const highlight = r.model.includes("Breakpoint");
              return (
                <TableRow key={r.model} className={cn("border-slate-100", highlight ? "bg-primary/5" : "hover:bg-slate-50")}>
                  {cols.map((c) => (
                    <TableCell
                      key={c.key}
                      className={cn(
                        "px-3 py-2 text-[13px]",
                        alignClass(c.align),
                        c.key === "model"
                          ? cn("font-medium", highlight ? "text-primary" : "text-slate-800")
                          : "gb-num text-slate-600"
                      )}
                    >
                      {r[c.key as keyof typeof r]}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
