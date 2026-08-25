"use client";

import { useEffect } from "react";
import { TrendingUp, CheckCircle2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const MODEL_COLORS: Record<string, string> = {
  "Kalman Filter (DSAS)": "#7c3aed",
  "EKF Rate": "#10b981",
  "ARIMA": "#f59e0b",
  "Holt Exponential Smoothing": "#8b5cf6",
  "Linear Regression (LRR)": "#2563eb",
  "Classic Endpoint Rate (EPR)": "#64748b",
};

export function ForecastEvalView() {
  const store = useStore();
  const { sessionId, forecastEval, params } = store;

  useEffect(() => {
    if (sessionId && params?.has_forecast_eval && !forecastEval) {
      store.refreshForecastEval();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, params?.has_forecast_eval]);

  if (!forecastEval || !forecastEval.available) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <div className="rounded-full bg-violet-50 p-3 text-violet-600 border border-violet-200">
          <TrendingUp className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold text-slate-900 text-sm">No Forecast Evaluation Yet</h3>
          <p className="text-xs text-slate-500 max-w-md">
            Select one or more forecast models and click <b>Forecast</b>. After forecasting,
            hindcast RMSE and MAE will appear here showing which model predicts best on your dataset.
          </p>
        </div>
      </div>
    );
  }

  const { rows, best_model, n_transects } = forecastEval;

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-white">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">Forecast Hindcast Evaluation</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Each model trained on surveys 1…N-1 and tested against the withheld last survey.
            Lower RMSE = better forecasting accuracy on this dataset.
          </p>
        </div>
        <span className="gb-num text-[11px] text-slate-400">{n_transects} transects</span>
      </div>

      {/* Best model callout */}
      {best_model && (
        <div className="mx-4 mt-3 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50/70 px-3 py-2.5">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
          <span className="text-[13px] text-emerald-800">
            <b>{best_model}</b> has the lowest hindcast RMSE — best forecasting accuracy for this dataset.
          </span>
        </div>
      )}

      {/* Results table */}
      <div className="px-4 py-3">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="pb-2 text-left font-semibold text-slate-500">Model</th>
              <th className="pb-2 text-right font-semibold text-slate-500">Hindcast RMSE</th>
              <th className="pb-2 text-right font-semibold text-slate-500">Hindcast MAE</th>
              <th className="pb-2 text-right font-semibold text-slate-500">N evaluated</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {rows.map((row, i) => {
              const isBest = row.model === best_model;
              const color = MODEL_COLORS[row.model] ?? "#64748b";
              return (
                <tr key={row.model} className={cn("transition-colors", isBest && "bg-emerald-50/40")}>
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <span className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }} />
                      <span className={cn("font-medium", isBest ? "text-slate-900" : "text-slate-700")}>
                        {row.model}
                      </span>
                      {isBest && (
                        <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                          best
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={cn("py-2.5 text-right gb-num", isBest ? "text-emerald-700 font-semibold" : "text-slate-700")}>
                    {row.rmse}
                  </td>
                  <td className="py-2.5 text-right gb-num text-slate-600">{row.mae}</td>
                  <td className="py-2.5 text-right text-slate-400">{row.n}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Explanation */}
      <div className="mx-4 mb-4 rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2.5 text-[11px] text-slate-500 leading-relaxed">
        <b>RMSE / MAE</b> are hindcast errors in metres — the distance between the model's
        predicted shoreline position and the actual withheld survey position.
        These are <b>forecast accuracy</b> metrics, not measures of erosion/accretion rate quality.
      </div>
    </div>
  );
}
