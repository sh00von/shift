"use client";

import { useEffect, useMemo, useState } from "react";
import { useStore } from "@/lib/store";
import { api, RateProfilePoint } from "@/lib/api";

type Metric = "lrr" | "epr" | "wlr" | "sens" | "ekf";

const METRICS: { key: Metric; label: string; color: string }[] = [
  { key: "lrr",  label: "LRR",      color: "#2563eb" },
  { key: "epr",  label: "EPR",      color: "#64748b" },
  { key: "wlr",  label: "WLR",      color: "#0891b2" },
  { key: "sens", label: "Sen's",    color: "#d97706" },
  { key: "ekf",  label: "EKF",      color: "#7c3aed" },
];

const W = 900, H = 220, PAD = { top: 18, right: 16, bottom: 36, left: 56 };
const INNER_W = W - PAD.left - PAD.right;
const INNER_H = H - PAD.top - PAD.bottom;

export function RateProfileChart() {
  const { sessionId, params } = useStore();
  const [points, setPoints]   = useState<RateProfilePoint[]>([]);
  const [metric, setMetric]   = useState<Metric>("lrr");
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    if (!sessionId || !params?.has_results) return;
    api.rateProfile(sessionId).then((d) => setPoints(d.points));
  }, [sessionId, params?.has_results]);

  const vals = useMemo(
    () => points.map((p) => p[metric]).filter((v): v is number => v !== null),
    [points, metric]
  );

  if (!params?.has_results || points.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-400">
        Run analysis to see the rate profile.
      </div>
    );
  }

  const yMin = Math.min(...vals, 0);
  const yMax = Math.max(...vals, 0);
  const yPad = Math.max((yMax - yMin) * 0.12, 0.5);
  const yLo  = yMin - yPad;
  const yHi  = yMax + yPad;

  const xScale = (i: number) => (i / Math.max(points.length - 1, 1)) * INNER_W;
  const yScale = (v: number) => INNER_H - ((v - yLo) / (yHi - yLo)) * INNER_H;
  const zeroY  = yScale(0);

  // Build polyline path
  const linePts = points
    .map((p, i) => {
      const v = p[metric];
      return v !== null ? `${xScale(i).toFixed(1)},${yScale(v).toFixed(1)}` : null;
    })
    .filter(Boolean);
  const polyline = linePts.join(" ");

  // Y axis ticks
  const nTicks = 5;
  const yTicks = Array.from({ length: nTicks + 1 }, (_, i) => {
    const v = yLo + ((yHi - yLo) * i) / nTicks;
    return { v, y: yScale(v) };
  });

  // X axis ticks — show ~8 evenly spaced transect IDs
  const xStep = Math.max(1, Math.round(points.length / 8));
  const xTicks = points
    .filter((_, i) => i % xStep === 0 || i === points.length - 1)
    .map((p, _, arr) => {
      const idx = points.indexOf(p);
      return { id: p.transect_id, x: xScale(idx) };
    });

  const col = METRICS.find((m) => m.key === metric)!.color;

  return (
    <div className="flex h-full flex-col gap-2 p-3">
      {/* Metric selector */}
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] font-medium text-slate-500 mr-1">Y axis:</span>
        {METRICS.map(({ key, label, color }) => {
          // only show if data has non-null values for this metric
          const hasData = points.some((p) => p[key] !== null);
          if (!hasData) return null;
          return (
            <button
              key={key}
              onClick={() => setMetric(key)}
              className={`rounded px-2 py-0.5 text-[11px] font-semibold transition-colors ${
                metric === key
                  ? "text-white shadow-sm"
                  : "bg-slate-100 text-slate-500 hover:bg-slate-200"
              }`}
              style={metric === key ? { backgroundColor: color } : {}}
            >
              {label}
            </button>
          );
        })}
        <span className="ml-auto text-[11px] text-slate-400">m/yr · {points.length} transects</span>
      </div>

      {/* SVG chart */}
      <div className="relative min-h-0 flex-1">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-full w-full"
          onMouseLeave={() => setHovered(null)}
        >
          <g transform={`translate(${PAD.left},${PAD.top})`}>
            {/* Grid lines */}
            {yTicks.map(({ v, y }) => (
              <line key={v} x1={0} x2={INNER_W} y1={y} y2={y}
                stroke={v === 0 ? "#94a3b8" : "#e2e8f0"}
                strokeWidth={v === 0 ? 1.2 : 0.8}
                strokeDasharray={v === 0 ? "none" : "3 3"}
              />
            ))}

            {/* Fill area above/below zero */}
            {points.length > 1 && (() => {
              const erosion: string[] = [];
              const accretion: string[] = [];
              points.forEach((p, i) => {
                const v = p[metric];
                if (v === null) return;
                const x = xScale(i).toFixed(1);
                const y = yScale(v).toFixed(1);
                if (v < 0) erosion.push(`${x},${y}`);
                else accretion.push(`${x},${y}`);
              });

              // build a filled polygon for the whole line clipped to above/below zero
              const allPts = points
                .map((p, i) => ({ x: xScale(i), y: yScale(p[metric] ?? 0), v: p[metric] }))
                .filter((pt) => pt.v !== null);

              if (allPts.length < 2) return null;
              const areaPath =
                `M ${allPts[0].x} ${zeroY} ` +
                allPts.map((pt) => `L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`).join(" ") +
                ` L ${allPts[allPts.length - 1].x} ${zeroY} Z`;

              return (
                <>
                  <clipPath id="above-zero">
                    <rect x={0} y={0} width={INNER_W} height={zeroY} />
                  </clipPath>
                  <clipPath id="below-zero">
                    <rect x={0} y={zeroY} width={INNER_W} height={INNER_H - zeroY} />
                  </clipPath>
                  <path d={areaPath} fill="#10b981" fillOpacity={0.15} clipPath="url(#above-zero)" />
                  <path d={areaPath} fill="#ef4444" fillOpacity={0.15} clipPath="url(#below-zero)" />
                </>
              );
            })()}

            {/* Rate line */}
            {polyline && (
              <polyline
                points={polyline}
                fill="none"
                stroke={col}
                strokeWidth={1.8}
                strokeLinejoin="round"
              />
            )}

            {/* Hover dots + tooltip */}
            {points.map((p, i) => {
              const v = p[metric];
              if (v === null) return null;
              const x = xScale(i);
              const y = yScale(v);
              const isHov = hovered === i;
              return (
                <g key={p.transect_id}>
                  <rect
                    x={x - 6} y={0} width={12} height={INNER_H}
                    fill="transparent"
                    onMouseEnter={() => setHovered(i)}
                  />
                  {isHov && (
                    <>
                      <line x1={x} x2={x} y1={0} y2={INNER_H}
                        stroke="#94a3b8" strokeWidth={1} strokeDasharray="3 3" />
                      <circle cx={x} cy={y} r={4} fill={col} stroke="white" strokeWidth={1.5} />
                      <rect
                        x={Math.min(x + 6, INNER_W - 90)} y={Math.max(y - 28, 0)}
                        width={86} height={22} rx={4}
                        fill="#1e293b" fillOpacity={0.9}
                      />
                      <text
                        x={Math.min(x + 49, INNER_W - 45)} y={Math.max(y - 13, 13)}
                        textAnchor="middle" fill="white" fontSize={10} fontFamily="monospace"
                      >
                        #{p.transect_id}  {v > 0 ? "+" : ""}{v.toFixed(2)} m/yr
                      </text>
                    </>
                  )}
                </g>
              );
            })}

            {/* Y axis */}
            {yTicks.map(({ v, y }) => (
              <text key={v} x={-6} y={y + 4} textAnchor="end"
                fontSize={9} fill="#64748b" fontFamily="monospace">
                {v > 0 ? "+" : ""}{v.toFixed(1)}
              </text>
            ))}

            {/* X axis ticks */}
            {xTicks.map(({ id, x }) => (
              <text key={id} x={x} y={INNER_H + 14} textAnchor="middle"
                fontSize={9} fill="#94a3b8">
                {id}
              </text>
            ))}

            {/* Axis labels */}
            <text x={INNER_W / 2} y={INNER_H + 28} textAnchor="middle"
              fontSize={10} fill="#64748b">
              Transect ID
            </text>
            <text
              transform={`translate(-42,${INNER_H / 2}) rotate(-90)`}
              textAnchor="middle" fontSize={10} fill="#64748b"
            >
              Rate (m/yr)
            </text>

            {/* Accretion / Erosion labels */}
            {yMax > 0 && (
              <text x={INNER_W - 4} y={8} textAnchor="end"
                fontSize={9} fill="#10b981" fontWeight="600">▲ Accretion</text>
            )}
            {yMin < 0 && (
              <text x={INNER_W - 4} y={INNER_H - 4} textAnchor="end"
                fontSize={9} fill="#ef4444" fontWeight="600">▼ Erosion</text>
            )}
          </g>
        </svg>
      </div>
    </div>
  );
}
