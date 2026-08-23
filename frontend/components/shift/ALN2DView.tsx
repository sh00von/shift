"use client";

import { useEffect, useState } from "react";
import { Sparkles, Scale, Activity } from "lucide-react";
import { useStore } from "@/lib/store";
import { api, Aln2dSummaryRow, Aln2dReachRow } from "@/lib/api";

export function ALN2DView() {
  const store = useStore();
  const { sessionId, params } = store;

  const [summary, setSummary] = useState<Aln2dSummaryRow[]>([]);
  const [reaches, setReaches] = useState<Aln2dReachRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    Promise.all([
      api.aln2dSummary(sessionId).catch(() => ({ rows: [] })),
      api.aln2dReachRows(sessionId).catch(() => ({ rows: [] })),
    ])
      .then(([sumRes, reachRes]) => {
        setSummary(sumRes.rows || []);
        setReaches(reachRes.rows || []);
      })
      .finally(() => setLoading(false));
  }, [sessionId, params?.has_aln2d_results, store.aln2dSummary]);

  const hasData = summary.length > 0 || reaches.length > 0;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center p-8 text-sm text-slate-500">
        Loading 2D-ALN Morphodynamic Engine results…
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <div className="rounded-full bg-emerald-50 p-3 text-emerald-600 border border-emerald-200">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h3 className="font-semibold text-slate-900 text-sm">No 2D-ALN Results Computed</h3>
          <p className="text-xs text-slate-500 max-w-md">
            Click <b>2D-ALN (2D-ALN)</b> in the Analysis Ribbon to execute the pure 2D morphodynamic model (2D Boolean differencing and alongshore reach normalization).
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto divide-y divide-slate-200 bg-white">
      {/* 1. Executive Summary & Morphodynamic Budget */}
      <section className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-600" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              2D Areal Shoreline Morphodynamic Budget Summary
            </h3>
          </div>
          <span className="text-[11px] text-slate-500">Continuous 2D Boolean Polygon Mass</span>
        </div>

        <div className="overflow-x-auto rounded-md border border-slate-200">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="px-3 py-2">Transition Period</th>
                <th className="px-3 py-2 text-right">Span (yrs)</th>
                <th className="px-3 py-2 text-right text-red-700">Eroded (km²)</th>
                <th className="px-3 py-2 text-right text-emerald-700">Accreted (km²)</th>
                <th className="px-3 py-2 text-right text-red-700">Erosion Rate (km²/yr)</th>
                <th className="px-3 py-2 text-right text-emerald-700">Accretion Rate (km²/yr)</th>
                <th className="px-3 py-2 text-right font-bold">Net Balance (km²/yr)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {summary.map((row, idx) => {
                const netVal = parseFloat(row.net_balance_km2_yr);
                const isPos = !isNaN(netVal) && netVal >= 0;
                return (
                  <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-3 py-1.5 font-sans font-medium text-slate-900">
                      {row.from_epoch} → {row.to_epoch}
                    </td>
                    <td className="px-3 py-1.5 text-right text-slate-600">{row.span_years}</td>
                    <td className="px-3 py-1.5 text-right text-red-600">{row.eroded_km2}</td>
                    <td className="px-3 py-1.5 text-right text-emerald-600">{row.accreted_km2}</td>
                    <td className="px-3 py-1.5 text-right text-red-600">{row.erosion_rate_km2_yr}</td>
                    <td className="px-3 py-1.5 text-right text-emerald-600">{row.accretion_rate_km2_yr}</td>
                    <td className={`px-3 py-1.5 text-right font-bold ${isPos ? "text-emerald-600" : "text-red-600"}`}>
                      {isPos ? `+${row.net_balance_km2_yr}` : row.net_balance_km2_yr}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* 2. Reach-Based Normalized Migration Rates */}
      <section className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-purple-600" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Reach-Based Normalized Migration Rates (2D-ALN) ({reaches.length} Reaches)
            </h3>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">v = (Area / Length) / Time</span>
        </div>

        <div className="overflow-x-auto rounded-md border border-slate-200 max-h-72 overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 sticky top-0 bg-white">
              <tr>
                <th className="px-3 py-2">Reach #</th>
                <th className="px-3 py-2 text-right">Length (m)</th>
                <th className="px-3 py-2 text-right font-bold text-emerald-700">Net 2D-ALN Rate (m/yr)</th>
                <th className="px-3 py-2 text-right text-red-600">2D Ero Rate (m/yr)</th>
                <th className="px-3 py-2 text-right text-emerald-600">2D Acc Rate (m/yr)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
              {reaches.map((row) => (
                <tr key={row.reach_id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-3 py-1.5 font-sans font-medium text-slate-900">Reach {row.reach_id}</td>
                  <td className="px-3 py-1.5 text-right text-slate-600">{row.length_m}</td>
                  <td className={`px-3 py-1.5 text-right font-bold ${parseFloat(row.net_2d_m_yr) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {parseFloat(row.net_2d_m_yr) > 0 ? `+${row.net_2d_m_yr}` : row.net_2d_m_yr}
                  </td>
                  <td className="px-3 py-1.5 text-right text-red-600">{row.ero_2d_m_yr}</td>
                  <td className="px-3 py-1.5 text-right text-emerald-600">{row.acc_2d_m_yr}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

