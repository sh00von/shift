"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, BarChart3, FlaskConical, GitBranch,
  RefreshCw, Loader2, AlertTriangle, Info,
} from "lucide-react";
import { api, DiagnosticsData, ScatterPoint } from "@/lib/api";
import { runJob } from "@/lib/api";
import { useStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── helpers ────────────────────────────────────────────────────────────────

const MK_COLOR: Record<string, string> = {
  "Erosion★":   "#ef4444",
  "Accretion★": "#10b981",
  "Stable":     "#94a3b8",
  "—":          "#cbd5e1",
};

const CBC_LABELS = [
  "Monotonic Erosion",
  "Monotonic Accretion",
  "Cyclical",
  "Interrupted",
  "Recovery",
  "Stable",
] as const;

// ── Moran's I card ─────────────────────────────────────────────────────────

function MoransCard({ data }: { data: DiagnosticsData }) {
  const m = data.morans;
  if (!m || m.I === null) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-[12px] text-slate-400">
        Moran&apos;s I — insufficient data (need ≥ 4 transects with rates).
      </div>
    );
  }
  const interp = m.interpretation ?? "—";
  const chipCls =
    interp === "Clustered"
      ? "bg-sky-100 text-sky-700"
      : interp === "Dispersed"
      ? "bg-amber-100 text-amber-700"
      : "bg-slate-100 text-slate-600";

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">Moran&apos;s I</span>
        <span className="text-[18px] font-bold text-slate-800 gb-num">{m.I?.toFixed(3)}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">Z</span>
        <span className="text-[14px] font-semibold text-slate-700 gb-num">{m.z_score?.toFixed(2)}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wide">p</span>
        <span className="text-[14px] font-semibold text-slate-700 gb-num">{m.p_value?.toFixed(4)}</span>
      </div>
      <span className={cn("rounded-full px-2.5 py-0.5 text-[11px] font-semibold", chipCls)}>
        {interp}
      </span>
      <span className="text-[11px] text-slate-400">
        {interp === "Clustered"
          ? "Similar rates cluster spatially — erosion/accretion zones are spatially coherent."
          : interp === "Dispersed"
          ? "Rates are more uniform than random — no dominant spatial clustering."
          : "No significant spatial pattern in transect rates."}
      </span>
    </div>
  );
}

// ── Spatial smoothing slider ────────────────────────────────────────────────

function SmoothingSlider({
  window: win,
  onChange,
}: {
  window: number;
  onChange: (w: number) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] text-slate-500 whitespace-nowrap">Smoothing window</span>
      <input
        type="range"
        min={1}
        max={15}
        step={1}
        value={win}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-36 accent-sky-600"
      />
      <span className="gb-num text-[12px] font-semibold text-slate-700 w-6 text-right">{win}</span>
      <span className="text-[11px] text-slate-400">transects</span>
      <span className="text-[11px] text-slate-300">(display-only, does not affect analysis)</span>
    </div>
  );
}

// ── CBC donut chart (pure SVG) ──────────────────────────────────────────────

function CbcDonut({ legend }: { legend: DiagnosticsData["cbc_legend"] }) {
  const total = legend.reduce((s, l) => s + l.count, 0);
  if (total === 0) return <div className="text-[12px] text-slate-400">Run CBC to see results.</div>;

  const R = 52, cx = 60, cy = 60, stroke = 18;
  const circ = 2 * Math.PI * R;
  let offset = 0;
  const slices = legend
    .filter((l) => l.count > 0)
    .map((l) => {
      const frac = l.count / total;
      const dash = frac * circ;
      const seg = { label: l.label, color: l.color, dasharray: `${dash} ${circ - dash}`, offset };
      offset += dash;
      return seg;
    });

  return (
    <div className="flex items-center gap-6">
      <svg width={120} height={120}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
        {slices.map((s) => (
          <circle
            key={s.label}
            cx={cx} cy={cy} r={R}
            fill="none"
            stroke={s.color}
            strokeWidth={stroke}
            strokeDasharray={s.dasharray}
            strokeDashoffset={-s.offset}
            transform={`rotate(-90 ${cx} ${cy})`}
          />
        ))}
        <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle"
          fontSize={13} fontWeight={700} fill="#1e293b">{total}</text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize={9} fill="#94a3b8">transects</text>
      </svg>

      <div className="flex flex-col gap-1">
        {legend.map((l) => (
          <div key={l.label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm flex-shrink-0" style={{ background: l.color }} />
            <span className="text-[12px] text-slate-700">{l.label}</span>
            <span className="gb-num text-[11px] text-slate-400">
              {l.count} ({total > 0 ? ((l.count / total) * 100).toFixed(0) : 0}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── EPR vs LRR scatter (pure SVG) ─────────────────────────────────────────

function ScatterPlot({
  scatter,
  regLine,
  outlierCount,
  onSelect,
}: {
  scatter: ScatterPoint[];
  regLine: DiagnosticsData["reg_line"];
  outlierCount: number;
  onSelect: (tid: number) => void;
}) {
  if (!scatter.length) return <div className="text-[12px] text-slate-400">No scatter data.</div>;

  const W = 340, H = 240, PAD = 36;
  const xs = scatter.map((p) => p.lrr);
  const ys = scatter.map((p) => p.epr);
  const allX = regLine ? [...xs, regLine.x[0], regLine.x[1]] : xs;
  const allY = regLine ? [...ys, regLine.y[0], regLine.y[1]] : ys;
  const xMin = Math.min(...allX), xMax = Math.max(...allX);
  const yMin = Math.min(...allY), yMax = Math.max(...allY);
  const xRange = xMax - xMin || 1, yRange = yMax - yMin || 1;

  const sx = (v: number) => PAD + ((v - xMin) / xRange) * (W - 2 * PAD);
  const sy = (v: number) => H - PAD - ((v - yMin) / yRange) * (H - 2 * PAD);

  // 1:1 line
  const oneMin = Math.min(xMin, yMin), oneMax = Math.max(xMax, yMax);

  return (
    <div>
      {outlierCount > 0 && (
        <div className="mb-2 flex items-center gap-1.5 text-[12px] text-amber-700">
          <AlertTriangle className="h-3.5 w-3.5" />
          {outlierCount} outlier transect{outlierCount > 1 ? "s" : ""} flagged — EPR and LRR diverge unusually.
        </div>
      )}
      <svg width={W} height={H} className="overflow-visible">
        {/* axes */}
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#e2e8f0" strokeWidth={1} />
        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#e2e8f0" strokeWidth={1} />
        <text x={W / 2} y={H - 4} textAnchor="middle" fontSize={10} fill="#94a3b8">LRR (m/yr)</text>
        <text x={10} y={H / 2} textAnchor="middle" fontSize={10} fill="#94a3b8"
          transform={`rotate(-90 10 ${H / 2})`}>EPR (m/yr)</text>

        {/* ±0.5 tolerance band */}
        {(() => {
          const x1 = sx(oneMin), x2 = sx(oneMax);
          const y1hi = sy(oneMin + 0.5), y1lo = sy(oneMin - 0.5);
          const y2hi = sy(oneMax + 0.5), y2lo = sy(oneMax - 0.5);
          return (
            <polygon
              points={`${x1},${y1hi} ${x2},${y2hi} ${x2},${y2lo} ${x1},${y1lo}`}
              fill="#e2e8f0" opacity={0.5}
            />
          );
        })()}

        {/* 1:1 line */}
        <line
          x1={sx(oneMin)} y1={sy(oneMin)} x2={sx(oneMax)} y2={sy(oneMax)}
          stroke="#94a3b8" strokeWidth={1} strokeDasharray="4 3"
        />

        {/* regression line */}
        {regLine && (
          <line
            x1={sx(regLine.x[0])} y1={sy(regLine.y[0])}
            x2={sx(regLine.x[1])} y2={sy(regLine.y[1])}
            stroke="#7c3aed" strokeWidth={1.5}
          />
        )}

        {/* points */}
        {scatter.map((p) => (
          <circle
            key={p.transect_id}
            cx={sx(p.lrr)} cy={sy(p.epr)}
            r={p.is_outlier ? 5 : 3}
            fill={MK_COLOR[p.mk_trend] ?? "#94a3b8"}
            stroke={p.is_outlier ? "#f59e0b" : "white"}
            strokeWidth={p.is_outlier ? 1.5 : 0.5}
            opacity={0.85}
            className="cursor-pointer"
            onClick={() => onSelect(p.transect_id)}
          >
            <title>T-{p.transect_id} | EPR: {p.epr} | LRR: {p.lrr} | {p.mk_trend}</title>
          </circle>
        ))}
      </svg>

      {/* legend */}
      <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
        {Object.entries(MK_COLOR).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: c }} />
            {k}
          </span>
        ))}
        {regLine && (
          <span className="flex items-center gap-1">
            <span className="inline-block h-0.5 w-4 bg-violet-500" />
            Regression (R²={regLine.r2.toFixed(2)})
          </span>
        )}
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-sm bg-slate-200" />
          ±0.5 m/yr band
        </span>
      </div>
    </div>
  );
}

// ── Monte Carlo section ────────────────────────────────────────────────────

function MonteCarloSection({
  sessionId,
  mcAvailable,
  mcRows,
  onDone,
}: {
  sessionId: string;
  mcAvailable: boolean;
  mcRows: DiagnosticsData["mc_rows"];
  onDone: () => void;
}) {
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

  const runMC = async () => {
    setRunning(true);
    setMsg("Initialising…");
    try {
      await runJob(sessionId, "montecarlo", (f) => {
        if (f.message) setMsg(f.message);
      });
      onDone();
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  // Show summary stats if available
  const summary =
    mcRows.length > 0
      ? (() => {
          const widths = mcRows.map(
            (r) =>
              (r.lrr_mc_high ?? 0) - (r.lrr_mc_low ?? 0)
          );
          const mean = widths.reduce((a, b) => a + b, 0) / widths.length;
          const max = Math.max(...widths);
          return { mean: mean.toFixed(2), max: max.toFixed(2) };
        })()
      : null;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[12px] text-slate-500">
        Perturbs each survey position by ±σ (from the uncertainty column) N=500 times, refits
        LRR and Sen&apos;s slope, and reports empirical 90% CIs. Wider CIs flag transects where
        positional uncertainty significantly affects the rate estimate.
      </p>

      <div className="flex items-center gap-3">
        <Button
          size="sm"
          variant="outline"
          onClick={runMC}
          disabled={running}
          className="gap-2 h-8"
        >
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FlaskConical className="h-3.5 w-3.5" />}
          {running ? "Running…" : mcAvailable ? "Re-run Monte Carlo" : "Run Monte Carlo (N=500)"}
        </Button>
        {msg && <span className="text-[11px] text-slate-400">{msg}</span>}
      </div>

      {summary && (
        <div className="flex gap-6 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wide">Mean LRR CI width</div>
            <div className="gb-num text-[17px] font-bold text-slate-800">{summary.mean} m/yr</div>
          </div>
          <div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wide">Max LRR CI width</div>
            <div className="gb-num text-[17px] font-bold text-slate-800">{summary.max} m/yr</div>
          </div>
          <div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wide">Transects simulated</div>
            <div className="gb-num text-[17px] font-bold text-slate-800">{mcRows.length}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── CBC runner ─────────────────────────────────────────────────────────────

function CbcSection({
  sessionId,
  data,
  onDone,
}: {
  sessionId: string;
  data: DiagnosticsData;
  onDone: () => void;
}) {
  const [running, setRunning] = useState(false);
  const [msg, setMsg] = useState("");

  const runCBC = async () => {
    setRunning(true);
    setMsg("Classifying…");
    try {
      await runJob(sessionId, "cbc", (f) => {
        if (f.message) setMsg(f.message);
      });
      onDone();
    } catch (e: any) {
      setMsg(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-[12px] text-slate-500">
        Classifies each transect into one of 6 coastal behaviour types using Mann-Kendall significance,
        autocorrelation, CUSUM structural-break detection, and half-series comparison.
      </p>
      <div className="flex items-center gap-3">
        <Button size="sm" variant="outline" onClick={runCBC} disabled={running} className="gap-2 h-8">
          {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <GitBranch className="h-3.5 w-3.5" />}
          {running ? "Running…" : data.cbc_rows.length > 0 ? "Re-run CBC" : "Run CBC Classifier"}
        </Button>
        {msg && <span className="text-[11px] text-slate-400">{msg}</span>}
      </div>
      {data.cbc_rows.length > 0 && <CbcDonut legend={data.cbc_legend} />}
    </div>
  );
}

// ── Section wrapper ─────────────────────────────────────────────────────────

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-100 pb-5 last:border-0 last:pb-0">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-slate-400" />
        <h3 className="text-[13px] font-semibold text-slate-700">{title}</h3>
      </div>
      {children}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function DiagnosticsView() {
  const { sessionId, params, setSelectedTransect, setInspectorOpen, refreshCbc } = useStore();
  const [data, setData] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [smoothWindow, setSmoothWindow] = useState(3);
  const smoothDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(
    (win?: number) => {
      if (!sessionId || !params?.has_results) return;
      setLoading(true);
      api
        .diagnostics(sessionId, win)
        .then(setData)
        .catch(() => {})
        .finally(() => setLoading(false));
    },
    [sessionId, params?.has_results]
  );

  useEffect(() => {
    load();
  }, [load]);

  const handleWindowChange = (w: number) => {
    setSmoothWindow(w);
    if (smoothDebounce.current) clearTimeout(smoothDebounce.current);
    smoothDebounce.current = setTimeout(() => load(w), 400);
  };

  const handleSelectTransect = (tid: number) => {
    setSelectedTransect(tid);
    setInspectorOpen(true);
  };

  if (!params?.has_results) {
    return (
      <div className="flex h-full items-center justify-center text-[13px] text-slate-400">
        Run an analysis to populate diagnostics.
      </div>
    );
  }

  return (
    <div className="gb-panel">
      {/* toolbar */}
      <div className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 px-3 py-2">
        <span className="text-[13px] font-medium text-slate-700">Spatial &amp; Statistical Diagnostics</span>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 gap-1.5 text-[12px] text-slate-500"
          onClick={() => load(smoothWindow)}
          disabled={loading}
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          Refresh
        </Button>
      </div>

      {/* body */}
      <div className="shift-scroll flex-1 overflow-y-auto px-4 py-4">
        {!data ? (
          <div className="flex items-center gap-2 text-[12px] text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading diagnostics…
          </div>
        ) : !data.available ? (
          <div className="text-[12px] text-slate-400">No classic analysis results found.</div>
        ) : (
          <div className="flex flex-col gap-6">
            {/* 1. Spatial */}
            <Section icon={Activity} title="Spatial Autocorrelation (Moran's I)">
              <MoransCard data={data} />
              <SmoothingSlider window={smoothWindow} onChange={handleWindowChange} />
            </Section>

            {/* 2. CBC */}
            <Section icon={GitBranch} title="Coastal Behaviour Classification (CBC)">
              <CbcSection
                sessionId={sessionId!}
                data={data}
                onDone={() => { load(smoothWindow); refreshCbc(); }}
              />
            </Section>

            {/* 3. Scatter */}
            <Section icon={BarChart3} title="Rate Scatter — EPR vs LRR">
              <ScatterPlot
                scatter={data.scatter}
                regLine={data.reg_line}
                outlierCount={data.outlier_count}
                onSelect={handleSelectTransect}
              />
            </Section>

            {/* 4. Monte Carlo */}
            <Section icon={FlaskConical} title="Monte Carlo Positional Uncertainty (N=500)">
              <MonteCarloSection
                sessionId={sessionId!}
                mcAvailable={data.mc_available}
                mcRows={data.mc_rows}
                onDone={() => load(smoothWindow)}
              />
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}
