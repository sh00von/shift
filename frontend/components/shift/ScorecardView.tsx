"use client";

import { useEffect } from "react";
import { Trophy, Crown, Info } from "lucide-react";
import { useStore } from "@/lib/store";

const METHOD_COLORS: Record<string, string> = {
  EPR: "#64748b",
  LRR: "#2563eb",
  WLR: "#0891b2",
  "Theil-Sen": "#16a34a",
  RANSAC: "#65a30d",
  Kalman: "#7c3aed",
  Breakpoint: "#ea580c",
};

export function ScorecardView() {
  const store = useStore();
  const { sessionId, scorecard, params } = store;

  // Hydrate from the backend when the tab mounts / after a run.
  useEffect(() => {
    if (sessionId && params?.has_scorecard && !scorecard) {
      store.refreshScorecard();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, params?.has_scorecard]);

  if (!scorecard || !scorecard.available) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <div className="rounded-full bg-amber-50 p-3 text-amber-600 border border-amber-200">
          <Trophy className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold text-slate-900 text-sm">No Model Ranking Computed</h3>
          <p className="text-xs text-slate-500 max-w-md">
            Click <b>Rank Methods</b> in the Analysis ribbon to score every method with
            out-of-sample cross-validation (LOOCV + rolling-origin) and pick the best method per transect.
          </p>
        </div>
      </div>
    );
  }

  const th = scorecard.thresholds;

  return (
    <div className="flex h-full flex-col overflow-y-auto divide-y divide-slate-200 bg-white">
      {/* Headline recommendation */}
      <section className="p-4">
        <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3">
          <Crown className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-500" />
          <div>
            <div className="text-sm font-semibold text-slate-900">{scorecard.headline}</div>
            <div className="mt-0.5 text-[11px] text-slate-600">
              Ranked on out-of-sample holdout prediction error across {scorecard.n_participating}/{scorecard.n_total} transects.
              Each model was trained on historical surveys (1 to N-1) and evaluated against the latest held-out survey (N).
            </div>
          </div>
        </div>
      </section>

      {/* Leaderboard */}
      <section className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4 text-amber-600" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Method Leaderboard (Holdout Test: 1..N-1 → N)
          </h3>
        </div>
        <div className="overflow-x-auto rounded-md border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-3 py-2">Method</th>
                <th className="px-3 py-2 text-right">Holdout RMSE</th>
                <th className="px-3 py-2 text-right">Holdout MAE</th>
                <th className="px-3 py-2 text-right">In-Sample R²</th>
                <th className="px-3 py-2 text-right">BIC</th>
                <th className="px-3 py-2 text-right">Coverage</th>
                <th className="px-3 py-2 text-right">Win %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {scorecard.rows.map((r) => (
                <tr
                  key={r.method}
                  className={r.is_recommended ? "bg-amber-50/70" : "hover:bg-slate-50/70 transition-colors"}
                >
                  <td className="px-3 py-1.5 font-sans font-medium text-slate-900">
                    <span className="inline-flex items-center gap-1.5">
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-full"
                        style={{ background: METHOD_COLORS[r.method] || "#94a3b8" }}
                      />
                      {r.method}
                      {r.is_recommended && <Crown className="h-3 w-3 text-amber-500" />}
                    </span>
                  </td>
                  <td className="px-3 py-1.5 text-right font-bold text-slate-900">{r.holdout_rmse || r.loocv_rmse}</td>
                  <td className="px-3 py-1.5 text-right text-slate-700 font-medium">{r.holdout_mae || r.mae}</td>
                  <td className="px-3 py-1.5 text-right text-slate-600">{r.r2}</td>
                  <td className="px-3 py-1.5 text-right text-slate-600">{r.bic}</td>
                  <td className="px-3 py-1.5 text-right text-slate-500">{r.coverage}</td>
                  <td className="px-3 py-1.5 text-right font-semibold text-slate-900">{r.win_pct}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Winner distribution */}
      {scorecard.distribution.length > 0 && (
        <section className="p-4 space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Winning method distribution
          </h3>
          <div className="flex h-4 w-full overflow-hidden rounded-full border border-slate-200">
            {scorecard.distribution.map((d) => (
              <div
                key={d.method}
                title={`${d.method}: ${d.wins} transects (${d.win_pct}%)`}
                style={{ width: `${d.win_pct}%`, background: METHOD_COLORS[d.method] || "#94a3b8" }}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-600">
            {scorecard.distribution.map((d) => (
              <span key={d.method} className="inline-flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: METHOD_COLORS[d.method] || "#94a3b8" }} />
                {d.method} <span className="gb-num font-medium">{d.wins}</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Thresholds footnote */}
      <section className="px-4 py-3">
        <div className="flex items-start gap-2 text-[11px] text-slate-500">
          <Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <span>
            Guardrail settings used: regime shift requires ΔBIC ≥ {th.bic_gain}; robust eligibility if
            |standardised residual| &gt; {th.outlier_z}; ties within {th.tie_pct}% resolved toward the simpler model.
            These are saved with the exported session config.
          </span>
        </div>
      </section>
    </div>
  );
}
